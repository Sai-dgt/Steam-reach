import json
from datetime import datetime,timedelta, timezone
import requests

#-----Changinng this per game----
appid = 2206240
release_date = datetime(2024, 4, 30, tzinfo=timezone.utc)
#--------------------------------

url = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"

release_ts = int(release_date.timestamp())
first_year_end = int((release_date + timedelta(days=365)).timestamp())


def fetch_page(extra=None):
    ### request one page of reviews. 'extra' adds keys such as cursor or date range.###
    query = {
      'appid': appid,
      'filter': 1,
      'review_type':0,
      'purchase_type': 0,
      'languages': ['english'],
      'filter_offtopic_activity': False,
      'num_per_page': 100,
}
    if extra :
      query.update(extra)
    response = requests.get(url, params={'input_json': json.dumps(query)}, timeout=30)
    response.raise_for_status()
    try:
      return response.json().get('response',{})
    except requests.exceptions.JSONDecodeError:
      raise SystemExit("Steam did not return valid JSON: " + repr(response.text[:120]))  # Print the first 120 characters of the response
 
def fetch_all_reviews(extra=None):
    result = fetch_page(extra)  
    reviews = result.get("reviews", [])
    total = result.get("total_matching", 0)
     
    while len(reviews) < total:
        result = fetch_page({**(extra or {}), 'cursor': result.get("cursor")})
        new_reviews = result.get("reviews", [])
        if not new_reviews:
            raise RuntimeError("Steam stopped returning reviews before reaching the total_matching.")
        reviews.extend(new_reviews)
        print(f"Fetched {len(reviews)} /{total}", end="\r")
    return reviews, total
def steam_count(date_start, date_end):
    result= fetch_page({'date_range_start': date_start, 'date_range_end': date_end, 'num_per_page': 1})
    return result.get("total_matching", 0)


def count_between(reviews, date_start, date_end):
   return sum(date_start <= r['timestamp_created'] <= date_end for r in reviews)

def check(label,mine,steam):
   status= "PASS" if mine == steam else "FAIL"
   print(f"{status} {label}:manual={mine} steam={steam} ")


reviews,lifetime_total = fetch_all_reviews()
print(f"App {appid}: downloaded {len(reviews)} reviews \n") 

check("lifetime", len(reviews), lifetime_total)
check("first year", 
         count_between(reviews, release_ts, first_year_end),
         steam_count(release_ts, first_year_end))
check("Pre-release",
         count_between(reviews, 1, release_ts),
         steam_count(1, release_ts))