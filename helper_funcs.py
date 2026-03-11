import os
import json

# ===========================================================================
# General Helper Functions
# ===========================================================================

def load_env(file_path='.env'):
    """
    Function to load environment variables from a .env file
    :param file_path: Path to the .env file
    """
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

def load_json(file_path: str) -> dict:
    """
    Load a JSON file from the specified path.
    :param file_path: Path to the JSON file
    :return: JSON object
    """
    if not os.path.exists(f"{file_path}.json"):
        raise FileNotFoundError(f"JSON file not found: {file_path}.json")
    with open(f"{file_path}.json", 'r') as f:
        return json.load(f)

def save_json(data: dict|list[dict], file_name: str):
    """
    Save a JSON object to a file in the `data/` directory. Creates directories if needed.
    :param data: JSON object to save.
    :param file_name: Name of the file to save.
    """
    json_str = json.dumps(data, indent=4)
    # Create the data directory if it doesn't exist
    if not os.path.exists("data/"):
        os.makedirs("data/")
    # Create directories if needed
    if '/' in file_name:
        dir_name = file_name.split('/')
        if dir_name[0] == 'data':
            dir_name = dir_name[1:]
            file_name = file_name.replace('data/', '')
        if len(dir_name) == 2:
            dir_name = dir_name[0]
            if not os.path.exists(f"data/{dir_name}"):
                os.makedirs(f"data/{dir_name}")
        else:
            raise ValueError("Invalid file name format. Use only one slash to separate directories.")
    with open(f"data/{file_name}.json", "w") as f:
        f.write(json_str)

# ===========================================================================
# UNSDG Helper Functions
# ===========================================================================

def load_raw_unsdg_data() -> tuple[dict, dict, dict, dict]:
    """
    Load the UNSDG data
    :return: JSON objects for Goals, Targets, Indicators, and Series
    """
    data_dir = "data/UNSDG/"
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Directory {data_dir} not found. Please run unsdg_collector.py first.")
    goals = load_json(data_dir+"unsdg_goal_list")
    targets = load_json(data_dir + "unsdg_target_list")
    indicators = load_json(data_dir+"unsdg_indicator_list")
    series = load_json(data_dir+"unsdg_series_list")
    return goals, targets, indicators, series


# ===========================================================================
# OpenAlex Helper Functions
# ===========================================================================

def load_raw_openalex_data() -> tuple[list[dict], list[dict], list[tuple[str, str]]]:
    """
    Load the relevant OpenAlex data, including the LinkedSDG classifications
    :return: JSON object of OpenAlex data
    """
    oa_data_dir = "data/OpenAlex/"
    lsdg_data_dir = "data/LinkedSDG/"
    if not os.path.exists(oa_data_dir) or not os.path.exists(lsdg_data_dir):
        raise FileNotFoundError(f"Directory {oa_data_dir}, {lsdg_data_dir} not found. Please run both {{openalex}}{{unsdg}}_collector.py first.")

    # Extract all the OpenAlex works that have been extracted
    oa_works_expanded = load_json(f"{oa_data_dir}extracted_works_expanded")
    oa_works_sdg = load_json(f"{oa_data_dir}extracted_works_sdg")
    oa_sdg = load_json(f"{oa_data_dir}/bin/sdgs")

    # Extract all the LinkedSDG classifications of the OpenAlex works
    classifications_expanded = load_json(f"{lsdg_data_dir}classifications_expanded")
    classifications_sdg = load_json(f"{lsdg_data_dir}classifications_sdg")

    # Get all the OpenAlex IDs of the works that have been classified
    expanded_ids = [c["openalex_id"] for c in classifications_expanded]
    sdg_ids = [c["openalex_id"] for c in classifications_sdg]

    # Get the work objects for each set of classified works
    expanded_works = [w for w in oa_works_expanded if w["id"] in expanded_ids]
    sdg_works = [w for w in oa_works_sdg if w["id"] in sdg_ids]

    # Add the classification scores to the work objects
    for c in expanded_works:
        c["flat_series_scores"] = next((item["flat_series"] for item in classifications_expanded if item['openalex_id'] == c["id"]), None)
    for c in sdg_works:
        c["flat_series_scores"] = next((item["flat_series"] for item in classifications_sdg if item['openalex_id'] == c["id"]), None)

    # Extract the OpenAlex equivalent URIs for each SDG goal
    oa_sdg_goals_links = [(s["ids"]["openalex"].split("/")[-1], s["ids"]["wikidata"].split("/")[-1]) for s in oa_sdg["results"]]  # tuple of (OpenAlex ID, Wikidata ID)

    return expanded_works, sdg_works, oa_sdg_goals_links