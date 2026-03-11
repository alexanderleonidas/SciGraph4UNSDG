import requests
import os
import time
from itertools import islice
from helper_funcs import load_env, save_json, load_json

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_env()

OPENALEX_API = "https://api.openalex.org/"
OPENALEX_KEY = os.environ["OPENALEX_API_KEY"]

# Fields we actually need for the KG — using select= keeps responses lean
# and avoids paying for fields we discard. See ontology for rationale.
WORK_SELECT_FIELDS = ",".join([
    "id",
    "doi",
    "title",
    "publication_year",
    "publication_date",
    "type",
    "language",
    "primary_location",  # → source (journal id, name, issn, type, is_oa)
    "authorships",  # → institutions + country_codes only (no authors)
    "primary_topic",  # → topic id/name + subfield/field/domain
    "topics",  # → secondary topics with scores
    "sustainable_development_goals",  # → SDG id + score (the bridge property)
    "funders",  # → funder id + display_name
])


# ---------------------------------------------------------------------------
# Resilient HTTP helper (as recommended in the docs)
# ---------------------------------------------------------------------------
def _get(url: str, params: dict, max_retries: int = 5) -> dict:
    """
    GET with exponential back-off on 429 / 5xx.
    :param url: API endpoint
    :param params: query parameters
    :param max_retries: max number of retries before giving up
    :return: A JSON object
    """
    params["api_key"] = OPENALEX_KEY
    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        if response.status_code in (429, 500, 502, 503):
            wait = 2 ** attempt
            print(f"  [{response.status_code}] retrying in {wait}s …")
            time.sleep(wait)
            continue
        response.raise_for_status()
    raise RuntimeError("Max retries exceeded")


# ---------------------------------------------------------------------------
# Cursor-based paginator
# ---------------------------------------------------------------------------
def _paginate(endpoint: str, params: dict, max_results: int) -> list[dict]:
    """
    Fetches up to `max_results` records using cursor pagination. OpenAlex caps basic paging at 10 000 results,
    but the cursor bypasses that. `per_page` is set to 100 (API max) to minimise request count.
    :param endpoint: API endpoint
    :param params: query parameters
    :param max_results: max number of results to return
    :return: A list of raw OpenAlex work dicts
    """
    params = {**params, "per_page": 100, "cursor": "*"}
    collected: list[dict] = []

    while len(collected) < max_results:
        data = _get(endpoint, params)
        results = data.get("results", [])
        if not results:
            break
        collected.extend(results)
        print(f"  … fetched {len(collected)} / {max_results}")

        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    return collected[:max_results]


# ---------------------------------------------------------------------------
# Balanced corpus builder
# SDG works: filter=sustainable_development_goals.id:<id>
# Filter for works only in journals, with funders and that are open access: primary_location.source.type:journal,funders.id:!null,open_access.is_oa:true
#
# Collect `n_per_sdg` works per SDG (1-17) in the SDG bucket,
# then mirror that total with a random sample of non-SDG works so the
# corpus is balanced. A fixed seed makes the sample reproducible.
# ---------------------------------------------------------------------------

# Extended select used only for the seed pass — we need referenced_works
# to drive citation expansion. Not used in the general paginator to keep
# payloads small.
SEED_SELECT_FIELDS = WORK_SELECT_FIELDS + ",referenced_works"

# Max IDs per OR-filter batch (API hard limit is 100)
_BATCH_SIZE = 100

def _batched(iterable, n: int):
    """Yield successive n-sized chunks from an iterable."""
    it = iter(iterable)
    while chunk := list(islice(it, n)):
        yield chunk

SDG_IDS = list(range(1, 18))  # 1 … 17


def collect_sdg_works(n_per_sdg: int = 200, seed: int = 42) -> list[dict]:
    """
    Fetches up to `n_per_sdg` works labelled for each of the 17 SDGs.
    :param n_per_sdg: max number of works to fetch per SDG
    :param seed: random seed for reproducibility
    :return: A list of raw OpenAlex work dicts
    """
    endpoint = OPENALEX_API + "works"
    seen_ids: set[str] = set()
    all_works: list[dict] = []

    for sdg_id in SDG_IDS:
        print(f"Fetching SDG {sdg_id} works …")
        params = {
            "filter": f"primary_location.source.type:journal,funders.id:!null,open_access.is_oa:true,sustainable_development_goals.id:{sdg_id}",
            "select": SEED_SELECT_FIELDS, # includes referenced_works for citation expansion
            "sort": "cited_by_count:desc", # prioritise well-cited works
        }
        works = _paginate(endpoint, params, n_per_sdg)
        for w in works:
            oa_id = w.get("id")
            if oa_id and oa_id not in seen_ids:
                seen_ids.add(oa_id)
                all_works.append(w)

    print(f"SDG bucket: {len(all_works)} unique works across all 17 goals.")
    return all_works

