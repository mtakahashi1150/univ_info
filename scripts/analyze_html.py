#!/usr/bin/env python3
"""
失敗した9大学の HTML 構造を分析
日付情報がどこに格納されているかを調査
"""
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 分析対象の大学（失敗した9校）
failing_universities = {
    "早稲田大学": "https://www.waseda.jp/inst/admission/event/oc/",
    "慶應義塾大学": "https://www.keio.ac.jp/ja/admission/guide/experience/",
    "上智大学": "https://www.sophia.ac.jp/jpn/admission/",
    "青山学院大学": "https://www.aoyama.ac.jp/exam/event/",
    "法政大学": "https://www.hosei.ac.jp/admissions/event/",
    "学習院大学": "https://www.gakushuin.ac.jp/admission/",
    "芝浦工業大学": "https://www.shibaura-it.ac.jp/admission/",
    "東京電機大学": "https://www.dendai.ac.jp/admission/",
    "東京工科大学": "https://www.teu.ac.jp/admission/",
}

def init_driver():
    """Selenium WebDriver を初期化"""
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def extract_dates_with_regex(text):
    """テキストから日付を抽出（複数パターン対応）"""
    patterns = [
        r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',  # 2026年4月5日 / 2026-04-05
        r'(\d{1,2})[月\-/](\d{1,2})日?',  # 4月5日 / 4-5
    ]
    
    dates = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match) == 3:
                    year, month, day = match
                    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(match) == 2:
                    month, day = match
                    date_str = f"2026-{month.zfill(2)}-{day.zfill(2)}"
                dates.append(date_str)
            except:
                pass
    
    return dates

def analyze_university(uni_name, url):
    """大学ページの HTML 構造を分析"""
    print(f"\n{'='*60}")
    print(f"🔍 分析中: {uni_name}")
    print(f"{'='*60}")
    print(f"URL: {url}")
    
    driver = None
    try:
        driver = init_driver()
        driver.get(url)
        
        # JavaScript 実行待機
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
        )
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # ページタイトルを確認
        title = soup.find('title')
        print(f"\n📄 ページタイトル: {title.text if title else 'N/A'}")
        
        # メインコンテンツの構造を調査
        print("\n📋 HTML 構造分析:")
        
        # h1, h2 タグを探す
        headings = soup.find_all(['h1', 'h2', 'h3'])
        if headings:
            print(f"   見出し（最初の10個）:")
            for h in headings[:10]:
                text = h.get_text(strip=True)[:50]
                print(f"     - {h.name}: {text}")
        
        # テーブルを探す
        tables = soup.find_all('table')
        print(f"   テーブル数: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables[:2]):
                print(f"\n   テーブル {i+1}:")
                rows = table.find_all('tr')[:3]
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    print(f"      {' | '.join([c.get_text(strip=True)[:20] for c in cells])}")
        
        # リスト要素を探す
        ul_lists = soup.find_all('ul')
        ol_lists = soup.find_all('ol')
        print(f"   ul リスト数: {len(ul_lists)}, ol リスト数: {len(ol_lists)}")
        
        # 日付パターンを含むテキストを探す
        all_text = soup.get_text()
        dates_found = extract_dates_with_regex(all_text)
        
        print(f"\n📅 抽出された日付候補:")
        if dates_found:
            unique_dates = list(set(dates_found))[:5]
            for date in unique_dates:
                print(f"   - {date}")
        else:
            print("   ⚠️  日付が見つかりませんでした")
        
        # 特定の要素を探す（イベント情報）
        event_keywords = ['開催', 'イベント', '予定', '申込', '応募', '日程', '日付', '開始']
        print(f"\n🎯 イベント情報を含む要素:")
        
        for elem in soup.find_all(['div', 'section', 'li']):
            text = elem.get_text(strip=True)
            if any(keyword in text for keyword in event_keywords) and len(text) < 200:
                if any(re.search(r'\d{4}[年\-]\d{1,2}', text) for _ in [0]):
                    print(f"   - {text[:100]}")
        
        # JSON-LD スキーマを探す
        json_lds = soup.find_all('script', {'type': 'application/ld+json'})
        if json_lds:
            print(f"\n📊 JSON-LD スキーマ数: {len(json_lds)}")
            for i, ld in enumerate(json_lds[:1]):
                try:
                    data = json.loads(ld.string)
                    print(f"   タイプ: {data.get('@type', 'Unknown')}")
                    if 'events' in str(data)[:100]:
                        print(f"   ✓ events フィールド検出")
                except:
                    pass
        
        print(f"\n✅ 分析完了")
        
    except Exception as e:
        logger.error(f"❌ エラー: {e}")
    finally:
        if driver:
            driver.quit()

def main():
    """メイン実行"""
    print("\n" + "="*60)
    print("🚀 HTML 構造分析スクリプト")
    print("="*60)
    
    for uni_name, url in failing_universities.items():
        analyze_university(uni_name, url)
    
    print("\n" + "="*60)
    print("✅ 分析完了")
    print("="*60)

if __name__ == "__main__":
    main()
