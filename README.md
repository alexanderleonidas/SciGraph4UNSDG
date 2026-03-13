# A FAIR Knowledge Graph for Mapping Research to the UN Sustainable Development Goals
SciGraph4UNSDG is a knowledge graph system designed to map scientific research to the United Nations Sustainable Development Goals (UN SDGs). The project implements FAIR (Findable, Accessible, Interoperable, Reusable) principles to create a structured, machine-readable representation of research contributions aligned with the UN's 17 SDGs.

## Features

- Knowledge graph construction for research-to-SDG mapping using RDF/OWL
- FAIR data principles implementation with provenance tracking via PROV-O
- Integration with OpenAlex scholarly database and UN SDG metadata
- Automated SDG classification with relevance scoring and concept-level evidence uing LinkedSDG
- SPARQL-based analysis and querying over 1.5M+ triples
- Controlled vocabulary alignment with EuroVoc and UNBIS thesauri

## Installation

```bash
pip install -r requirements.txt
````
Make sure to add your OpenAlex API key to the `.env` file.

# Usage
Run the `main.py` script to generate the knowledge graph.

```bash
python main.py
```

This will:
 1. Collect UN SDG data (goals, targets, series)
 2. Fetch research works from OpenAlex
 3. Classify works against the SDGs using LinkedSDG
 4. Build and serialize the knowledge graph to `data/SciGraph4UNSDG.ttl`

Use `sparql_queries.ipynb` to run analytical SPARQL queries over the constructed graph

# Requirements
- Python 3.9+
- Dependencies in requirements.txt

# Project Structure
```
SciGraph4UNSDG/
├── data/                           # Data files and output TTL graph (this will be created when you run `main.py`)
├── main.py                         # Main script to run the full pipeline
├── helper_funcs.py                 # Shared utility functions
├── create_knowledge_graph.py       # Populates the RDF knowledge graph with OpenAlex and UN SDG data
├── create_ontology.py              # Defines the OWL class and property ontology (scitax vocabulary)
├── linkedsdg_classifier.py         # Classifies OpenAlex works against SDG targets with scoring
├── unsdg_collector.py              # Downloads and parses UN SDG goals, targets, and series metadata
├── openalex_collector.py           # Fetches research works and metadata from the OpenAlex API
└── sparql_queries.ipynb            # Example SPARQL queries for knowledge graph analysis and reporting
```

# Ontology & Vocabularies
The project defines a custom `scitax:` namespace for the schema structure and a `sci:` namespace for instances of classification assignments. It extends standard ontologies:

| Prefix    | Purpose                                                  |
|-----------|----------------------------------------------------------|
| `prov:`   | Provenance of classification activities (PROV-O)         |
| `skos:`   | SDG labels and controlled vocabulary alignment           |
| `bibo:`   | Bibliographic document typing                            |
| `foaf:`   | Agent and topic descriptions                             |
| `schema:` | Concept names and metadata                             |

## Contact
For questions or collaboration opportunities, please open an issue on GitHub.

## Acknowledgments
This project supports the United Nations Sustainable Development Goals and promotes open science through FAIR data practices.

