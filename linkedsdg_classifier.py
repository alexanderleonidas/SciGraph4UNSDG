"""
linkedsdg_classifier.py

Takes extracted OpenAlex work records, feeds their PDF URLs into the
LinkedSDG API, and saves a structured JSON mapping:

    openalex_id  →  SDG classification tree (goals/targets/indicators/series)

The output JSON is designed to be loaded directly into the KG population
step, where each series entry maps to an scitax:sdgRelevanceScore triple.
"""

import os
import hashlib
import datetime
import time
import requests
from urllib.parse import quote
from helper_funcs import save_json, load_json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LINKEDSDG_API = "http://linkedsdg.officialstatistics.org/swaggerapi"

# These four flags control response verbosity.
# We want all of them to populate the full SDG tree in the output.
API_PARAMS = {
    "text": "true",
    "geoAreas": "true",
    "concepts": "true",
    "sdgs": "true",
}

# Polite pacing — LinkedSDG is a public academic service.
REQUEST_DELAY_SECONDS = 1.5

MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _encode_url(link: str) -> str:
    """
    Percent-encode a URL for embedding in a query string.
    Uses quote() rather than manual replace() so all reserved characters
    are handled correctly, not just ':' and '/'.
    """
    return quote(link, safe="")


def _pick_url(extracted_work: dict) -> list[str]:
    """
    Returns an ordered list of URLs to try for a given work, from most
    to least likely to yield a parseable full-text response from LinkedSDG.

    Priority order:
    1. pdf_url — direct PDF link; best chance of full-text parsing
    2. landing_page_url — publisher page; LinkedSDG can often find the PDF
    3. DOI URL — resolves via doi.org redirect; last resort

    :param extracted_work: a work record as returned by openalex_collector.py
    :returns: an empty list if no URL is available. Callers should try each URL in order and stop at the first success.
    """
    urls: list[str] = []
    source = extracted_work.get("source") or {}

    pdf_url = source.get("pdf_url")
    if pdf_url:
        urls.append(pdf_url)

    landing = source.get("landing_page_url")
    if landing and landing not in urls:
        urls.append(landing)

    doi = extracted_work.get("doi")
    if doi:
        doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        if doi_url not in urls:
            urls.append(doi_url)

    return urls


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def query_linkedsdg(document_url: str) -> dict | None:
    """
    Sends a single URL to the LinkedSDG /url endpoint and returns the
    parsed JSON response. Returns None on unrecoverable failure.

    Endpoint:  POST /swaggerapi/url?url=<encoded>&text=true&geoAreas=true&...
    Payload:   empty — all parameters are query params.

    :param document_url: URL to query
    :returns: JSON response, or None on failure
    """
    encoded = _encode_url(document_url)
    url = f"{LINKEDSDG_API}/url?url={encoded}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                params=API_PARAMS,
                headers={"Content-Type": "application/json"},
                timeout=60,  # LinkedSDG can be slow on large PDFs
            )
            if response.status_code == 200:
                return response.json()

            if response.status_code in (429, 500, 502, 503):
                wait = REQUEST_DELAY_SECONDS * (2 ** attempt)
                print(f"    [{response.status_code}] attempt {attempt}/{MAX_RETRIES} "
                      f"— retrying in {wait:.1f}s")
                time.sleep(wait)
                continue

            # 4xx other than 429: URL is wrong or inaccessible, don't retry
            print(f"    [HTTP {response.status_code}] skipping: {document_url}")
            return None

        except requests.exceptions.Timeout:
            print(f"    [Timeout] attempt {attempt}/{MAX_RETRIES}: {document_url}")
            time.sleep(REQUEST_DELAY_SECONDS * attempt)
        except requests.exceptions.RequestException as exc:
            print(f"    [RequestError] {exc}")
            return None

    print(f"    Max retries exceeded for: {document_url}")
    return None


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def extract_sdg_classification(openalex_id: str, response: dict) -> dict:
    """
    Flattens the nested LinkedSDG response tree into a structured record keyed by openalex_id.

    :param openalex_id: OpenAlex ID of the work being classified
    :param response: LinkedSDG API response
    :returns: A dict with the following keys: openalex_id, geo_areas, concepts, sdg_tree, flat_series.
    """
    record: dict = {
        "openalex_id": openalex_id,
        "geo_areas": [],
        "concepts": [],
        "sdg_tree": [],
        "flat_series": [],
    }

    # --- Geographic areas ---------------------------------------------------
    geo = response.get("geoAreas") or []
    record["geo_areas"] = [
        {"id": g.get("id"), "label": g.get("label")}
        for g in (geo if isinstance(geo, list) else [])
    ]

    # --- Concepts -----------------------------------------------------------
    # Each concept becomes an scitax:EvidenceConcept node in the KG.
    # We extract every field needed to populate the PROV-O properties defined
    # in the ontology: label, weight, vocab matches, and context quotes.
    raw_concepts = response.get("concepts") or []
    record["concepts"] = []

    for concept in (raw_concepts if isinstance(raw_concepts, list) else []):
        # Controlled vocabulary alignments (EuroVoc, UNBIS, etc.)
        # Each match becomes a skos:exactMatch triple in the KG.
        vocab_matches = [{"uri": m.get("uri"), "source": m.get("source")}  for m in (concept.get("match") or []) if m.get("uri")]

        # Context quotes: one EvidenceConcept node will carry ALL quotes
        # for the same concept (deduplicated by matched_phrase + quote).
        # These populate scitax:matchedPhrase and scitax:matchContext.
        contexts = [{"matched_phrase": ctx.get("matched_phrase"), "quote": ctx.get("quote")} for ctx in (concept.get("contexts") or []) if ctx.get("matched_phrase")]

        record["concepts"].append({
        "label": concept.get("label"),  # scitax:conceptLabel
        "weight": concept.get("weight", 0),  # scitax:conceptWeight
        "vocab_matches": vocab_matches,  # skos:exactMatch URIs
        "contexts": contexts,  # matched phrases + quotes
        })

    # --- SDG tree -----------------------------------------------------------
    goals = (response.get("sdgs") or {}).get("children") or []

    for goal in goals:
        goal_node = {
            "goal_id": goal.get("id"),
            "goal_label": goal.get("label"),
            "keywords": goal.get("keywords", []),
            "targets": [],
        }

        for target in goal.get("children") or []:
            target_node = {
                "target_id": target.get("id"),
                "target_label": target.get("label"),
                "keywords": target.get("keywords", []),
                "indicators": [],
            }

            for indicator in target.get("children") or []:
                indicator_node = {
                    "indicator_id": indicator.get("id"),
                    "indicator_label": indicator.get("label"),
                    "keywords": indicator.get("keywords", []),
                    "series": [],
                }

                for series in indicator.get("children") or []:
                    score = series.get("value", 0.0)
                    indicator_node["series"].append({
                        "series_id": series.get("id"),
                        "series_label": series.get("label"),
                        "score": score,
                    })

                    # Flat entry — only keep non-zero scores
                    if score and score > 0:
                        record["flat_series"].append({
                            "goal_id": goal.get("id"),
                            "target_id": target.get("id"),
                            "indicator_id": indicator.get("id"),
                            "series_id": series.get("id"),
                            "score": score,
                        })

                target_node["indicators"].append(indicator_node)
            goal_node["targets"].append(target_node)
        record["sdg_tree"].append(goal_node)

    return record


