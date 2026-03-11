import requests
from urllib.parse import quote

# Function to transform a link into a format suitable for the LinkedSDG API
def transform_link(link: str) -> str:
    return link.replace(":", "%3A").replace("/", "%2F")

# Function to classify a document using the LinkedSDG API
def query_api(document_link: str=None, document_text: str=None) -> dict:
    api = "http://linkedsdg.officialstatistics.org/swaggerapi"
    # params = {"text": "true", "geoAreas": "true", "concepts": "true", "sdgs": "true"}
    params = {"text": "true", "geoAreas": "true", "concepts": "true", "sdgs": "true"}
    headers = {"Content-Type": "application/json"}
    if not document_link and document_text:
        url = api + "/file"
        raise NotImplementedError("Document text integration implemented yet")
    elif document_link and not document_text:
        url = api + "/url" + "?url=" + transform_link(document_link)
        payload = {}
    else:
        raise ValueError("Either document_link or document_text must be provided.")
    response = requests.post(url, params=params, headers=headers)
    return response.json()

# Extract all the relevant information from the API response
def extract_information(response: dict):
    print(response.keys())
    # print(response['geoAreas'])
    # print(response['concepts'])
    print(response['sdgs']["children"][0]['keywords'])

    for goal in response['sdgs']['children']:
        goal_id = goal['id']
        for target in goal['children']:
            target_id = target['id']
            for indicator in target['children']:
                indicator_id = indicator['id']
                for series in indicator['children']:
                    series_id = series['id']
                    scored_value = series['value']
                    print(f"Goal ID: {goal_id}, Target ID: {target_id}, Indicator ID: {indicator_id}, Series ID: {series_id}, Scored Value: {scored_value}")

l = "https://www.frontiersin.org/journals/water/articles/10.3389/frwa.2024.1267164/full"
res = query_api(document_link=l)
extract_information(res)