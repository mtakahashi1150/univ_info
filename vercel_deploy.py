#!/usr/bin/env python3
"""
Vercel API を使用してプロジェクトをデプロイ
ユーザーが VERCEL_TOKEN を環境変数で提供する必要があります
"""

import os
import sys
import requests
import json

token = os.getenv('VERCEL_TOKEN')
if not token:
    print("❌ VERCEL_TOKEN が設定されていません")
    print("\n手順:")
    print("1. https://vercel.com/account/tokens にアクセス")
    print("2. 新規トークンを生成 (Full Account scope)")
    print("3. 以下を実行:")
    print('   export VERCEL_TOKEN="your_token_here"')
    print("   python vercel_deploy.py")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json'
}

# Get teams
teams_response = requests.get('https://api.vercel.com/v1/teams', headers=headers)
if teams_response.status_code != 200:
    print(f"❌ Teams API Error: {teams_response.status_code}")
    print(teams_response.text)
    sys.exit(1)

teams = teams_response.json().get('teams', [])
team_id = teams[0]['id'] if teams else None

print(f"✅ Vercel アカウント接続成功")
print(f"   Team: {teams[0].get('name', 'Personal')} (ID: {team_id})")

# Create or get project
project_name = "univ-info"
projects_url = f"https://api.vercel.com/v9/projects?teamId={team_id}" if team_id else "https://api.vercel.com/v9/projects"

projects_response = requests.get(projects_url, headers=headers)
projects = projects_response.json().get('projects', [])
project = next((p for p in projects if p['name'] == project_name), None)

if project:
    print(f"✅ プロジェクト '{project_name}' が見つかりました")
    print(f"   URL: {project.get('targets', {}).get('production', {}).get('url', 'N/A')}")
else:
    print(f"⚠️  プロジェクト '{project_name}' が見つかりません")
    print("   以下の手順で Vercel ダッシュボードから作成してください:")
    print(f"   https://vercel.com/new?template=other")
    print("")
    print("または GitHub から直接インポート:")
    print("   https://vercel.com/masamichitakahashi-8682s-projects")

print("\n💡 または CLI でデプロイ:")
print("   vercel deploy --prod")