def build_provenance(openalex_id: str, query_url: str, timestamp: str, classification: dict) -> dict:
    """
    Builds a PROV-O provenance record for one LinkedSDG classification.

    The record describes:
      - The ClassificationActivity (API call metadata)
      - One SDGAssignment per flat_series entry (reified SDG links)
      - EvidenceConcepts from the concepts[] block, linked to assignments
        via the concept weight and vocab matches

    LinkedSDG does not explicitly say "concept X caused indicator Y" —
    it returns concepts and SDG assignments as separate lists. We therefore
    link ALL concepts to ALL assignments from the same activity. This is a
    conservative over-approximation: it means every concept is treated as
    potential evidence for every SDG link. At query time you can filter by
    concept weight or vocab source to narrow the evidence chain.

    :param openalex_id: OpenAlex work URI
    :param query_url: the URL that was sent to the LinkedSDG API
    :param timestamp: ISO-8601 string of when the call was made
    :param classification: output of extract_sdg_classification()
    :returns: Dict ready to be serialised to JSON and later ingested into the KG.
    """

    def _hash(*parts):
        """Stable short ID from concatenated strings."""
        return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()[:12]


    # --- ClassificationActivity ---------------------------------------------
    activity_id = f"CFA{_hash(openalex_id, timestamp)}"
    activity = {
        "id":                 activity_id,
        "type":               "ClassificationActivity",    # → prov:Activity
        "query_url":          query_url,                   # scitax:queryURL
        "timestamp":          timestamp,                   # prov:startedAtTime
        "used_work":          openalex_id,                 # prov:used → work
    }

    # --- EvidenceConcepts ---------------------------------------------------
    evidence_concepts = []
    for concept in classification.get("concepts") or []:
        concept_id = f"CNP{_hash(openalex_id, concept.get('id', concept.get('label', '')))}"
        evidence_concepts.append({
            "id":            concept_id,
            "type":          "EvidenceConcept",            # → prov:Entity + skos:Concept
            "label":         concept.get("label"),         # scitax:conceptLabel
            "weight":        concept.get("weight", 0),     # scitax:conceptWeight
            "vocab_matches": concept.get("vocab_matches", []),  # skos:exactMatch
            "contexts":      concept.get("contexts", []),  # matchedPhrase + matchContext
            "derived_from":  openalex_id,                  # prov:wasDerivedFrom
        })

    # --- SDGAssignments (one per scored flat_series entry) ------------------
    assignments = []
    for entry in classification.get("flat_series") or []:
        assign_id = f"ASG{_hash(openalex_id, entry['series_id'])}"
        assignments.append({
            "id":           assign_id,
            "type":         "SDGAssignment",               # → prov:Entity
            "for_work":     openalex_id,                   # scitax:forWork
            "goal_id":      entry.get("goal_id"),          # scitax:assignedGoal
            "target_id":    entry.get("target_id"),        # scitax:assignedTarget
            "indicator_id": entry.get("indicator_id"),     # scitax:assignedIndicator
            "series_id":    entry.get("series_id"),        # scitax:assignedSeries
            "score":        entry.get("score"),            # scitax:sdgRelevanceScore
            # prov:wasGeneratedBy → activity
            "generated_by": activity_id,
            # prov:used → all evidence concepts (conservative linking)
            "used_concepts": [ec["id"] for ec in evidence_concepts],
        })

    return {
        "openalex_id":      openalex_id,
        "activity":         activity,
        "evidence_concepts": evidence_concepts,
        "assignments":      assignments,
    }



