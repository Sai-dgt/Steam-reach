import json
from pathlib import Path
import random
import csv
#Sample order generated from the game list downloaded 2026-11-10  19:46:32 (199,623 apps), seed 42. The order is randomized with a fixed seed for reproducibility.
#Locate the project raw data directory
project_root = Path(__file__).resolve().parent.parent
raw_dir = project_root / 'data' / 'raw'

#Find the four downloaded json files
files = sorted(raw_dir.glob("steam_game_list_2026-11-10_19-46-32_page*.json"))
if not files:
    raise SystemExit(f"No game list files found in {raw_dir}.")
app_ids = []

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        apps = data.get('response', {}).get('apps', [])
        app_ids.extend(app['appid'] for app in apps)


#Check the results 
print("Files processed:", len(files))
print("Total app IDs collected:", len(app_ids))
print("unique app IDs:", len(set(app_ids)))
print("Duplicates found:", len(app_ids) - len(set(app_ids)))

#Shuffle the app IDs using a random seed
app_ids = sorted(set(app_ids))  # Remove duplicates and sort
random.Random(42).shuffle(app_ids)
#Save the randomized order to a CSV file
output_file = project_root / 'data' / 'sample_order.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['position', 'appid'])
    for position, app_id in enumerate(app_ids, start=1):
        writer.writerow([position, app_id])

print(f"saved {len(app_ids)} randomized app IDs to {output_file}")