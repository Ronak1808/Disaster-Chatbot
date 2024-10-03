from dotenv import load_dotenv
import requests
import json
import pathlib
load_dotenv()
import os
import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st
HERE_API_KEY = os.getenv("HERE_API_KEY")
media = pathlib.Path(__file__).parents[1] / "BTP"
#Function to search for earthquake detail 
from country_bounding_boxes import (
      country_subunits_containing_point,
      country_subunits_by_iso_code
    )


def get_current_date():
    # Get current date in YYYY-MM-DD format
    """Returns the current date as string. """
    return datetime.utcnow().strftime('%Y-%m-%d')

def check_earthquake_alert(min_latitude : float = None, max_latitude : float = None, min_longitude : float = None, max_longitude : float = None,  latitude : float = None,  longitude : float = None, start_date : str = None, end_date : str = None, radius_km : float = 1000, min_magnitude : float = 3):
    print(locals())
    """determine the earthquake details in the given latitude and longitude within a given radius which are having magnitude greater than or equal to min_magnitude.
    Args:
        latitude : Latitude of the place (optional if using bounding box).
        longitude : Longitude of the place (optional if using bounding box).
        min_latitude : Minimum latitude of the bounding box (optional).
        min_longitude : Minimum longitude of the bounding box (optional).
        max_latitude : Maximum latitude of the bounding box (optional).
        max_longitude : Maximum longitude of the bounding box (optional).
        radius_km : Radius range from the place where earthquake details should be included (default is 1000 km).
        min_magnitude : Minimum magnitude of the earthquake to be included (default is 3).
        start_date : Start date (YYYY-MM-DD) from which earthquake details are fetched.
        end_date : End date (YYYY-MM-DD) up to which earthquake details are fetched.
    Returns: 
        A dictionary containing earthquake details if found any. And error in case of network errr.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    print(f"Start data is {start_date} end date is {end_date}")
    params = {
        "format": "geojson",
        "minmagnitude": min_magnitude,
        "starttime" : datetime.utcnow().strftime('%Y-%m-%d') if start_date is None else start_date,
        "endtime" : (datetime.utcnow() + timedelta(weeks=1)).strftime('%Y-%m-%d') if end_date is None else end_date,
        "limit" : 10
    }
    if min_latitude is not None and min_longitude is not None and max_latitude is not None and max_longitude is not None:
        params["minlatitude"] = min_latitude
        params["minlongitude"] = min_longitude
        params["maxlatitude"] = max_latitude
        params["maxlongitude"] = max_longitude
    # Otherwise, use radius-based search
    elif latitude is not None and longitude is not None:
        params["latitude"] = latitude
        params["longitude"] = longitude
        params["maxradiuskm"] = radius_km
    else:
        return {"error": "Either provide latitude and longitude with radius, or a bounding box (min/max latitude and longitude)."}
    print(json.dumps(params, indent=4))
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent= 4))
        if data["features"]:
            return {"alert": "Earthquake detected", "earthquakes": data["features"]}
        else:
            return {"alert": "No earthquake alerts in the given area."}
    else:
        return {"error": "Failed to fetch data from USGS API."}


#Function to find the location of a point
def get_location_coordinates(location_name : str):
    """determine the coordinates of a point from the name"
    Args:
        location_name : Can be any place on earth.
    Retruns : 
        A dictionary containing longitude and latitude of the location
    """
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {
        "q": location_name,
        "apiKey": HERE_API_KEY
    }
    response = requests.get(url, params=params) 
    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            location = data["items"][0]["position"]
            x = {
                "latitude": location["lat"],
                "longitude": location["lng"]
            }
            return x
        else:
            return {"error": "Location not found."}
    else:
        return {"error": f"Failed to fetch data. HTTP Status code: {response.status_code}"}

system_instruction = """
You are Bhoomi, a chatbot designed to provide earthquake-related information. You have access to the following functions:

1. **`get_location_coordinates`**: This function converts a city name into its corresponding latitude and longitude.
2. **`check_earthquake_alert`**: This function retrieves earthquake details based on provided parameters.

