import os
import requests
from pathlib import Path
from dotenv import load_dotenv

#load the API key 
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)
api_key = os.getenv('STEAM_API_KEY')

if not api_key:
    raise RuntimeError("Steam API key not found ")
#Steam API endpoint 
url="https://api.steampowered.com/IStoreService/GetAppList/v1/"

#parameters sent to Steam
params = {
    'key': api_key,
    'max_results':5
}

#Make the request
try:
    response = requests.get(url, params=params, timeout=30)


except requests.RequestException:
        print("Network request failed.")

else :
     print("HTTP status:", response.status_code)

     if response.ok:
            data = response.json()
            print("Response structure:", list(data.keys()))
            print("First games:", data.get('response', {}).get('apps', [])[:5])

            