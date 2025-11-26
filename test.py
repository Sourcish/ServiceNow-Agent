# test_snow_auth.py - Run this separately to test
import requests

username = ""  # Your ServiceNow username
password = ""  # Your actual password
base_url = "" # Your ServiceNow instance API URL

response = requests.get(
    base_url,
    auth=(username, password),
    headers={"Accept": "application/json"},
    params={"sysparm_limit": 1}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