# ---------------------------------------------------------------------------
# Batch classifier
# ---------------------------------------------------------------------------

def classify_corpus(
        extracted_works: list[dict],
        output_path: str = "LinkedSDG/classifications",
        checkpoint_every: int = 50,
        score_threshold: float = 0.0,
        num_successes: int = None,
) -> tuple[list[dict],list[dict]]:
    """
    Iterates over extracted work records, queries LinkedSDG for each, and
    saves a JSON mapping of openalex_id → SDG classification.

    Skipped works (no URL, API failure, empty result) are logged to
    <output_path>_skipped.json so you can inspect and retry them.

    :param extracted_works: output of extract_corpus() from openalex_collector.py
    :param output_path: save path (checkpointed periodically during the run)
    :param checkpoint_every: save to disk every N works (guards against crashes on long runs — the LinkedSDG API is slow)
    :param score_threshold: only retain flat_series entries with score >= this value; 0.0 keeps everything non-zero
    :param num_successes: if set, only save classifications for the first N works that return a successul response.

    :returns: List of classification dicts, one per successfully classified work.
    """
    classifications: list[dict] = []
    provenance_records: list[dict] = []
    skipped: list[dict] = []
    total = len(extracted_works)

    for i, work in enumerate(extracted_works, start=1):
        oa_id = work.get("id")
        print(f"[{i}/{total}] {oa_id}")

        # --- Pick URLs (ordered: pdf → landing page → doi) -----------------
        candidate_urls = _pick_url(work)
        if not candidate_urls:
            print(f"  → skipped: no usable URL")
            skipped.append({"openalex_id": oa_id, "reason": "no_url"})
            continue

        # Try each URL in priority order; stop at first non-empty result.
        # This is the main fix for empty classifications: many works have
        # no accessible PDF at the DOI but do have a direct pdf_url, or
        # vice versa. Exhausting all options before skipping maximises yield.
        response = None
        doc_url = None
        for url in candidate_urls:
            print(f"  → trying: {url}")
            resp = query_linkedsdg(url)
            if resp is None:
                continue
            # Treat a response as useful if it contains any SDG children
            sdg_children = (resp.get("sdgs") or {}).get("children") or []
            if sdg_children:
                response = resp
                doc_url = url
                break
            print(f"    (empty result — trying next URL)")

        if response is None:
            print(f"  → skipped: all URLs returned empty or failed")
            skipped.append({
                "openalex_id": oa_id,
                "reason": "all_urls_failed",
                "urls_tried": candidate_urls,
            })
            continue

        # --- Parse ----------------------------------------------------------
        classification = extract_sdg_classification(oa_id, response)
        classification["source_url"] = doc_url  # record which URL succeeded

        # Apply optional score filter
        if score_threshold > 0:
            classification["flat_series"] = [
                s for s in classification["flat_series"]
                if s["score"] >= score_threshold
            ]

        # Skip works where the API found absolutely nothing
        if not classification["flat_series"] and not classification["concepts"]:
            print(f"  → skipped: empty classification")
            skipped.append({"openalex_id": oa_id, "reason": "empty_result", "url": doc_url})
            continue

        classifications.append(classification)

        # Build PROV-O provenance record for this classification
        prov = build_provenance(
            openalex_id=oa_id,
            query_url=doc_url,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            classification=classification,
        )
        provenance_records.append(prov)

        print(f"  → {len(classification['flat_series'])} scored series | "
              f"{len(classification['geo_areas'])} geo areas | "
              f"{len(classification['concepts'])} concepts | "
              f"{len(prov['evidence_concepts'])} evidence concepts")

        # --- Checkpoint -----------------------------------------------------
        if i % checkpoint_every == 0:
            save_json(classifications, output_path)
            save_json(provenance_records, output_path + "_provenance")
            save_json(skipped, output_path + "_skipped")
            print(f"  [checkpoint] saved {len(classifications)} classifications")

        # Stop if we've reached the desired number of successful classifications (for testing or partial runs)
        if num_successes is not None:
            if  len(classifications) == num_successes:
                print(f"  [checkpoint] reached {num_successes} successful classifications")
                break

        time.sleep(REQUEST_DELAY_SECONDS)

    # Final save
    save_json(classifications, output_path)
    save_json(provenance_records, output_path + "_provenance")
    save_json(skipped, output_path + "_skipped")
    print(f"\nDone.  Classified: {len(classifications)} | Skipped: {len(skipped)}")
    return classifications, provenance_records


