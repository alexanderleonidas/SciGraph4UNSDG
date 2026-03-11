import rdflib
from rdflib import Graph, Namespace, Literal

# ----------------------------------------------------------------------
# Namespaces
# ----------------------------------------------------------------------

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
SDGO = Namespace("http://metadata.un.org/sdg/ontology#")
BIBO = Namespace("http://purl.org/ontology/bibo/")
ORG = Namespace("http://www.w3.org/ns/org#")
SCITAX = Namespace("http://scigraph4unsdg.org/taxonomy#")
SCI = Namespace("http://scigraph4unsdg.org/")

# ----------------------------------------------------------------------
# Graph + Prefix bindings
# ----------------------------------------------------------------------
g = Graph()
g.bind("wd", WD)
g.bind("schema", SCHEMA)
g.bind("xsd", XSD)
g.bind("owl", OWL)
g.bind("prov", PROV)
g.bind("rdfs", RDFS)
g.bind("rdf", RDF)
g.bind("skos", SKOS)
g.bind("foaf", FOAF)
g.bind("dct", DCT)
g.bind("sdgo", SDGO)
g.bind("bibo", BIBO)
g.bind("org", ORG)
g.bind("scitax",  SCITAX)
g.bind("sci",  SCI)


def _add_class(uri, label, comment=None, subClassOf: list = None, equivalence: list = None):
    """
    Helper to add a class triple.
    :param uri: URI of the class
    :param label: Label of the class
    :param comment: Comment of the class
    :param subClassOf: List of superclasses
    :param equivalence: List of equivalent classes
    """
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.label, Literal(label, lang="en")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en")))
    if subClassOf:
        for subClassOf in subClassOf:
            g.add((uri, RDFS.subClassOf, subClassOf))
    if equivalence:
        for equiv in equivalence:
            g.add((uri, OWL.equivalentClass, equiv))


def _add_specific_class(uri, cls, label, comment=None, equivalence=None):
    """
    Helper to add a specific type of class as a subclass of a general class.
    :param uri: URI of the class
    :param cls: General class
    :param label: Label of the class
    :param comment: Comment of the class
    :param equivalence: List of equivalent classes
    """
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.subClassOf, cls))
    g.add((uri, RDFS.label, Literal(label, lang="en", )))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en", )))
    if equivalence:
        for equiv in equivalence:
            g.add((uri, OWL.equivalentClass, equiv))


def _add_property(uri, property_type, domain, range_, label, comment=None, inv=None, subPropOf: list = None,
                  equivalence: list = None):
    """
    Helper to add an object property triple
    :param uri: URI of the property
    :param domain: Domain of the property
    :param range_: Range of the property
    :param label: Label of the property
    :param comment: Comment of the property
    :param inv: Inverse of the property
    :subPropOf: Subproperty of the property
    :equivalence: Equivalent of the property
    """
    g.add((uri, RDF.type, property_type))
    g.add((uri, RDFS.domain, domain))
    g.add((uri, RDFS.range, range_))
    g.add((uri, RDFS.label, Literal(label, lang="en", )))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en", )))
    if inv:
        g.add((uri, OWL.inverseOf, inv))
    if subPropOf:
        for sub in subPropOf:
            g.add((uri, RDFS.subPropertyOf, sub))
    if equivalence:
        for equiv in equivalence:
            g.add((uri, OWL.equivalentProperty, equiv))