def expand_via_citations(seed_works: list[dict], existing_ids: set[str], max_candidates: int = 5000, min_citations_in_seed: int = 2) -> list[dict]:
    """
    Citation expansion: given a high-confidence SDG seed set, collect neighbouring works that have NO SDG label. The strategy is to:
      1. Harvest every OpenAlex ID referenced by the seed works.
      2. Discard IDs already in the corpus (existing_ids).
      3. Batch-fetch the candidates (100 IDs per request — API hard limit).
      4. Keep only works where sustainable_development_goals is empty.
      5. Optionally filter by how many seed papers cite the candidate

    These papers sit in the citation neighbourhood of SDG research but were not labelled by OpenAlex. They are high-value for:
     - gap analysis (under-labelled but topically adjacent work)
     - classifier training (borderline cases that are harder to classify but still relevant)
     - SDG-aware recommendation (borderline cases)

    :param seed_works: output of collect_sdg_works (must include referenced_works)
    :param existing_ids: set of OpenAlex IDs already in the corpus — skipped
    :param max_candidates: upper bound on candidates fetched from the API
    :param min_citations_in_seed: only keep candidates cited by at least this many seed papers (raises topical precision; set to 1 to keep everything)
    :return: List of raw OpenAlex work dicts with no SDG label.
    """
    endpoint = OPENALEX_API + "works"

    # ------------------------------------------------------------------
    # Step 1 & 2: harvest referenced IDs and count how many seed papers cite each candidate
    # ------------------------------------------------------------------
    citation_count: dict[str, int] = {}   # candidate_id → count of seed papers citing it
    for work in seed_works:
        for ref_id in work.get("referenced_works") or []:
            # ref_id looks like "https://openalex.org/W123456"
            if ref_id not in existing_ids:
                citation_count[ref_id] = citation_count.get(ref_id, 0) + 1

    # Apply topical precision filter and rank by citation frequency
    candidates = sorted(
        [cid for cid, cnt in citation_count.items() if cnt >= min_citations_in_seed],
        key=lambda cid: citation_count[cid],
        reverse=True,
    )
    candidates = candidates[:max_candidates]   # cap before API calls
    print(f"Citation expansion: {len(citation_count)} unique references found, "
          f"{len(candidates)} pass min_citations_in_seed={min_citations_in_seed} filter.")

    if not candidates:
        return []

    # ------------------------------------------------------------------
    # Step 3: batch-fetch candidates (100 IDs per request)
    # ------------------------------------------------------------------
    # We strip the base URL to get bare IDs like "W123456" for the filter
    def _bare_id(full_uri: str) -> str:
        return full_uri.split("/")[-1]

    expanded: list[dict] = []

    for batch in _batched(candidates, _BATCH_SIZE):
        bare_ids = "|".join(_bare_id(cid) for cid in batch)
        params = {
            # We can add `sustainable_development_goals.id:null` to the filter for works without SDG labels
            "filter": f"openalex_id:{bare_ids},primary_location.source.type:journal,funders.id:!null,open_access.is_oa:true",
            "select": WORK_SELECT_FIELDS,       # no referenced_works needed here
            "per_page": _BATCH_SIZE,
        }
        data = _get(endpoint, params)
        results = data.get("results", [])

        # ------------------------------------------------------------------
        # Step 4: keep only unlabelled works
        # ------------------------------------------------------------------
        unlabelled = [
            w for w in results
            if not w.get("sustainable_development_goals")   # empty list or None
        ]
        expanded.extend(unlabelled)
        print(f"  … batch fetched {len(results)}, {len(unlabelled)} unlabelled "
              f"| running total: {len(expanded)}")

    print(f"Citation expansion complete: {len(expanded)} unlabelled neighbouring works.")
    return expanded


