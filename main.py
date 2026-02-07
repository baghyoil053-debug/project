import requests

BASE_URL = "https://openapivts.koreainvestment.com:29443"
APPKEY = "..."
APPSECRET = "..."

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