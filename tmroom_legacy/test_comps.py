import requests
import json
def get_token():

    email = 'varga.samu@ujpestfc.hu'
    password = 'Ujpest1885!'

    auth_url = 'https://apiprod.transferroom.com/api/external/login?email='+email+'&password='+password

    r = requests.post(auth_url)
    json_data = r.json()
    token = json_data['token']
    return token


token = get_token()
headers = {"Authorization": "Bearer "+token}

request_url = 'https://apiprod.transferroom.com/api/external/competitions'
r = requests.get(request_url,headers=headers)
json_data = r.json()

json_save_path = 'competitions.json'
with open(json_save_path, 'w') as f:
    json.dump(json_data, f, indent=4)