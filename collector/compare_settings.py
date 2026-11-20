import csv
from pathlib import Path
from datetime import datetime, timezone,timedelta
import json
import time
import requests

REVIEWS_URL="https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"

HEADERS={
"user-agent":"steam-reach/1.0(+https://github.com/Sai-dgt/Steam-reach)"}


project_root= Path(__file__).resolve().parent.parent
results_file= project_root/"data"/"results.csv"
with open (results_file,"r", newline="", encoding="utf8") as f:
    reader=csv.DictReader(f)
    rows =list(reader)
    print("Rows read:", len(rows))
    
eligible_games = [
    row for  row in rows
        if row["status"]=="eligible"
         
             ]




def fetch_count(appid, start, end, purchase_type,offtopic=False):
    
    query={
         "appid":int(appid),
         "filter":1,
         "review_type":0,
         "purchase_type":purchase_type,
         "languages":["all"],
         "filter_offtopic_activity": offtopic,
         "num_per_page":1,
         "date_range_start":start,
         "date_range_end":end
}

    response = requests.get(
    REVIEWS_URL,
    params={"input_json": json.dumps(query)},
    headers=HEADERS,
    timeout=30
)
    response.raise_for_status()
    return response.json()["response"]["total_matching"
                                       ]
comparison_file=project_root/ "data" /"settings_comparison.csv"
done=set()
if comparison_file.exists():
    with open(comparison_file,"r",newline="",encoding="utf8") as f:
        for r in csv.DictReader(f):
            done.add(r["appid"])
is_new=not comparison_file.exists()

with open(comparison_file,"a",newline="",encoding="utf8") as f:
    writer=csv.writer(f)
    if is_new:
        writer.writerow(["appid","first_year","all_purchases","offtopic_excluded"])
    print("Already done:", len(done))
            
    for game in eligible_games:
        
        if game["appid"]  in done:
            continue
    
        release_text=game["release_date"]
        release=datetime.fromisoformat(release_text).replace(tzinfo=timezone.utc)
        start=int(release.timestamp())
        end=int((release+timedelta(days=365)).timestamp())
        all_purchase=fetch_count(game["appid"],start,end,1, False)
        time.sleep(1.5)
        off_topic=fetch_count(game["appid"],start,end,0,True)

        writer.writerow([game["appid"],game["first_year"],all_purchase,off_topic])
        f.flush()
        print(game["appid"],"first year:",game["first_year"],"start:",start, "end:",end,"All purchases:",all_purchase,"Off topic excluded:",off_topic)
        time.sleep(1.5)