def build_balanced_corpus(n_per_sdg: int = 200, seed: int = 42, citation_expansion: bool = True, min_citations_in_seed: int = 2) -> dict:
    """
    Builds and saves a balanced corpus:
      - SDG bucket: up to ``n_per_sdg`` per goal (deduplicated)
      - Citation-expanded unlabelled works (optional, saved separately)
    The citation-expanded works are saved to a separate file so they can be treated as a distinct split rather than blindly merged into the random non-SDG sample.
    Saves the raw outputs to JSON files in the `data/OpenAlex/` directory.

    :param n_per_sdg: max number of works to fetch per SDG goal
    :param seed: random seed for reproducibility
    :param citation_expansion: whether to expand SDG seed set with neighbouring works
    :param min_citations_in_seed: only keep candidates cited by at least this many seed papers (raises topical precision; set to 1 to keep everything)
    :return: A dict with summary stats
    """
    # --- SDG seed -----------------------------------------------------------
    sdg_works = collect_sdg_works(n_per_sdg, seed)
    seed_ids = {w["id"] for w in sdg_works}
    save_json(sdg_works, "OpenAlex/works_sdg")

    # --- Citation expansion -------------------------------------------------
    expanded_works: list[dict] = []
    if citation_expansion:
        expanded_works = expand_via_citations(
            seed_works=sdg_works,
            existing_ids=seed_ids,
            max_candidates=30000,
            min_citations_in_seed=min_citations_in_seed,
        )
        save_json(expanded_works, "OpenAlex/works_expanded")
        # Add their IDs so the random sampler doesn't duplicate them
        seed_ids.update(w["id"] for w in expanded_works)

    summary = {
        "sdg_works_count": len(sdg_works),
        "expanded_works_count": len(expanded_works),
        "balanced": len(sdg_works) == (len(expanded_works)),
    }
    print(summary)
    return summary


# ---------------------------------------------------------------------------
# Information extractor
# Maps a raw OpenAlex work dict → the flat dict that will be used to
# populate RDF triples in the knowledge graph.
# ---------------------------------------------------------------------------

def extract_information(work: dict) -> dict:
    """
    Extracts and normalises the fields needed to populate the KG from a single OpenAlex work record.
    :param work: A raw OpenAlex work dict.
    :returns: A dict whose keys mirror the ontology datatype/object properties defined in SciGraph4UNSDG ontology.
    None if the record is missing its core identifier.
    """
    oa_id = work.get("id")
    if not oa_id:
        return {}

    # --- Core bibliographic -------------------------------------------------
    record = {
        "id": oa_id,  # openalex:work IRI
        "doi": work.get("doi"),  # bibo:doi
        "title": work.get("title") or work.get("display_name"),  # dct:title
        "publication_year": work.get("publication_year"),  # schema:copyrightYear
        "publication_date": work.get("publication_date"),  # schema:datePublished
        "work_type": work.get("type"),  # dct:type
        "language": work.get("language"),  # dct:language
    }

    # --- Open access --------------------------------------------------------
    # oa = work.get("open_access") or {}
    # record["is_oa"] = oa.get("is_oa", False)  # schema:isAccessibleForFree

    # --- Source (journal / repository) --------------------------------------
    # → will become an bibo:journal node linked via dct:isPartOf
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    record["source"] = {
        "id": source.get("id"),
        "name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "type": source.get("type"),
        "is_oa": primary_loc.get("is_oa", False),
        "pdf_url": primary_loc.get("pdf_url"),
        "landing_page_url": primary_loc.get("landing_page_url"),
    } if source else None

    # --- Institutions & countries -------------------------------------------
    # → will become org:Organization nodes linked via ex:affiliatedWith
    # Authors are intentionally discarded; we only keep institution-level data.
    institutions_seen: dict[str, dict] = {}
    country_codes: set[str] = set()

    for authorship in work.get("authorships") or []:
        for cc in authorship.get("countries") or []:
            country_codes.add(cc)
        for inst in authorship.get("institutions") or []:
            inst_id = inst.get("id")
            if inst_id and inst_id not in institutions_seen:
                institutions_seen[inst_id] = {
                    "id": inst_id,
                    "name": inst.get("display_name"),
                    "ror": inst.get("ror"),
                    "country_code": inst.get("country_code"),
                    "type": inst.get("type"),
                }

    record["institutions"] = list(institutions_seen.values())  # ex:affiliatedWith
    record["country_codes"] = sorted(country_codes)  # schema:countryOfOrigin

    # --- Topics -------------------------------------------------------------
    # → will become skos:Concept nodes linked via foaf:topic
    primary_topic_raw = work.get("primary_topic") or {}
    record["primary_topic"] = _extract_topic(primary_topic_raw) if primary_topic_raw else None

    # record["topics"] = [
    #     _extract_topic(t)
    #     for t in (work.get("topics") or [])
    #     if t.get("id") != (primary_topic_raw.get("id"))  # avoid duplicating primary
    # ]

    # --- Funders ------------------------------------------------------------
    # → will become schema:FundingAgency nodes linked via schema:funder
    record["funders"] = [
        {
            "id": f.get("id"),
            "name": f.get("display_name"),
        }
        for f in (work.get("funders") or [])
    ]

    # --- SDG labels ---------------------------------------------------------
    # → the BRIDGE: ex:addressesGoal / addressesTarget
    record["sdg_labels"] = [
        {
            "id": sdg.get("id"),  # e.g. "https://metadata.un.org/sdg/1"
            "score": sdg.get("score"),  # ex:sdgRelevanceScore
        }
        for sdg in (work.get("sustainable_development_goals") or [])
    ]
    record["has_sdg_label"] = bool(record["sdg_labels"])

    return record


