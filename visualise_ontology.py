from graphviz import Digraph

dot = Digraph(comment="SciGraph4UNSDG Ontology with Provenance")
dot.attr(rankdir="TB", size="12,10")
dot.attr('node', shape='plain', fontname='Arial')
dot.attr('edge', fontname='Arial')

# ----- Color palette -----
sdg_color      = "#E0F7FA"   # light cyan
openalex_color = "#FFF3E0"   # light orange
prov_color     = "#FFF2CC"   # light yellow

def sdg_label(class_name, attributes):
    rows = [f'<tr><td colspan="2"><b>{class_name}</b></td></tr>']
    for attr, typ in attributes:
        rows.append(f'<tr><td align="left">{attr}</td><td align="left">{typ}</td></tr>')
    return f'''<<table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="{sdg_color}">
        {''.join(rows)}
    </table>>'''

def oa_label(class_name, attributes):
    rows = [f'<tr><td colspan="2"><b>{class_name}</b></td></tr>']
    for attr, typ in attributes:
        rows.append(f'<tr><td align="left">{attr}</td><td align="left">{typ}</td></tr>')
    return f'''<<table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="{openalex_color}">
        {''.join(rows)}
    </table>>'''

def prov_label(class_name, attributes):
    rows = [f'<tr><td colspan="2"><b>{class_name}</b></td></tr>']
    for attr, typ in attributes:
        rows.append(f'<tr><td align="left">{attr}</td><td align="left">{typ}</td></tr>')
    return f'''<<table border="0" cellborder="1" cellspacing="0" cellpadding="4" bgcolor="{prov_color}">
        {''.join(rows)}
    </table>>'''

# ----- UN SDG cluster (left) -----
with dot.subgraph(name='cluster_sdg') as c:
    c.attr(label='UN SDG', style='filled', color='lightgrey', fontname='Arial')
    c.node("Goal", sdg_label("sdgo:Goal", [("rdf:label", "langString")]))
    c.node("Target", sdg_label("sdgo:Target", [("rdf:label", "langString")]))
    c.node("Indicator", sdg_label("sdgo:Indicator", [("rdf:label", "langString")]))
    c.node("Series", sdg_label("sdgo:Series", [("rdf:label", "langString")]))

    # SDG hierarchy
    c.edge("Goal", "Target", label="sdgo:hasTarget")
    c.edge("Target", "Indicator", label="sdgo:hasIndicator")
    c.edge("Indicator", "Series", label="sgo:hasSeries")

# ----- OpenAlex cluster (middle) -----
with dot.subgraph(name='cluster_openalex') as c:
    c.attr(label='OpenAlex', style='filled', color='lightgrey', fontname='Arial')
    c.node("ScientificWork", oa_label("ScientificWork(bibo:Document)", [
        ("dct:title", "xsd:string"), ("bibo:doi", "xsd:anyURI"), ("dct:language", "xsd:language"),
        ("schema:datePublished", "xsd:date"), ("schema:copyrightYear", "xsd:gYear"), ("schema:isOpenAccess", "xsd:boolean")
    ]))
    c.node("Journal", oa_label("bibo:Journal", [("schema:name", "xsd:string"), ("bibo:issn", "xsd:string")]))
    c.node("Institution", oa_label("Institution(org:Organisation)", [("schema:name", "xsd:string"), ("org:identifier", "xsd:anyURI"), ("schema:countryOfOrigin", "xsd:string")]))
    c.node("Topic", oa_label("Topic(skos:Concept)", [("skos:prefLabel", "langString")]))
    c.node("SubField", oa_label("scitax:SubField", [("skos:prefLabel", "langString")]))
    c.node("Field", oa_label("scitax:Field", [("skos:prefLabel", "langString")]))
    c.node("Domain", oa_label("scitax:Domain", [("skos:prefLabel", "langString")]))
    c.node("Funder", oa_label("schema:FundingAgency", [("schema:name", "langString")]))

    # OpenAlex relationships
    c.edge("Institution", "ScientificWork", label="prov:produces")
    c.edge("Funder", "ScientificWork", label="foaf:funds")
    c.edge("ScientificWork", "Journal", label="foaf:isPartOf")
    c.edge("ScientificWork", "Topic", label="foaf:primaryTopic")
    c.edge("Topic", "SubField", label="skos:broader")
    c.edge("SubField", "Field", label="skos:broader")
    c.edge("Field", "Domain", label="skos:broader")

# ----- Provenance cluster (right) -----
with dot.subgraph(name='cluster_provenance') as c:
    c.attr(label='Provenance', style='filled', color='lightgrey', fontname='Arial')
    c.node("SDGAssignment", prov_label("SDGAssignment", [("scitax:relevanceScore", "xsd:decimal")]))
    c.node("ClassificationActivity", prov_label("ClassificationActivity", [("prov:generatedAtTime", "xsd:dateTime")]))
    c.node("EvidenceConcept", prov_label("EvidenceConcept", [("scitax:matchedPhrase", "langString"), ("scitax:quoteContext", "langString"), ("scitax:conceptWeight", "xsd:decimal"), ("skos:exactMatch", "xsd:anyURI")]))

# ----- Invisible edges to align the three columns -----
dot.edge("Goal", "ScientificWork", style="invis")
dot.edge("ScientificWork", "SDGAssignment", style="invis")

# ----- Bridge edges (shortcut SDG links) -----
dot.edge("ScientificWork", "Goal", label="<<b>scitax:addresses<br/>Goal</b>>", color="red", fontcolor="red")
dot.edge("ScientificWork", "Target", label="<<b>scitax:addresses<br/>Target</b>>", color="red", fontcolor="red")
dot.edge("ScientificWork", "Indicator", label="<<b>scitax:addresses<br/>Indicator</b>>", color="red", fontcolor="red")
dot.edge("ScientificWork", "Series", label="<<b>scitax:addresses<br/>Series</b>>", color="red", fontcolor="red")

# ----- Provenance edges (blue) -----
# Work → hasAssignment → SDGAssignment
dot.edge("ScientificWork", "SDGAssignment", label="<<b>scitax:hasAssignment</b>>", color="red", fontcolor="red")
# SDGAssignment → wasGeneratedBy → ClassificationActivity
dot.edge("SDGAssignment", "ClassificationActivity", label="prov:wasGeneratedBy", color="black", fontcolor="black")
# ClassificationActivity → used → ScientificWork (the input document)
dot.edge("ClassificationActivity", "ScientificWork", label="prov:used", color="orange", fontcolor="orange")
# SDGAssignment → used → EvidenceConcept
dot.edge("SDGAssignment", "EvidenceConcept", label="prov:used", color="black", fontcolor="black")
# EvidenceConcept → wasDerivedFrom → ScientificWork
dot.edge("EvidenceConcept", "ScientificWork", label="scitax:wasDerivedFrom", color="purple", fontcolor="purple")
# SDGAssignment → toGoal / toTarget / toIndicator / toSeries (linking to SDG hierarchy)
dot.edge("SDGAssignment", "Goal", label="scitax:toGoal", color="blue", fontcolor="blue")
dot.edge("SDGAssignment", "Target", label="scitax:toTarget", color="blue", fontcolor="blue")
dot.edge("SDGAssignment", "Indicator", label="scitax:toIndicator", color="blue", fontcolor="blue")
dot.edge("SDGAssignment", "Series", label="scitax:toSeries", color="blue", fontcolor="blue")

# Render
dot.render("SciGraph4UNSDG_ontology", view=True, format='png')