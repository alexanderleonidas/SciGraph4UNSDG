import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from helper_funcs import load_raw_unsdg_data, load_raw_openalex_data, load_json

# Define the namespaces
WD = Namespace("https://www.wikidata.org/wiki/")
SCHEMA = Namespace("http://schema.org/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
PROV = Namespace("http://www.w3.org/ns/prov#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
BIBO = Namespace("http://purl.org/ontology/bibo/")
ORG = Namespace("http://www.w3.org/ns/org#")
UNSDG = Namespace("http://metadata.un.org/sdg/")
SDGO = Namespace("http://metadata.un.org/sdg/ontology#")
SCITAX = Namespace("http://scigraph4unsdg.org/taxonomy#")
SCI = Namespace("http://scigraph4unsdg.org/")

# Create an empty graph
SciGraph4UNSDG = Graph()
SciGraph4UNSDG.bind("wd", WD)
SciGraph4UNSDG.bind("schema", SCHEMA)
SciGraph4UNSDG.bind("xsd", XSD)
SciGraph4UNSDG.bind("owl", OWL)
SciGraph4UNSDG.bind("prov", PROV)
SciGraph4UNSDG.bind("rdfs", RDFS)
SciGraph4UNSDG.bind("rdf", RDF)
SciGraph4UNSDG.bind("skos", SKOS)
SciGraph4UNSDG.bind("foaf", FOAF)
SciGraph4UNSDG.bind("dct", DCT)
SciGraph4UNSDG.bind("unsdg", UNSDG)
SciGraph4UNSDG.bind("sdgo", SDGO)
SciGraph4UNSDG.bind("bibo", BIBO)
SciGraph4UNSDG.bind("org", ORG)
SciGraph4UNSDG.bind("scitax",  SCITAX)
SciGraph4UNSDG.bind("sci",  SCI)


def add_triple(subject, predicate, obj):
    """
    Add a triple to the SciGraph4UNSDG graph
    :param subject: URI
    :param predicate: URI
    :param obj: Literal or URI
    :return:
    """
    SciGraph4UNSDG.add((subject, predicate, obj))


def transform_indicator_code(code: str) -> str:
    """
    Transform an indicator code into a format suitable for the knowledge graph. For example, "1.1.1" would be transformed into "C010101".
    :param code: Indicator code
    :return: Transformed indicator code
    """
    code = code.replace(".", "0")
    return "C0" + code


def add_unsdg_triples():
    """
    Procedure to add UNSDG triples to the KG
    """
    # Load the UNSDG data from the JSON files
    goals, targets, indicators, series = load_raw_unsdg_data()

    # Add triples for the Goals
    for g in goals:
        code = g["code"]
        add_triple(UNSDG[code], RDF.type, SDGO.Goal)
        add_triple(UNSDG[code], SKOS.prefLabel, Literal(g["title"], lang="en"))
        add_triple(UNSDG[code], DCT.description, Literal(g["description"], lang="en"))

    # Add triples for the Targets
    for t in targets:
        goal = t["goal"]
        code = t["code"]
        add_triple(UNSDG[code], RDF.type, SDGO.Target)
        add_triple(UNSDG[code], SKOS.prefLabel, Literal(t["title"], lang="en"))
        add_triple(UNSDG[goal], SDGO.hasTarget, UNSDG[code])
        add_triple(UNSDG[code], SDGO.isTargetOf, UNSDG[goal])

    # Add triples for the Indicators
    for i in indicators:
        target = i["target"]
        code = transform_indicator_code(i["code"])
        add_triple(UNSDG[code], RDF.type, SDGO.Indicator)
        add_triple(UNSDG[code], SDGO.isIndicatorOf, UNSDG[target])
        add_triple(UNSDG[target], SDGO.hasIndicator, UNSDG[code])
        add_triple(UNSDG[code], SKOS.prefLabel, Literal(i["description"], lang="en"))

    for s in series:
        code = s["code"]
        add_triple(UNSDG[code], RDF.type, SDGO.Series)
        add_triple(UNSDG[code], SKOS.prefLabel, Literal(s["description"], lang="en"))
        for i in s["indicator"]:
            i = transform_indicator_code(i)
            add_triple(UNSDG[code], SDGO.isSeriesOf, UNSDG[i])
            add_triple(UNSDG[i], SDGO.hasSeries, UNSDG[code])


def add_work(work: dict):
    """
    Add a work object to the SciGraph4UNSDG graph and all its related triples (institutions, topics, SDG connections, etc.)
    :param work: a JSON object representing a work
    """
    # Add the work as a bibo:Document
    work_id = URIRef(work["id"])
    add_triple(work_id, RDF.type, BIBO.Document)
    add_triple(work_id, DCT.title, Literal(work["title"], lang="en"))
    add_triple(work_id, BIBO.doi, Literal(work["doi"], lang="en"))
    # add_triple(work_id, DCT.type, Literal(work["doi"], lang="en"))
    add_triple(work_id, DCT.language, Literal(work["language"], datatype=XSD.language))
    add_triple(work_id, SCHEMA.datePublished, Literal(work["publication_date"], datatype=XSD.date))
    add_triple(work_id, SCHEMA.copyrightYear, Literal(work["publication_year"], datatype=XSD.gYear))
    add_triple(work_id, SCHEMA.isAccessibleForFree, Literal(work["source"]["is_oa"], datatype=XSD.boolean))

    # ---------- Add the journal as a bibo:Journal ----------
    journal_id = URIRef(work["source"]["id"])
    add_triple(journal_id, RDF.type, BIBO.Journal)
    add_triple(journal_id, SCHEMA.name, Literal(work["source"]["name"], lang="en"))
    add_triple(journal_id, BIBO.issn, Literal(work["source"]["issn"], datatype=XSD.string))
    add_triple(work_id, DCT.isPartOf, journal_id)  # connect the work to the journal
    add_triple(journal_id, DCT.hasPart, work_id)

    # ---------- Add the institutions as ORG:Organization ----------
    for institution in work["institutions"]:
        institution_id = URIRef(institution["id"])
        add_triple(institution_id, RDFS.subClassOf, ORG.Organization)
        if institution["type"] == 'education':
            add_triple(institution_id, RDFS.type, SCHEMA.EducationalOrganization)
        elif institution["type"] == 'healthcare':
            add_triple(institution_id, RDFS.type, SCHEMA.MedicalOrganization)
        elif institution["type"] == 'company':
            add_triple(institution_id, RDFS.type, SCHEMA.Corporation)
        elif institution["type"] == 'government':
            add_triple(institution_id, RDFS.type, SCHEMA.GovernmentOrganization)
        elif institution["type"] == 'nonprofit':
            add_triple(institution_id, RDFS.type,  SCITAX.NonProfit)
        elif institution["type"] == 'facility':
            add_triple(institution_id, RDFS.type,  SCITAX.Facility)
        else:
            add_triple(institution_id, RDFS.type, ORG.Organization)
            SciGraph4UNSDG.remove((institution_id, RDFS.subClassOf, ORG.Organization))
        add_triple(institution_id, SCHEMA.name, Literal(institution["name"], lang="en"))
        add_triple(institution_id, ORG.identifier, Literal(institution["ror"], datatype=XSD.anyURI))
        # add_triple(institution_id, SCHEMA.countryOfOrigin, Literal(institution["country_code"], lang="en"))
        add_triple(institution_id, SCHEMA.producer, work_id)  # connect the institution to the work

    # ---------- Add the primary topics of the work ----------
    primary_topic_id = URIRef(work["primary_topic"]["id"])
    domain_id = URIRef(work["primary_topic"]["domain"]["id"])
    field_id = URIRef(work["primary_topic"]["field"]["id"])
    subfield_id = URIRef(work["primary_topic"]["subfield"]["id"])

    add_triple(primary_topic_id, RDF.type, SKOS.Concept)
    add_triple(primary_topic_id, SKOS.prefLabel, Literal(work["primary_topic"]["name"], lang="en"))
    add_triple(primary_topic_id, SKOS.inScheme, subfield_id)
    add_triple(primary_topic_id, FOAF.isPrimaryTopicOf, work_id)  # connect the primary topic to the work
    add_triple(work_id, FOAF.primaryTopic, primary_topic_id)

    add_triple(domain_id, RDF.type,  SCITAX.Domain)
    add_triple(domain_id, SKOS.prefLabel, Literal(work["primary_topic"]["domain"]["name"], lang="en"))
    add_triple(domain_id, SKOS.braoder, field_id)
    add_triple(field_id, SKOS.narrower, domain_id)
    add_triple(work_id, FOAF.topic, domain_id)
    add_triple(domain_id, SCHEMA.subjectOf, work_id)

    add_triple(field_id, RDF.type,  SCITAX.Field)
    add_triple(field_id, SKOS.prefLabel, Literal(work["primary_topic"]["field"]["name"], lang="en"))
    add_triple(field_id, SKOS.braoder, subfield_id)
    add_triple(subfield_id, SKOS.narrower, field_id)
    add_triple(work_id, FOAF.topic, field_id)
    add_triple(field_id, SCHEMA.subjectOf, work_id)

    add_triple(subfield_id, RDF.type,  SCITAX.Subfield)
    add_triple(subfield_id, SKOS.prefLabel, Literal(work["primary_topic"]["subfield"]["name"], lang="en"))
    add_triple(subfield_id, SKOS.braoder, primary_topic_id)
    add_triple(primary_topic_id, SKOS.narrower, subfield_id)
    add_triple(work_id, FOAF.topic, subfield_id)
    add_triple(subfield_id, SCHEMA.subjectOf, work_id)

    # ---------- Add the funders of the work ----------
    for funder in work["funders"]:
        funder_id = URIRef(funder["id"])
        add_triple(funder_id, RDF.type, SCHEMA.FundingAgency)
        add_triple(funder_id, SCHEMA.name, Literal(funder["name"], lang="en"))
        add_triple(funder_id, SCHEMA.funder, work_id)
        add_triple(work_id, FOAF.fundedBy, funder_id)

    # ---------- Add the SDG connections to the work ----------
    # 1. Compute total score per goal
    goal_totals = {}
    for series in work["flat_series_scores"]:
        goal_uri = series["goal_id"]
        goal_totals[goal_uri] = goal_totals.get(goal_uri, 0) + series["score"]

    # 2. Determine the maximum total (if any series exist)
    if goal_totals:
        max_total = max(goal_totals.values())
    else:
        max_total = 0  # no series → nothing to add

    # 3. Iterate over series and add triples only for those whose goal achieves the max total
    for series in work["flat_series_scores"]:
        if goal_totals[series["goal_id"]] == max_total:
            g_id = series["goal_id"].split('/')[-1]
            t_id = series["target_id"].split('/')[-1]
            i_id = series["indicator_id"].split('/')[-1]
            s_id = series["series_id"].split('/')[-1]

            # Series level
            add_triple(work_id,  SCITAX.addressesSeries, UNSDG[s_id])
            add_triple(UNSDG[s_id],  SCITAX.seriesAddressedBy, work_id)

            # Indicator level
            add_triple(work_id,  SCITAX.addressesIndicator, UNSDG[i_id])
            add_triple(UNSDG[i_id],  SCITAX.indicatorAddressedBy, work_id)

            # Target level
            add_triple(work_id,  SCITAX.addressesTarget, UNSDG[t_id])
            add_triple(UNSDG[t_id],  SCITAX.targetAddressedBy, work_id)

            # Goal level
            add_triple(work_id,  SCITAX.addressesGoal, UNSDG[g_id])
            add_triple(UNSDG[g_id],  SCITAX.goalAddressedBy, work_id)


def add_openalex_triples(max_works: int = None):
    """
    Procedure to add OpenAlex triples to the KG
    :param max_works: if set, only add this many works to the KG
    """
    # Load the classified OpenAlex data
    print("Loading OpenAlex data...")
    expanded_works, sdg_works, _ = load_raw_openalex_data()

    print("Adding Extended works to the KG...")
    works_parsed = 0
    for work in expanded_works:
        add_work(work)
        works_parsed += 1
        if max_works and works_parsed >= max_works:
            break

    works_parsed = 0
    print("Adding SDG works to the KG...")
    for work in sdg_works:
        add_work(work)
        works_parsed += 1
        if max_works and works_parsed >= max_works:
            break


def add_provenance_for_work(prov_record: dict) -> None:
    """
    Adds PROV-O triples for one work's classification provenance.
    :param prov_record: a JSON object representing a work's classification provenance
    """
    work_uri = URIRef(prov_record["openalex_id"])
    act = prov_record.get("activity", {})
    concepts = prov_record.get("evidence_concepts", [])
    assigns = prov_record.get("assignments", [])

    # ── 1. ClassificationActivity ─────────────────────────────────────────
    act_uri =  SCI[act["id"]]
    add_triple(act_uri, RDF.type,  SCITAX.ClassificationActivity)
    add_triple(act_uri, PROV.used, work_uri)
    if act.get("timestamp"):
        add_triple(act_uri, PROV.wasGeneratedAtTime,
                   Literal(act["timestamp"], datatype=XSD.dateTime))
    # if act.get("query_url"):
    #     add_triple(act_uri,  SCITAX.queryURL,
    #                Literal(act["query_url"], datatype=XSD.anyURI))
    # if act.get("classifier_version"):
    #     add_triple(act_uri,  SCITAX.classifierVersion,
    #                Literal(act["classifier_version"], datatype=XSD.string))

    # ── 2. EvidenceConcepts ───────────────────────────────────────────────
    concept_uri_map: dict[str, URIRef] = {}  # local id → URIRef for step 3

    for ec in concepts:
        ec_uri =  SCI[ec["id"]]
        concept_uri_map[ec["id"]] = ec_uri

        add_triple(ec_uri, RDF.type,  SCITAX.EvidenceConcept)
        add_triple(ec_uri, PROV.wasDerivedFrom, URIRef(ec["derived_from"]))

        if ec.get("label"):
            add_triple(ec_uri,  SCHEMA.name,
                       Literal(ec["label"], datatype=XSD.string))
        if ec.get("weight") is not None:
            add_triple(ec_uri,  SCITAX.conceptWeight,
                       Literal(int(ec["weight"]), datatype=XSD.integer))

        # One matchedPhrase + matchContext triple per context entry
        for ctx in ec.get("contexts") or []:
            if ctx.get("matched_phrase"):
                add_triple(ec_uri,  SCITAX.matchedPhrase,
                           Literal(ctx["matched_phrase"], lang='en'))
            if ctx.get("quote"):
                add_triple(ec_uri,  SCITAX.quoteContext,
                           Literal(ctx["quote"], lang='en'))

        # skos:exactMatch + vocabSource for each controlled vocab alignment
        for vm in ec.get("vocab_matches") or []:
            if vm.get("uri"):
                add_triple(ec_uri, SKOS.exactMatch, URIRef(vm["uri"]))
            # if vm.get("source"):
            #     add_triple(ec_uri,  SCITAX.vocabSource,
            #                Literal(vm["source"], datatype=XSD.string))

    # ── 3. SDGAssignments ─────────────────────────────────────────────────
    for assign in assigns:
        assign_uri =  SCI[assign["id"]]

        # Type and core provenance backbone
        add_triple(assign_uri, RDF.type,  SCITAX.SDGAssignment)
        add_triple(assign_uri, PROV.wasGeneratedBy, SCI[assign["generated_by"]])

        # Bidirectional link between Work and Assignment
        # (the shortcut addressesGoal etc. is already written by add_work;
        #  these new properties carry the full provenance-aware path)
        add_triple(assign_uri,  SCITAX.isAssignmentOf, work_uri)
        add_triple(work_uri,  SCITAX.hasAssignment, assign_uri)

        # Score
        if assign.get("score") is not None:
            add_triple(assign_uri,  SCITAX.relevanceScore,
                       Literal(float(assign["score"]), datatype=XSD.decimal))

        # Link evidence concepts to this assignment
        for ec_id in assign.get("used_concepts") or []:
            ec_uri = concept_uri_map.get(ec_id)
            if ec_uri is not None:
                add_triple(assign_uri, PROV.used, ec_uri)

        # ── Bridge into the UNSDG hierarchy ──────────────────────────────
        # We rebuild the same bare IDs that add_work() uses so these triples
        # point to the exact same unsdgio:Goal / Target / Indicator / Series
        # nodes that already exist in the graph.

        def _bare(uri_str: str | None) -> str | None:
            return uri_str.split("/")[-1] if uri_str else None

        g_bare = _bare(assign.get("goal_id"))
        t_bare = _bare(assign.get("target_id"))
        i_bare = _bare(assign.get("indicator_id"))
        s_bare = _bare(assign.get("series_id"))

        # toGoal → unsdgio:Goal + inverse on the Goal node
        if g_bare:
            goal_node = UNSDG[g_bare]
            add_triple(assign_uri,  SCITAX.toGoal, goal_node)
            add_triple(goal_node, SCITAX.hasAssignmentForGoal, assign_uri)

        # toTarget → unsdgio:Target + inverse
        if t_bare:
            target_node = UNSDG[t_bare]
            add_triple(assign_uri,  SCITAX.toTarget, target_node)
            add_triple(target_node, SCITAX.hasAssignmentForTarget, assign_uri)

        # toIndicator → unsdgio:Indicator + inverse
        # Indicator codes go through transform_indicator_code() to match
        # the format used in add_unsdg_triples() (e.g. "1.1.1" → "C010101")
        if i_bare:
            i_transformed = transform_indicator_code(i_bare)
            indicator_node = UNSDG[i_transformed]
            add_triple(assign_uri,  SCITAX.toIndicator, indicator_node)
            add_triple(indicator_node, SCITAX.hasAssignmentForIndicator, assign_uri)

        # toSeries → unsdgio:Series + inverse
        if s_bare:
            series_node = UNSDG[s_bare]
            add_triple(assign_uri,  SCITAX.toSeries, series_node)
            add_triple(series_node, SCITAX.hasAssignmentForSeries, assign_uri)


def add_provenance_triples(max_works: int = None) -> None:
    """
    Loads all three provenance JSON files produced by classify_corpus() and
    adds PROV-O triples for every classification record.

    Works that were skipped by the classifier (no URL, API failure, empty
    result) will simply have no provenance nodes — that is correct behaviour.
    :param max_works: Optional parameter to limit the number of works added to the graph
    """
    prov_files = [
        "data/LinkedSDG/classifications_sdg_provenance",
        "data/LinkedSDG/classifications_expanded_provenance"
    ]

    works_parsed = 0
    for path in prov_files:
        records = load_json(path)
        print(f"  [provenance] {path}: {len(records)} records")
        for record in records:
            add_provenance_for_work(record)
            works_parsed += 1
            if max_works and works_parsed >= max_works:
                break

def serialise_kg():
    SciGraph4UNSDG.serialize("data/SciGraph4UNSDG.ttl", format="turtle")


def create_kg(max_works: int = None):
    """
    Main procedure to create the SciGraph4UNSDG knowledge graph. This procedure will load the UNSDG data, the OpenAlex data,
    and the provenance data, add all the relevant triples to the graph, and serialise it to a Turtle file.
    :param max_works: Optional parameter to limit the number of works added to the graph (for testing purposes). If None, all works will be added.
    :return:
    """
    SciGraph4UNSDG.parse("data/SciGraph4UNSDG_ontology.ttl")  # Load the ontology
    add_unsdg_triples()
    add_openalex_triples(max_works=max_works)
    add_provenance_triples(max_works=max_works)
    serialise_kg()
    print("Number of Tiples in the graph: ", len(SciGraph4UNSDG))


# if __name__ == "__main__":
#     create_kg()