def save_classifications(num_works: int = None):
    """
    Perform the full classification run
    :param num_works: The number of works to successfully classify, or None for all works
    """
    # Run all three corpus buckets separately so classifications remain
    # traceable back to their source (SDG-labelled / expanded / random).

    for bucket, in_path, out_path in [
        ("SDG-labelled", "data/OpenAlex/extracted_works_sdg", "LinkedSDG/classifications_sdg"),
        ("citation-expanded", "data/OpenAlex/extracted_works_expanded", "LinkedSDG/classifications_expanded")]:

        works = load_json(in_path)
        if not works:
            print(f"No works found at {in_path} — skipping bucket '{bucket}'.")
            continue

        print(f"\n{'=' * 60}")
        print(f"Classifying {len(works)} {bucket} works …")
        print(f"{'=' * 60}")

        classify_corpus(
            extracted_works=works,
            output_path=out_path,
            checkpoint_every=50,
            score_threshold=0.0,  # keep all non-zero; filter at KG ingestion
            num_successes=num_works,
        )



if __name__ == "__main__":
    # This is just a quick test run on a single URL to verify the API call and response parsing.
    # Get candidate URLs
    # url = "https://genomebiology.biomedcentral.com/counter/pdf/10.1186/gb-2009-10-3-r25"
    # # Try classification with each URL
    # response = query_linkedsdg(url)
    #
    # # Parse the classification
    # classification = extract_sdg_classification(url, response)
    # classification["source_url"] = url
    #
    # # Optionally save the example
    # print("\n Saving example classification...")
    # save_json(classification, "LinkedSDG/example_classification")
    # print("Saved to data/LinkedSDG/example_classification.json")
    pass