### How to Process User Queries:

- **Location Queries**:
  - If a user mentions a city, invoke `get_location_coordinates` to get its latitude and longitude.
  - If a user mentions a country, use the bounding box parameters (min_latitude, max_latitude, min_longitude, max_longitude) from the `bounding_boxes.csv` file and call `check_earthquake_alert` with those parameters.

- **Date Ranges**:
  - If the user specifies exact start and end dates, use those dates in `check_earthquake_alert`.
  - If the user says something like "earthquakes update in next 10 days" or "earthquake in next 20 days":
    - Use `get_current_date` function to find the current date.
    - Calculate the `end_date` based on the number of days mentioned, and then call `check_earthquake_alert`.
  - If the user doesn't specify anything about the time, then don't give anything as start_date and end_date arguments.

- **Famous Earthquake Information**: 
  - If the user asks about notable earthquakes, use the Gemini API to provide information without invoking the functions.

- **Helpline Information**:
  - For helpline numbers, refer to the `helpline.txt` file. Provide this information directly without calling any functions.

- **Safety Advice**:
  - Use the Gemini API to offer general safety tips for earthquakes when relevant.

### Important Notes:
- Ensure all dates are formatted as YYYY-MM-DD.
- Handle user inputs gracefully and clarify if any information is missing.
- Use the model’s capabilities to interpret natural language inputs effectively.
"""

# system_instruction = """
# You are Bhoomi, a chatbot that provides earthquake-realted information. you have access to functions 'get_location_coordinates` and 'check_earthquake_alert`. If the user gives any location, get_location_coordinate function can convert that location to latitude and longitude. `check_earthquake_alert` function takes latitude and longitude as arguments if the location is a city or state, but in case of country it takes the bounding box as argument which you can find in the file `bounding_boxes.csv`.

# If the user gives any city name then you can invoke the `get_location_coordinates` function to find the latitude and longitude information for that region. 
# If the user gives any country name as input. Then you have to use the bounding box to get information from the function. You can find the bounding box for that country from the file `bounding_boxes.csv`, you don't need to call any function for this. Then you can call the function `check_earthquake_alert` function using the parameters for bounding box which are min_latitude, max_latitude, min_longitude and max_longitude.
# `check_alert_function` also takes date range as argument. If the user provide exact start_date and end_date then use those details to invoke the `check_earthquake_alert` function. else if user gives statement like `earthquakes update in next 10 days` or `earthquake in next 20 days` then you have to find the current date using gemini api, which will become your start_date. end_date then needs to be calculated based on the number of days given. Afte these information you can invoke `check_earthquake_alert` function. 

# If user asks for some earthquake information which are famous, you can check gemini api to answer such queries, there is no need to always invoke the functions.
# Additionally, for helpline numbers, refer to the file 'helpline.txt' which contains earthquake-related helpline information. You should retrieve information from this file when asked for helpline numbers. You don not need to  call any function to retrieve this information. You can also provide generic advices on how to be safe during an earthquake using gemini api. 
# """

fns = [get_location_coordinates, check_earthquake_alert, get_current_date]
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash", tools=fns, system_instruction=system_instruction)
chat = model.start_chat(enable_automatic_function_calling=True)
helpline = genai.upload_file(media / "helpline.txt")
st.title("Chatbot with History")

if "messages" not in st.session_state:
    st.session_state.messages = []

user_input = st.text_input("You:")
if user_input:
    response = chat.send_message(user_input)
    st.session_state.messages.append(f"You: {user_input}")
    st.session_state.messages.append(f"Chatbot: {response.text}")

for message in st.session_state.messages:
    st.write(message)

# calls = []
# function_handlers = {
#     "set_light" : set_light,
#     "get_location_coordinates" : get_location_coordinates
# }
# for part in response.parts:
#     fn = part.function_call
#     if fn:
#         calls.append(fn)
# for f in calls:
#     args = {key : value for key, value in f.args.items()}
#     print(args)
#     function_resposne = function_handlers[f.name](**args)
#     print(function_resposne)