def create_ontology():
    # ===========================================================================
    # PART 1 — UN SDG ONTOLOGY
    # Classes: Goal · Target · Indicator · Series · Tier
    # ===========================================================================

    # --- Goal ------------------------------------------------------------------
    goal = SDGO.Goal
    g.add((goal, RDF.type, OWL.Class))
    g.add((goal, RDFS.subClassOf, SKOS.Concept))
    g.add((goal, RDFS.label, Literal("Goal", lang="en", )))
    g.add((goal, RDFS.label, Literal("Objetivo", lang="es", )))
    g.add((goal, RDFS.label, Literal("Objectif", lang="fr", )))

    # --- Indicator -------------------------------------------------------------
    indicator = SDGO.Indicator
    g.add((indicator, RDF.type, OWL.Class))
    g.add((indicator, RDFS.subClassOf, SKOS.Concept))
    g.add((indicator, RDFS.label, Literal("Indicator", lang="en", )))
    g.add((indicator, RDFS.label, Literal("Indicateur", lang="fr", )))
    g.add((indicator, RDFS.label, Literal("Indicador", lang="es", )))

    # --- Series ----------------------------------------------------------------
    series = SDGO.Series
    _add_class(series, "Series", "A series of indicators", [SKOS.Concept, SCHEMA.Dataset])

    # --- Target -----------------------------------------------------------------
    target = SDGO.Target
    g.add((target, RDF.type, OWL.Class))
    g.add((target, RDFS.subClassOf, SKOS.Concept))
    g.add((target, RDFS.label, Literal("Target", lang="en", )))
    g.add((target, RDFS.label, Literal("Cible", lang="fr", )))
    g.add((target, RDFS.label, Literal("Meta", lang="es", )))

    # --- Tier -------------------------------------------------------------------
    # tier = SDGO.Tier
    # g.add((tier, RDF.type, OWL.Class))
    # g.add((tier, RDFS.label, Literal("Tier Classification for Global UNSDG Indicators", lang="en")))
    # _add_class(tier, "Tier", "A tier of an indicator", [SKOS.Concept, SCHEMA.Dataset])

    # ---------------------------------------------------------------------------
    # UNSDG Hierarchy properties
    # ---------------------------------------------------------------------------
    # Target → hasIndicator → Indicator
    _add_property(SDGO.hasIndicator, OWL.ObjectProperty, SDGO.Target, SDGO.Indicator, "has indicator",
                  inv=SDGO.isIndicatorOf, subPropOf=[SKOS.narrower])

    # Indicator → isIndicator → Target
    _add_property(SDGO.isIndicatorOf, OWL.ObjectProperty, SDGO.Indicator, SDGO.Target, "is indicator of",
                  inv=SDGO.hasIndicator, subPropOf=[SKOS.broader])

    # Indicator → hasSeries → Series
    _add_property(SDGO.hasSeries, OWL.ObjectProperty, SDGO.Indicator, SDGO.Series, "has series", inv=SDGO.isSeriesOf,
                  subPropOf=[SKOS.narrower])

    # Series → isSeries → Indicator
    _add_property(SDGO.isSeriesOf, OWL.ObjectProperty, SDGO.Series, SDGO.Indicator, "is series of", inv=SDGO.hasSeries,
                  subPropOf=[SKOS.broader])
    isSeriesOf = SDGO.isSeriesOf

    # Goal → hasTarget → Target
    _add_property(SDGO.hasTarget, OWL.ObjectProperty, SDGO.Goal, SDGO.Target, "has target", inv=SDGO.isTargetOf,
                  subPropOf=[SKOS.narrower])

    # Target → isTarget → Goal
    _add_property(SDGO.isTargetOf, OWL.ObjectProperty, SDGO.Target, SDGO.Goal, "is target of", inv=SDGO.hasTarget,
                  subPropOf=[SKOS.broader])

    # Indicator → tier → Tier
    # _add_property(SDGO.tier, OWL.ObjectProperty, SDGO.Indicator, SDGO.Tier, "tier")

    # ===========================================================================
    # PART 2 — OPENALEX CLASSES
    # Classes: ScientificWork · Source · Institution · Topic · Funder
    # ===========================================================================

    # --- ScientificWork (core node of the graph) --------------------------------
    # Reuses bibo:Document; aligned to schema:ScholarlyArticle and foaf:Document.
    # We declare a local subclass to keep our graph self-contained.
    work = BIBO.Document
    _add_class(work, "ScientificWork", "Scholarly documents like journal articles, books, datasets, and theses",
               subClassOf=[SCHEMA.CreativeWork], equivalence=[FOAF.Document])

    # --- Source ------------------------------------------------------------------
    # I only include sources that are considered Journals. OpenAlex sources also consist of "conference",
    # "ebook platform", "repository", and "book series" which I will not include for simplicity.
    journal = BIBO.Journal
    _add_class(journal, "Journal", "A scholarly journal that publishes scientific work.")

    # --- Institution -------------------------------------------------------------
    institution = ORG.Organization
    _add_class(institution, "Institution", "An organization that produces the work",
               equivalence=[FOAF.Organization, SCHEMA.Organization, WD.Q43229])

    # Add subclasses for different types of institutions (education, healthcare, company, government, nonprofit, facility)
    _add_specific_class(SCHEMA.EducationalOrganization, institution, "Educational Institution",
                        equivalence=[WD.Q2385804])  # Education
    _add_specific_class(SCHEMA.MedicalOrganization, institution, "Healthcare Institution",
                        equivalence=[WD.Q4287745])  # Healthcare
    _add_specific_class(SCHEMA.Corporation, institution, "A Corporation", equivalence=[WD.Q783794])  # Company
    _add_specific_class(SCHEMA.GovernmentOrganization, institution, "Government Institution",
                        equivalence=[WD.Q7188])  # Government
    _add_specific_class( SCITAX.NonProfit, institution, "Non-Profit Institution", equivalence=[WD.Q163740])  # Nonprofit
    _add_specific_class( SCITAX.Facility, institution, "Healthcare Institution", equivalence=[WD.Q13226383])  # Facility

    # --- Topic -------------------------------------------------------------------
    # OpenAlex 4-level taxonomy: Domain > Field > Subfield > Topic
    topic = SKOS.Concept
    subfield =  SCITAX.Subfield
    field =  SCITAX.Field
    domain =  SCITAX.Domain
    _add_class(topic, "Topic", "A topic of work")
    _add_class(subfield, "Subfield", "A subfield of a field")
    _add_class(field, "Field", "A field of study", equivalence=[WD.Q2267705])
    _add_class(domain, "Domain", "A domain of field of study", equivalence=[WD.Q1047113])

    # --- Funder ------------------------------------------------------------------
    fund = SCHEMA.FundingAgency
    _add_class(fund, "Funder", "An organisation that funds the research reported in a work.", subClassOf=[institution],
               equivalence=[WD.Q5509032])

    # ===========================================================================
    # PART 3 — OPENALEX DATATYPE PROPERTIES (on ScientificWork)
    # ===========================================================================

    # Core bibliographic
    _add_property(DCT.title, OWL.DataProperty, work, RDF.langString, "title", "The display title of the work.")
    _add_property(BIBO.doi, OWL.DataProperty, work, XSD.anyURI, "doi", "The DOI of the work as a full URL.")
    _add_property(DCT.language, OWL.DataProperty, work, XSD.language, "language",
                  "BCP-47 language tag of the work (e.g. 'en').")
    # _add_property(DCT.type, OWL.DataProperty, work, RDF.langString,  "work type", "OpenAlex work type: article, book, dataset, thesis, etc.")
    _add_property(SCHEMA.datePublished, OWL.DataProperty, work, XSD.date, "publication date",
                  "ISO-8601 publication date.")
    _add_property(SCHEMA.copyrightYear, OWL.DataProperty, work, XSD.gYear, "publication year",
                  "Four-digit publication year.")

    # Open-access status
    _add_property(SCHEMA.isAccessibleForFree, OWL.DataProperty, work, XSD.boolean, "is open access",
                  "True when the work is openly accessible.")

    # Citation metrics
    # _add_property(SCHEMA.citation, OWL.DataProperty, work, XSD.integer, "cited by count", "Total number of citing works.")

    # Country coverage (ISO-3166-1 alpha-2 codes; multi-valued literal)
    # _add_property(SCHEMA.countryOfOrigin, OWL.DataProperty, work, RDF.langString, "country code", "ISO-3166-1 alpha-2 country code of an affiliated institution.")

    # Source datatype properties
    _add_property(SCHEMA.name, OWL.DataProperty, journal, RDF.langString, "source name", "Display name of the source.")
    _add_property(BIBO.issn, OWL.DataProperty, journal, XSD.string, "ISSN-L", "Linking ISSN of the journal.")
    # _add_property(SCHEMA.isAccessibleForFree, journal, XSD.boolean, "source is OA", "True when the source is fully open-access.")

    # Institution datatype properties
    _add_property(SCHEMA.name, OWL.DataProperty, institution, RDF.langString, "institution name", "Display name.")
    _add_property(ORG.identifier, OWL.DataProperty, institution, XSD.anyURI, "ROR ID",
                  "Research Organization Registry identifier URI.")
    _add_property(SCHEMA.countryOfOrigin, OWL.DataProperty, institution, RDF.langString, "country code",
                  "ISO-3166-1 alpha-2 country code of the institution.")
    _add_property(RDFS.type, OWL.DataProperty, institution, XSD.anyURI, "institution type",
                  "education, healthcare, company, government, nonprofit, facility.")

    # Topic datatype properties
    _add_property(SKOS.prefLabel, OWL.DataProperty, topic, RDF.langString, "topic name", "Display name of the topic.")
    # _add_property(SCHEMA.Rating, OWL.DataProperty, topic, XSD.decimal, "topic score", "Relevance score of this topic assignment to the work (0–1).")

    # Funder datatype properties
    _add_property(SCHEMA.name, OWL.DataProperty, fund, XSD.string, "funder name", "Display name of the funder.")

    # ===========================================================================
    # PART 4 — OPENALEX OBJECT PROPERTIES
    # ===========================================================================

    # Work → isPartOf → Source
    _add_property(DCT.isPartOf, OWL.ObjectProperty, work, journal, "is part of",
                  "Links a work to the source (journal) in which it appears.", inv=DCT.hasPart,
                  equivalence=[SCHEMA.isPartOf])

    _add_property(DCT.hasPart, OWL.ObjectProperty, journal, work, "has part", "Links a source to the works it hosts.",
                  equivalence=[SCHEMA.hasPart])

    # Institution → produced → Work
    _add_property(SCHEMA.producer, OWL.ObjectProperty, institution, work, "produced by",
                  "Links an institution to works whose authors are affiliated with it.")

    # Work → primaryTopic → Topic
    _add_property(FOAF.primaryTopic, OWL.ObjectProperty, work, topic, "has primary topic",
                  "Links a work to its single highest-confidence OpenAlex topic.", inv=FOAF.isPrimaryTopicOf)

    _add_property(FOAF.isPrimaryTopicOf, OWL.ObjectProperty, topic, work, "is primary topic of", inv=FOAF.primaryTopic)

    # Work → topic → Topic (secondary topics)
    _add_property(FOAF.topic, OWL.ObjectProperty, work, topic, "has topic",
                  "Links a work to any of its assigned OpenAlex topics.", inv=SCHEMA.subjectOf, subPropOf=[DCT.subject])

    _add_property(SCHEMA.subjectOf, OWL.ObjectProperty, topic, work, "is topic of", inv=FOAF.topic)

    # Funder → funds → Scientific Work
    _add_property(SCHEMA.funder, OWL.ObjectProperty, fund, work, "funds",
                  "Links a funder to the works it has supported", inv=SCHEMA.fundedBy)

    _add_property(FOAF.fundedBy, OWL.ObjectProperty, work, fund, "is funded by", inv=SCHEMA.funder)

    # Topic hierarchy: Topic → broaderTopic → Subfield → broader → Field → broader → Domain
    # _add_property(SKOS.broader, OWL.ObjectProperty, topic, subfield,"in subfield","Relates a topic to its parent subfield.")
    # _add_property(SKOS.narrower, OWL.ObjectProperty, subfield, topic,"has topic","Relates a subfield to its child topic.")
    #
    # _add_property(SKOS.broader, OWL.ObjectProperty, subfield, field, "in field", "Relates a subfield to its parent field.")
    # _add_property(SKOS.narrower, OWL.ObjectProperty, field, subfield, "has field", "Relates a field to its subfield.")
    #
    # _add_property(SKOS.broader, OWL.ObjectProperty, field, domain, "in domain", "Relates a field to its parent domain.")
    # _add_property(SKOS.narrower, OWL.ObjectProperty, domain, field, "has domain", "Relates a domain to its field.")

    # Institution → locatedIn → Country  (for geographic analytics)
    # _add_property(SCHEMA.location, institution, SCHEMA.Country, "located in", "Links an institution to its geographic location.")

    # ===========================================================================
    # PART 5 — THE BRIDGE: mapping ScientificWork ↔ SDG concepts
    # ===========================================================================

    # Work → addressesGoal → sdg:Goal
    _add_property( SCITAX.addressesGoal, OWL.ObjectProperty, work, SDGO.Goal, "addresses SDG goal",
                  "Asserts that a work is relevant to a UN SDG Goal.", inv= SCITAX.goalAddressedBy)
    _add_property( SCITAX.goalAddressedBy, OWL.ObjectProperty, SDGO.Goal, work, "goal is addressed by work",
                  inv= SCITAX.addressesGoal)

    # Work → addressesTarget → sdg:Target  (finer-grained linkage)
    _add_property( SCITAX.addressesTarget, OWL.ObjectProperty, work, SDGO.Target, "addresses SDG target",
                  "Asserts that a work is relevant to a specific UN SDG Target.", inv= SCITAX.targetAddressedBy)
    _add_property( SCITAX.targetAddressedBy, OWL.ObjectProperty, SDGO.Goal, work, "target is addressed by work",
                  inv= SCITAX.addressesTarget)

    # Work → addressesIndicator → sdg:Indicator (finest-grained; optional)
    _add_property( SCITAX.addressesIndicator, OWL.ObjectProperty, work, SDGO.Indicator, "addresses SDG indicator",
                  "Asserts that a work addresses a measurable SDG Indicator.", inv= SCITAX.indicatorAddressedBy)
    _add_property( SCITAX.indicatorAddressedBy, OWL.ObjectProperty, SDGO.Goal, work, "indicator is addressed by work",
                  inv= SCITAX.addressesIndicator)

    # Work → addressesSeries → sdg:Series (optional; for works that are relevant to a specific series of indicators, e.g. on climate change adaptation)
    _add_property( SCITAX.addressesSeries, OWL.ObjectProperty, work, SDGO.Series, "addresses SDG series",
                  "Asserts that a work addresses a specific series of SDG Indicators.", inv= SCITAX.seriesAddressedBy)
    _add_property( SCITAX.seriesAddressedBy, OWL.ObjectProperty, SDGO.Goal, work, "series is addressed by work",
                  inv= SCITAX.addressesSeries)

    # Confidence score on the SDG assignment (reified via a blank node or
    # named graph in practice; declared here as a datatype property for
    # simple triple-level annotation):
    # _add_property(SCHEMA.Rating, work, XSD.decimal,"SDG relevance score","A confidence score (0–1) for the work-to-SDG mapping, e.g. from a classifier.")

    # ===========================================================================
    # PART 6 — PROVENANCE (PROV-O)
    # Captures the evidence trail behind each SDG classification so the graph
    # can answer "why was this work linked to this SDG?" not just "was it?".
    #
    # Core pattern:
    #
    # bibo:document  ← prov:used ─── scitax:ClassificationActivity
    # ↑                                          │
    # prov:wasDerivedFrom               prov:wasGeneratedBy
    # │                                          ↓
    # scitax:SDGAssignment ──── prov:used ──► scitax:EvidenceConcept
    #
    # scitax:SDGAssignment  — the reified SDG link (work → goal/target/indicator)
    # scitax:ClassificationActivity — one LinkedSDG API call for one work
    # scitax:EvidenceConcept — a single matched concept from the concepts[] block
    # ===========================================================================

    # --- scitax:SDGAssignment -------------------------------------------------
    sdg_assignment =  SCITAX.SDGAssignment
    comm = "A reified assertion that a work addresses a particular SDG Goal, Target, or Indicator, produced by a ClassificationActivity and evidenced by one or more EvidenceConcepts."
    _add_class(sdg_assignment, "SDG Assignment", comm, subClassOf=[PROV.Entity])

    # --- scitax:ClassificationActivity ----------------------------------------
    # One instance per LinkedSDG API call (i.e. one per work processed).
    # Subclasses prov:Activity so all PROV-O activity properties apply.
    classification_activity =  SCITAX.ClassificationActivity
    comm = "A LinkedSDG API call that classifies a single document against the SDG framework. Records the URL queried, the tool version, and the timestamp."
    _add_class(classification_activity, "Classification Activity", comm, subClassOf=[PROV.Activity])

    # --- scitax:EvidenceConcept -----------------------------------------------
    # One instance per entry in the concepts[] array of the LinkedSDG response.
    # Carries the matched phrase, the quote context, and the controlled vocab URIs
    # (EuroVoc / UNBIS) that grounded the match.
    evidence_concept =  SCITAX.EvidenceConcept
    comm = "A controlled-vocabulary concept matched in a document by the LinkedSDG classifier. Subclasses both prov:Entity (provenance role) and skos:Concept (vocabulary role)."
    _add_class(evidence_concept, "Evidence Concept", comm, subClassOf=[PROV.Entity, SKOS.Concept])

    # ---------------------------------------------------------------------------
    # PROV-O object properties
    # ---------------------------------------------------------------------------

    # 1. Work → hasAssignment → SDGAssignment
    # Entry point into the provenance graph. Every SDG claim against a work
    # is reached via this property. The shortcut openalex:addressesGoal etc.
    # remains for simple queries; hasAssignment is for full provenance traversal.
    _add_property( SCITAX.hasAssignment, OWL.ObjectProperty, work, sdg_assignment, "has SDG assignment",
                  "Links a work to each of its reified SDG classification claims", inv= SCITAX.isAssignmentOf)
    _add_property( SCITAX.isAssignmentOf, OWL.ObjectProperty, sdg_assignment, work, "is SDG assignment of",
                  "Links an SDG Assignment back to the work it classifies.", inv= SCITAX.hasAssignment)

    # 2. ClassificationActivity → prov:used → ScientificWork (the input document)
    _add_property(PROV.used, OWL.ObjectProperty, classification_activity, work, "used",
                  "Links the classification activity to the document it processed.")

    # 3. SDGAssignment → prov:wasGeneratedBy → ClassificationActivity
    _add_property(PROV.wasGeneratedBy, OWL.ObjectProperty, sdg_assignment, classification_activity, "was generated by",
                  "Links an SDG assignment to the classification activity that produced it.")

    # 4. SDGAssignment → prov:used → EvidenceConcept (the evidence that caused the assignment)
    _add_property(PROV.used, OWL.ObjectProperty, sdg_assignment, evidence_concept, "used",
                  "Links an SDG assignment to the concept(s) that evidenced it.")

    # 5. EvidenceConcept → prov:wasDerivedFrom → ScientificWork
    _add_property(PROV.wasDerivedFrom, OWL.ObjectProperty, evidence_concept, work, "was derived from",
                  "Links an evidence concept back to the source document it was matched in.")

    # 6. SDGAssignment into the UNSDG hierarchy
    _add_property( SCITAX.toGoal, OWL.ObjectProperty, sdg_assignment, SDGO.Goal, "to goal",
                  "Connects an SDGAssignment to the unsdgio:Goal it claims the work addresses. This is the property that joins the provenance graph to the UN SDG hierarchy.",
                  inv= SCITAX.hasAssignmentForGoal)
    _add_property( SCITAX.hasAssignmentForGoal, OWL.ObjectProperty, SDGO.Goal, sdg_assignment, "has assignment for goal",
                  "Inverse of scitax:toGoal — links a Goal to all SDGAssignments claiming works address it.",
                  inv= SCITAX.toGoal)
    _add_property( SCITAX.toTarget, OWL.ObjectProperty, sdg_assignment, SDGO.Target, "to target",
                  "Connects an SDGAssignment to the unsdgio:Target it claims the work addresses.",
                  inv= SCITAX.hasAssignmentForTarget)
    _add_property( SCITAX.hasAssignmentForTarget, OWL.ObjectProperty, SDGO.Target, sdg_assignment,
                  "has assignment for target", "Inverse of scitax:toTarget.", inv= SCITAX.toTarget)
    _add_property( SCITAX.toIndicator, OWL.ObjectProperty, sdg_assignment, SDGO.Indicator, "to indicator",
                  "Connects an SDGAssignment to the unsdgio:Indicator it claims the work addresses.",
                  inv= SCITAX.hasAssignmentForIndicator)
    _add_property( SCITAX.hasAssignmentForIndicator, OWL.ObjectProperty, SDGO.Indicator, sdg_assignment, "to indicator",
                  "Inverse of scitax:toIndicator.", inv= SCITAX.toIndicator)
    _add_property( SCITAX.toSeries, OWL.ObjectProperty, sdg_assignment, SDGO.Series, "to series",
                  "Connects an SDGAssignment to the unsdgio:Series it claims the work addresses.",
                  inv= SCITAX.hasAssignmentForSeries)
    _add_property( SCITAX.hasAssignmentForSeries, OWL.ObjectProperty, SDGO.Series, sdg_assignment, "to series",
                  "Inverse of scitax:toSeries.", inv= SCITAX.toSeries)

    # ---------------------------------------------------------------------------
    # PROV-O datatype properties
    # ---------------------------------------------------------------------------

    # --- On ClassificationActivity ----------------------------------------------
    _add_property(PROV.wasGeneratedAtTime, OWL.DataProperty, classification_activity, XSD.dateTime,
                  "generated at time", "The time the classification activity was performed.")

    # --- On SDGAssignment -------------------------------------------------------
    _add_property(SCITAX.relevanceScore, OWL.DataProperty, sdg_assignment, XSD.decimal, "SDG relevance score",
                  "A confidence score (0–1) for the work-to-SDG mapping, e.g. from a classifier.",
                  subPropOf=[SCHEMA.value])

    # --- On EvidenceConcept -----------------------------------------------------
    _add_property(SCHEMA.name, OWL.DataProperty, evidence_concept, XSD.anyURI, "concept name",
                  "The name of the matched concept.")
    _add_property( SCITAX.matchedPhrase, OWL.DataProperty, evidence_concept, RDF.langString, "matched phrase",
                  "The matched phrase.")
    _add_property( SCITAX.quoteContext, OWL.DataProperty, evidence_concept, RDF.langString, "quote context",
                  "The context in which the phrase was matched.")
    _add_property( SCITAX.conceptWeight, OWL.DataProperty, evidence_concept, XSD.decimal, "concept weight",
                  "The weight of the concept in the classification.")
    _add_property(SKOS.exactMatch, OWL.DataProperty, evidence_concept, SKOS.Concept, "exact match",
                  "Links the evidence concept to its corresponding EuroVoc or UNBIS controlled vocabulary URI.")

    # ===========================================================================
    # Serialise
    # ===========================================================================
    output_path = "data/SciGraph4UNSDG_ontology.ttl"
    g.serialize(output_path, format="turtle")
    print(f"Ontology written to {output_path}  ({len(g)} triples)")