def _extract_topic(topic: dict) -> dict:
    """
    Normalises a single topic block from OpenAlex.
    :param topic: A raw OpenAlex topic dict.
    :returns: A dict whose keys mirror the ontology datatype/object properties defined in SciGraph4UNSDG ontology.
    """
    return {
        "id": topic.get("id"),
        "name": topic.get("display_name"),
        "score": topic.get("score"),
        "subfield": {
            "id": (topic.get("subfield") or {}).get("id"),
            "name": (topic.get("subfield") or {}).get("display_name"),
        },
        "field": {
            "id": (topic.get("field") or {}).get("id"),
            "name": (topic.get("field") or {}).get("display_name"),
        },
        "domain": {
            "id": (topic.get("domain") or {}).get("id"),
            "name": (topic.get("domain") or {}).get("display_name"),
        },
    }


def extract_corpus(works: list[dict]) -> list[dict]:
    """
    Runs extract_information over a list of raw works, dropping any records that fail validation (missing id).
    :param works: A list of raw OpenAlex work dicts.
    :returns: A list of normalised work dicts.
    """
    extracted = [extract_information(w) for w in works]
    return [r for r in extracted if r is not None]


def extract_openalex_data(num_works_per_sdg=200, seed=42, citation_expansion=True, min_citations_in_seed=2):
    """
    Extract the Works from OpenAlex and save them to a JSON file ready to be converted to RDF. The file is saved in the `data/OpenAlex/` directory.
    :param num_works_per_sdg: max number of works to fetch per SDG goal
    :param seed: random seed for reproducibility
    :param citation_expansion: whether to expand SDG seed set with neighbouring works
    :param min_citations_in_seed: only keep candidates cited by at least this many seed papers (raises topical precision; set to 1 to keep everything)
    :return: A dict with summary stats
    """
    # Build balanced corpus with citation expansion enabled.
    # Set citation_expansion=False to skip and use random-only non-SDG.
    build_balanced_corpus(n_per_sdg=num_works_per_sdg, seed=seed, citation_expansion=citation_expansion, min_citations_in_seed=min_citations_in_seed)

    # Load and extract all three buckets
    raw_sdg = load_json("data/OpenAlex/works_sdg")
    raw_expanded = load_json("data/OpenAlex/works_expanded")  # may be empty if expansion off

    save_json(extract_corpus(raw_sdg), "OpenAlex/extracted_works_sdg")
    save_json(extract_corpus(raw_expanded), "OpenAlex/extracted_works_expanded")
    print(f"Extracted {len(raw_sdg)} SDG | {len(raw_expanded)} citation-expanded ")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # # Build balanced corpus: 200 works per SDG + equal non-SDG sample
    # build_balanced_corpus(n_per_sdg=1, seed=42)
    #
    # # Load, extract, and save normalised records
    # raw_sdg = load_json("data/OpenAlex/works_sdg")
    # raw_non_sdg = load_json("data/OpenAlex/works_non_sdg")
    #
    # extracted_sdg = extract_corpus(raw_sdg)
    # extracted_non_sdg = extract_corpus(raw_non_sdg)
    #
    # save_json(extracted_sdg, "OpenAlex/extracted_works_sdg")
    # save_json(extracted_non_sdg, "OpenAlex/extracted_works_non_sdg")
    #
    # print(f"Extracted {len(extracted_sdg)} SDG + {len(extracted_non_sdg)} non-SDG records.")

    # save_openalex_data()
    pass
