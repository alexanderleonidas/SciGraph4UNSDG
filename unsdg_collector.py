import requests
from helper_funcs import save_json

# Set the UN SDG API endpoint
unsdg_api = "https://unstats.un.org/SDGAPI/v1/sdg/"

# Function to get data from the API
def get_data(api: str, endpoint: str):
    params = {"includechildren": 'true'}
    url = api + endpoint
    res = requests.get(url, params=params) # Make a GET request to the API
    res = res.json() # Convert the response to JSON
    return res

# Get and save the data for the Goals, Indicators, Series, and Targets
def save_unsdg_data():
    for enpoint in ["Goal", "Indicator", "Series", "Target"]:
        response = get_data(unsdg_api, enpoint+"/List")
        # print(f"Columns for: {enpoint}", response.keys())
        save_json(response, f"UNSDG/unsdg_{enpoint.lower()}_list")
        print(f"Saved data to data/UNSDG/unsdg_{enpoint.lower()}_list JSON file.")

if __name__ == "__main__":
    save_unsdg_data()
