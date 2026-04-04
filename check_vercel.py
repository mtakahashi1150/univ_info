#!/usr/bin/env python3
import os
import json
import requests

# Vercel REST API を使用する
vercel_token = os.getenv('VERCEL_TOKEN')
if not vercel_token:
    print("❌ Error: VERCEL_TOKEN env var not set")
    print("   Set it at: https://vercel.com/account/tokens")
    exit(1)

repo_url = "https://github.com/mtakahashi1150/univ_info"
project_name = "univ-info"

headers = {
    'Authorization': f'Bearer {vercel_token}',
    'Accept': 'application/json'
}

# Get existing projects
response = requests.get('https://api.vercel.com/v9/projects', headers=headers)
if response.status_code == 200:
    projects = response.json().get('projects', [])
    existing = [p for p in projects if p.get('name') == project_name]
    if existing:
        project_id = existing[0]['id']
        print(f"✅ Project '{project_name}' already exists (ID: {project_id})")
        print(f"   URL: https://vercel.com/masamichitakahashi-8682s-projects/{project_name}")
    else:
        print("⚠️ Project not found. Create via Vercel dashboard:")
        print(f"   https://vercel.com/masamichitakahashi-8682s-projects")
        exit(0)
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
    exit(1)
