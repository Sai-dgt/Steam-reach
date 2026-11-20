import csv
import json
from pathlib import Path
import requests
from datetime import datetime,timezone,timedelta
import time
from collections import Counter
import argparse


TARGET_ELIGIBLE = 500
parser = argparse.ArgumentParser(description="collects steam game details and first year review counts in sample order before check eligibility ")
parser.add_argument("--target", type=int, default=TARGET_ELIGIBLE,help="number of eligible games to reach before stopping")
args= parser.parse_args()
DETAILS_PAUSE = 1.5
REVIEW_PAUSE = 1.5
MAX_CONSECUTIVE_FAILURES = 5
Window_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
Window_end = datetime(2025, 10, 31, tzinfo=timezone.utc)
APPDETAILS_URL="https://store.steampowered.com/api/appdetails"
user_id={
"user-agent":"steam-reach/1.0(+https://github.com/Sai-dgt/Steam-reach)"

}
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

def get_json(url, params, max_attempts=5,call=None,appid=None):
    """Get a steam URL and return its JSON, retrying on rate limits and network errors"""

    wait = 30

    for attempt in range(1, max_attempts + 1):
      status = None  
      error=""  
        
      try:
            start=time.monotonic()
            response = requests.get(url, params=params, timeout=30, headers=user_id)
            status=response.status_code
            
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError (f"HTTP {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if data:
                return data
            error = "empty response"
            print(f"   empty response (attempt {attempt})")
      except (requests.RequestException, ValueError) as e:
            error= type(e).__name__
            print(f" request failed (attempt {attempt}): {e}")
      finally:
            log_call(appid, call, attempt, status, time.monotonic() - start, error)
      if attempt < max_attempts:
            print(f"   waiting {wait}s before retrying...")
            time.sleep(wait)
            wait *=2         #30s,60s,120s,240s

    raise RuntimeError(f"Gave up after {max_attempts} attempts")
    
def extract_review_count(data):
     if not isinstance(data,dict):
        return None
     response=data.get("response")
     if not isinstance(response,dict):
         return None
     count = response.get("total_matching")

     if isinstance(count,int) and not isinstance (count,bool) and count>=0:
              return count
     return None   

def get_review_count(appid,start,end, variant,purchase_type):
    url = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
    query = {
        'appid': appid,
        'filter': 1,
        'review_type': 0,
        'purchase_type': purchase_type,
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
    #check the previously saved file
    if output_file.exists():
        
        with open(output_file, "r", encoding="utf-8") as f:
            data=json.load(f)
        count=extract_review_count(data)
        if count is not None:
            print("using saved review response", output_file)
            
            return count

        print ("invalid saved count.Fetching again:", output_file)
    #Download a new response
    data=get_json(url,params, appid=appid, call=variant)
    time.sleep(REVIEW_PAUSE)

    #Validate the new response
    count = extract_review_count(data)
    if count is None :
        
        if not isinstance(data,dict):
           keys=type(data).__name__
        elif not isinstance(data.get("response"),dict):
            keys=type(data.get("response")).__name__
        else:

            keys= list(data.get("response").keys()) 
        raise RuntimeError(
                f"Missing review count for {appid}, variant {variant}. Response: {keys}"
            )

    #Save the valid answer
    temp_file = reviews_dir / f"{appid}_{variant}.json.tmp"
    with open (temp_file,"w", encoding="utf-8") as f:
               json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(output_file)
    return count
 

def collect_reviews(appid, release):
    
    first_year_end  = int((release + timedelta(days=365)).timestamp())
    before_year_end = int((release - timedelta(days=2)).timestamp())

    return{
        "before_release":get_review_count (appid, 1, before_year_end, "before_release",0),
        "first_year":get_review_count (appid,int(release.timestamp()),first_year_end,"first_year_all",1),
        "lifetime":get_review_count ( appid, None,None, "lifetime_all",1),
    }
     

project_root = Path(__file__).resolve().parent.parent
sample_file = project_root / 'data' / 'sample_order.csv'
details_dir = project_root / 'data' / 'raw' / 'details'
LOG_FILE = project_root / "data" / "collection_log.csv"
details_dir.mkdir(parents=True, exist_ok=True)

def log_call(appid, call, attempt, status, duration, error):
  
      LOG_FIELDS = ["time_utc","appid", "call", "attempt","status", "duration" , "error"] 
      is_new = not LOG_FILE.exists()
      with open (LOG_FILE,"a", newline="", encoding= 'utf8') as f:
              writer=csv.writer(f)
              if is_new:
                        writer.writerow(LOG_FIELDS)
              writer.writerow([
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    appid,
                    call,
                    attempt,
                    status,
                    round(duration, 2),
                    error
                ])
                  



#Write results to csv
results_file = project_root / "data" / "results.csv" 
FIELDS = ["position", "appid", "status", "release_date",
          "before_release", "first_year", "lifetime"]
          
# appids already written in a previous run
done = set()
eligible_count = 0
if results_file.exists():
  with open (results_file, newline='' , encoding= 'utf8') as rf:
      for r in csv.DictReader(rf):
         done.add(r["appid"])
         if r["status"] == "eligible":
             eligible_count += 1
is_new = not results_file.exists()
#read the first App id from our randomized list
with open(sample_file, 'r', newline='', encoding='utf-8') as f, \
     open(results_file, 'a', newline='', encoding='utf-8') as out:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    if is_new:
        writer.writeheader()
    skipped=0
    processed=0
    failed=0
    failed_attempt=0

    for position, row in enumerate(reader, start=1):
        if eligible_count >=args.target:
            break
        
        appid = row['appid']

        if appid in done:
            skipped += 1
            continue
#prepare the file path for the game details
        
        try:
            output_file = details_dir / f"{appid}.json"

#Reuse existing data or download new data if the file doesn't exist

            if output_file.exists():
                print("using saved data:", output_file)
                with open(output_file, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
            else:

                print("downloading data for appid:",appid)
                data=get_json(
                    APPDETAILS_URL,
                    {'appids':appid,
                      'cc':'US', 
                      'l':'english'
                      },
                      appid=appid ,
                      call="details"
                )
            
                temp_file = details_dir / f"{appid}.json.tmp"
                with open(temp_file, 'w', encoding='utf-8') as jf:
                    json.dump(data, jf, indent=2, ensure_ascii=False)
                temp_file.replace(output_file)
                time.sleep(DETAILS_PAUSE)  # Sleep to avoid hitting the rate limit
                print(f"Saved to {output_file}")

            #Display the results
            game=data.get(str(appid), {})

            status = eligibility(game)
            

            result = {"position": position, "appid": appid, "status": status}
            
            if status == "eligible":
                release = parse_date(game["data"]["release_date"]["date"])
                counts = collect_reviews(appid, release)
                result["release_date"] = release.date().isoformat()
                result.update(counts)
                if counts["before_release"]>0:
                    result["status"] = "7_prior_early_access"
                print("  reviews:", counts)
        except RuntimeError as e:
            print(f"{position} {appid} FAILED: {e}")
            failed +=1
            
            
            failed_attempt +=1
            print(f"failed attempts:{failed_attempt}")
            if failed_attempt>=MAX_CONSECUTIVE_FAILURES:
                print (f"Stopping:{MAX_CONSECUTIVE_FAILURES} consecutive failures in a row. position:{position}, appid{appid}. Rerun to resume")
                break 
            continue
        failed_attempt=0
        
        print(position, appid, result["status"])
        writer.writerow(result)
        out.flush()    #make sure the row is saved to disk now
        processed += 1

        if result["status"] == "eligible":
            eligible_count += 1
            print(f"    eligible: {eligible_count}/{args.target}")

print (f"Done: {processed} new, {skipped} already in results.csv, {failed} failed")
with open(results_file, newline='', encoding='utf-8') as rf:
  statuses = Counter(r["status"] for r in csv.DictReader(rf))

print("Status counts in results.csv:")
for status, n in sorted(statuses.items()):
    print(f"{status}: {n}")
print(f"Eligible games so far: {statuses['eligible']}")