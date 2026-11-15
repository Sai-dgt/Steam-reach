import csv
import json
from pathlib import Path
import requests
from datetime import datetime,timezone,timedelta
import time

Window_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
Window_end = datetime(2025, 12, 31, tzinfo=timezone.utc)

date_format = [

 "%b %d, %Y",
 "%d %b, %Y",
 "%B %d, %Y",
 "%d %B, %Y",
 

]

def parse_date(text):
    if not text:
        return None
    for fmt in date_format:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None  # Return None if no format matched

def eligibility(game):

    if not game.get('success'):
        return "1_unavailable"  # Exclude if the game data is not successful

    details = game.get('data')or {}

    if details.get('type') != 'game':
        return "1_not_game"  # Exclude if the type is not 'game'

    release_info = details.get('release_date')or {}

    if release_info.get('coming_soon'):
        return "2_coming_soon"  # Exclude if the game is coming soon

    release=parse_date(release_info.get('date'))

    if release is None:
        return "2_date_unparseable"  # Exclude if the release date is not available

    if not (Window_start <= release <= Window_end):
        return "3_outside_window"  # Exclude if the release date is outside the specified window
    if any (str(g.get("id"))== "70" for g in details.get("genres",[])):
        return "4_early_access" 
    if details.get("is_free"):
        return "5_free_to_play"  # Exclude if the game is free  
    if not details.get("price_overview"):
        return "6_no_price"  # Exclude if the game has no price information 
    return "eligible"

def get_review_count(appid,start,end, variant):
    url = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
    query = {
        'appid': appid,
        'filter': 1,
        'review_type': 0,
        'purchase_type': 0,
        'languages': ['all'],
        'filter_offtopic_activity': False,
        'num_per_page': 1  # We only need the count, so request 1 review
        
    }
    

    if start is not None and end is not None:
        query["date_range_start"] = start
        query["date_range_end"] = end 

    params = {
        'input_json': json.dumps(query)
    }
    #New Locate the saved review response 
    reviews_dir= Path(__file__).resolve().parent.parent / "data" / "raw" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    output_file = reviews_dir / f"{appid}_{variant}.json"

    #New reuse the variant if it already exists
    if output_file.exists():
        print("using saved review response", output_file)

        with open(output_file, "r", encoding="utf-8") as f:
            data=json.load(f)

    else:
        response= requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data=response.json()
        if not data:
            raise SystemExit("Empty review response (probably rate limited)")
        temp_file = reviews_dir / f"{appid}_{variant}.json.tmp"
        with open (temp_file,"w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(output_file)
        time.sleep(1.5)
    
    
    return data.get("response", {}).get("total_matching")



project_root = Path(__file__).resolve().parent.parent
sample_file = project_root / 'data' / 'sample_order.csv'
details_dir = project_root / 'data' / 'raw' / 'details'
details_dir.mkdir(parents=True, exist_ok=True)
#read the first App id from our randomized list
with open(sample_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for position, row in enumerate(reader, start=1):
        if position >5:
            break

        appid = row['appid']
#prepare the file path for the game details
        output_file = details_dir / f"{appid}.json"

#Reuse existing data or download new data if the file doesn't exist

        if output_file.exists():
            print("using saved data:", output_file)
            with open(output_file, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
        else:
            print("downloading data for appid:", appid)

            response = requests.get(
                "https://store.steampowered.com/api/appdetails",
                params={
                    'appids': appid,
                    'cc': 'US',
                    'l': 'english',
                },
                timeout=30
            )

            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            
            if not data:
                raise SystemExit("Empty response (probably rate limited)")
            

            temp_file = details_dir / f"{appid}.json.tmp"
            with open(temp_file, 'w', encoding='utf-8') as jf:
                json.dump(data, jf, indent=2, ensure_ascii=False)
            temp_file.replace(output_file)
            time.sleep(1.5)  # Sleep for 1,5 second to avoid hitting the rate limit
            print(f"Saved to {output_file}")

        

        #Display the results
        game=data.get(str(appid), {})

        print("Steam App ID:", appid)
        print("Available:", game.get('success', False))
        print("Eligibility:", eligibility(game))

#Test with a previously validated game
test_release=datetime(2023,3,13,tzinfo=timezone.utc)

start = int(test_release.timestamp())
end = int((test_release + timedelta(days=365)).timestamp())
count=get_review_count(1291860,start,end, "first_year")

print("Rough justice: '84 first year reviews:",count)

#New reviews before release
before_end=int(
    (test_release - timedelta(days=2)).timestamp()
)

before_count = get_review_count(
    1291860,
    1,
    before_end,
    "before_release"
)

print("Before_release reviews:", before_count)

#Pause before API requests
time.sleep(1)

#New reviews across the game's entire lifetime

lifetime_count= get_review_count(
1291860,
None,
None,
"lifetime"

)

print("lifetime reviews:",lifetime_count)