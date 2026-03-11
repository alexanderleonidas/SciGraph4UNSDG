from create_ontology import create_ontology
from create_knowledge_graph import create_kg
from linkedsdg_classifier import save_classifications
from openalex_collector import extract_openalex_data
from unsdg_collector import save_unsdg_data

if __name__ == '__main__':
    # Get and save the UNSDG data
    # save_unsdg_data()

    # Get and save the OpenAlex data
    # Not all OpenAlex works have PDFs, and not all are accessible by LinkedSDG
    # so make sure to set num_works_per_sdg to a high number to ensure you have enough classified works for the graph
    # extract_openalex_data(num_works_per_sdg=300, seed=9, citation_expansion=True, min_citations_in_seed=2)

    # Extract SDG classification and save the data
    # save_classifications(num_works=100)

    # Create the graph from the classified data
    create_ontology()
    create_kg()