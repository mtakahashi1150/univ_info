#!/usr/bin/env python3
"""
GitHub Actions ワークフロー実行状況確認
"""

import os
import requests
import sys
import time

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
REPO = "mtakahashi1150/univ_info"

if not GITHUB_TOKEN:
    print("❌ エラー: GITHUB_TOKEN が設定されていません")
    sys.exit(1)

# 最新のワークフロー実行を取得
url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=1&sort=created&order=desc"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    runs = data.get('workflow_runs', [])
    
    if runs:
        run = runs[0]
        run_id = run.get('id')
        status = run.get('status')
        conclusion = run.get('conclusion')
        name = run.get('name')
        created_at = run.get('created_at')
        
        print(f"✅ 最新ワークフロー実行:")
        print(f"   名前: {name}")
        print(f"   Run ID: {run_id}")
        print(f"   状態: {status}")
        print(f"   結論: {conclusion}")
        print(f"   作成: {created_at}")
        print(f"   リンク: https://github.com/{REPO}/actions/runs/{run_id}")
        
        # ジョブ詳細を取得
        jobs_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs"
        jobs_response = requests.get(jobs_url, headers=headers, timeout=10)
        jobs_response.raise_for_status()
        
        jobs_data = jobs_response.json()
        jobs = jobs_data.get('jobs', [])
        
        print(f"\n📊 ジョブ詳細:")
        for job in jobs:
            job_name = job.get('name')
            job_status = job.get('status')
            job_conclusion = job.get('conclusion')
            print(f"   - {job_name}: {job_status} ({job_conclusion})")
    else:
        print("❌ ワークフロー実行が見つかりません")
        sys.exit(1)

except requests.exceptions.RequestException as e:
    print(f"❌ 通信エラー: {e}")
    sys.exit(1)
