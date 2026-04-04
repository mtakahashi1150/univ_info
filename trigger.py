#!/usr/bin/env python3
"""
GitHub Actions ワークフロー手動トリガー
fetch-and-notify.yml を手動で実行
"""

import os
import requests
import sys

# GitHub 認証情報
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
REPO = "mtakahashi1150/univ_info"
WORKFLOW_ID = "fetch-and-notify.yml"

if not GITHUB_TOKEN:
    print("❌ エラー: GITHUB_TOKEN または GH_TOKEN が設定されていません")
    print("export GITHUB_TOKEN='your_token' で設定してください")
    sys.exit(1)

url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
payload = {"ref": "main"}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    
    if response.status_code == 204:
        print("✅ ワークフロー手動トリガー実行！")
        print(f"📍 進行状況: https://github.com/{REPO}/actions")
        print(f"⏳ 1-2 分後に GitHub Pages を確認:")
        print(f"   https://mtakahashi1150.github.io/univ_info/")
    else:
        print(f"❌ エラー: HTTP {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)

except requests.exceptions.RequestException as e:
    print(f"❌ 通信エラー: {e}")
    sys.exit(1)
