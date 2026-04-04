#!/usr/bin/env python3
import os
import requests

token = os.getenv('univ_info_deploy')
if not token:
    print("Error: univ_info_deploy token not set")
    exit(1)

repo_owner = 'mtakahashi1150'
repo_name = 'univ_info'

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

# Check if Pages is already enabled
pages_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pages'
response = requests.get(pages_url, headers=headers)

if response.status_code == 404:
    # Pages not yet enabled, enable it
    payload = {
        'source': {
            'branch': 'main',
            'path': '/'
        }
    }
    response = requests.post(pages_url, json=payload, headers=headers)
    if response.status_code in [201, 204]:
        print("✅ GitHub Pages enabled successfully")
    else:
        print(f"Error enabling Pages: {response.status_code}")
        print(response.text)
elif response.status_code == 200:
    print("✅ GitHub Pages already enabled")
    data = response.json()
    print(f"   URL: {data.get('html_url', 'N/A')}")
    print(f"   Status: {data.get('status', 'N/A')}")
else:
    print(f"Error checking Pages: {response.status_code}")
    print(response.text)
