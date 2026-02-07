import requests

BASE_URL = "https://openapivts.koreainvestment.com:29443"
APPKEY = "PSVtl4u1YdAUHz37pErtgrqgUvJ3xXwbSC18"
APPSECRET = "oa8TAFmINbppKjw6wmPPaVn1NNubC3eeUsCDiM7zD4T3TaqdW1fU5QQ6KbXiNqoPydKciw17Rr27uSlzz9dhVQVT/Vrp6/g0oTe5+WMxz/0kr52P3/t44kHPi4xAbeOBdvRu0AqmxLaSY12GpWpfA04g7XAxhJffH00EbMsgluq07g9BHbM"

url = f"{BASE_URL}/oauth2/tokenP"
headers = {
    "Content-Type": "application/json"
}
body = {
    "grant_type": "client_credentials",
    "appkey": APPKEY,
    "appsecret": APPSECRET
}
try:
    res = requests.post(url, headers=headers, json=body)
    data = res.json()
    print(data)
except Exception as e:
    print(e)