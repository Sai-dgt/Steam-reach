import requests
appid = 1291860
url="https://store.steampowered.com/api/appdetails"

params = {
    'appids': appid,
    'cc': 'us',
    'l': 'en'

}

response = requests.get(url, params=params,timeout=30)

print("HTTP status:", response.status_code)
response.raise_for_status()  # Raise an exception for HTTP errors

data = response.json()
game_result = data[str(appid)]

print:("Success :",game_result['success'])


if game_result['success']:
    game=game_result['data']

    print("Name", game.get('name'))
    print("Type", game.get('type'))
    print("Release Date", game.get('release_date'))
    print("Free",game.get('is_free'))
    print ("Price", game.get('price_overview'))