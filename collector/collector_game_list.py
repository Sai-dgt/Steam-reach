import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime



#load the API key 
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)
api_key = os.getenv('STEAM_API_KEY')

if not api_key:
    raise RuntimeError("Steam API key not found ")
#Steam API endpoint 
url="https://api.steampowered.com/IStoreService/GetAppList/v1/"

last_appid = 0
page_number = 0

# Create the output directory if needed   
output_dir = Path(__file__).resolve().parent.parent / 'data' /"raw"
output_dir.mkdir(parents=True, exist_ok=True)
download_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
total_games = 0
while True :
    params = {
        'key': api_key,
        'max_results':50000,
        'last_appid': last_appid,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()  # Raise an exception for HTTP errors

    data = response.json()['response']
    total_games += len(data.get('apps', []))
    page_number += 1

   

    # Generate a date based filename 
    
    filename = output_dir / f"steam_game_list_{download_date}_page{page_number:03d}.json"
   
    #Save the complete API response
    with open(filename, 'w', encoding='utf-8') as file:
      json.dump(response.json(), file, indent=2, ensure_ascii=False)   
    print(
          f"Page {page_number}: HTTP status: {response.status_code}, "
          f"{len(data.get('apps', []))} games, "
          f"last_appid = {data.get('last_appid')} "
         )

    if not data.get("have_more_results"):
        print(f"No more results: {page_number} pages, {total_games} games saved.")
        break
    
    if data["last_appid"] <= last_appid:
        raise RuntimeError("pagination has stopped advancing")
    last_appid = data["last_appid"]
       