#!/usr/bin/env python3
"""
各大学ページの HTML 構造を分析するスクリプト
日付・学部・キャンパス情報がどこに記載されているかを調査
"""

import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
import json
from typing import Dict, List, Any

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)
TIMEOUT = 10

# 分析対象大学・URL
universities = {
    "早稲田大学": "https://www.waseda.jp/inst/admission/event/oc/",
    "慶應義塾大学": "https://www.keio.ac.jp/ja/admission/guide/experience/",
    "上智大学": "https://www.sophia.ac.jp/jpn/admission/",
    "東京理科大学": "https://www.tus.ac.jp/admissions/university/visittus/opencampus/",
    "明治大学": "https://www.meiji.ac.jp/exam/event/opencampus/",
    "青山学院大学": "https://www.aoyama.ac.jp/exam/event/",
    "立教大学": "https://www.rikkyo.ac.jp/admissions/visit/opencampus/index.html",
    "中央大学": "https://www.chuo-u.ac.jp/exam/event/",
    "法政大学": "https://www.hosei.ac.jp/admissions/event/",
    "学習院大学": "https://www.gakushuin.ac.jp/admission/",
    "芝浦工業大学": "https://www.shibaura-it.ac.jp/admission/",
    "東京都市大学": "https://www.tcu.ac.jp/admission/",
    "東京電機大学": "https://www.dendai.ac.jp/admission/",
    "工学院大学": "https://www.kogakuin.ac.jp/admissions/event/oc.html",
    "東京工科大学": "https://www.teu.ac.jp/admission/",
    "電気通信大学": "https://www.uec.ac.jp/education/undergraduate/event/opencampus.html",
}

def fetch_page(url: str) -> str:
    """ページを取得"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except Exception as e:
        print(f"❌ {url}: {e}")
        return None

def extract_dates(text: str) -> List[str]:
    """テキストから日付をすべて抽出"""
    patterns = [
        r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})',  # 2026年4月1日
        r'(\d{1,2})/(\d{1,2})',  # 4/1 (月/日)
        r'(\d{1,2})\.(\d{1,2})',  # 4.1（月.日）
    ]
    dates = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        dates.extend(['-'.join(m) if len(m) == 3 else f"-{m[0]}-{m[1]}" for m in matches])
    return list(set(dates))

def analyze_university(name: str, url: str):
    """大学ページを分析"""
    print(f"\n{'='*60}")
    print(f"📍 {name}")
    print(f"   URL: {url}")
    print(f"{'='*60}")
    
    html = fetch_page(url)
    if not html:
        print(f"❌ 取得失敗")
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # ページタイトル
    title = soup.find('title')
    print(f"\n📄 タイトル: {title.string if title else '不明'}")
    
    # メタ説明
    og_desc = soup.find('meta', property='og:description')
    if og_desc:
        print(f"📝 OG説明: {og_desc.get('content', '')[:100]}")
    
    # テキストから日付を抽出
    text = soup.get_text()
    dates = extract_dates(text)
    print(f"\n📅 抽出された日付 ({len(dates)}件):")
    for date in sorted(set(dates))[:5]:  # 上位5件
        print(f"   - {date}")
    
    # h1-h3の見出しから重要な情報を抽出
    print(f"\n🎯 見出し情報:")
    for tag in ['h1', 'h2', 'h3']:
        headings = soup.find_all(tag)
        for heading in headings[:3]:
            text = heading.get_text(strip=True)
            if text and len(text) < 100:
                print(f"   <{tag}> {text}")
    
    # 日付を含むテキストノードを抽出
    print(f"\n🔍 日付を含むテキスト（最初の3件）:")
    count = 0
    for elem in soup.find_all(string=re.compile(r'\d{4}[年/-]?\d{1,2}[月/-]\d{1,2}|開催|申込|日程|期間')):
        if count >= 3:
            break
        text_snippet = str(elem).strip()[:80]
        if text_snippet and len(text_snippet) > 10:
            print(f"   {text_snippet}")
            count += 1
    
    # テーブル情報を抽出
    tables = soup.find_all('table')
    print(f"\n📊 テーブル数: {len(tables)}")
    if tables:
        for i, table in enumerate(tables[:2]):
            rows = table.find_all('tr')
            print(f"   テーブル {i+1}: {len(rows)} 行")
            for row in rows[:2]:
                cells = row.find_all(['td', 'th'])
                cell_texts = [cell.get_text(strip=True)[:30] for cell in cells]
                print(f"      {' | '.join(cell_texts)}")
    
    # HTML 保存（後で詳細分析用）
    analysis_dir = Path('analysis')
    analysis_dir.mkdir(exist_ok=True)
    
    filename = f"{analysis_dir}/{name.replace('大学', '')}_raw.html"
    with open(filename, 'w', encoding='utf-8') as f:
        # 見やすくするため整形
        soup_pretty = BeautifulSoup(html, 'html.parser')
        f.write(soup_pretty.prettify()[:10000])  # 最初の10KB
    
    print(f"\n💾 HTML保存: {filename} (最初の10KB)")

def main():
    print("\n🔍 大学オープンキャンパス情報ページ分析")
    print(f"対象大学数: {len(universities)}\n")
    
    for name, url in sorted(universities.items()):
        analyze_university(name, url)
    
    print(f"\n{'='*60}")
    print("✅ 分析完了")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
