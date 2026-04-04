#!/usr/bin/env python3
"""
GitHub REST API でリポジトリを作成するスクリプト

使用方法:
  python create_repo.py --token YOUR_TOKEN --name univ_info --user mtakahashi1150
"""

import requests
import argparse
import sys

def create_github_repo(token, repo_name, username):
    """
    GitHub API でリポジトリを作成
    
    Args:
        token: GitHub Personal Access Token
        repo_name: リポジトリ名
        username: GitHub ユーザー名
    """
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    data = {
        'name': repo_name,
        'description': 'University Opencampus Information Aggregator',
        'public': True,
        'auto_init': False
    }
    
    url = 'https://api.github.com/user/repos'
    
    print(f"Creating repository: {repo_name}")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        repo = response.json()
        print(f"✓ Repository created successfully!")
        print(f"  URL: {repo['html_url']}")
        print(f"  Clone URL: {repo['clone_url']}")
        return repo
    else:
        print(f"✗ Failed to create repository")
        print(f"  Status: {response.status_code}")
        print(f"  Error: {response.text}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create GitHub repository')
    parser.add_argument('--token', required=True, help='GitHub Personal Access Token')
    parser.add_argument('--name', required=True, help='Repository name')
    parser.add_argument('--user', help='GitHub username (for display)')
    
    args = parser.parse_args()
    
    repo = create_github_repo(args.token, args.name, args.user)
    sys.exit(0 if repo else 1)
