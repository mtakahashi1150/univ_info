#!/usr/bin/env python3
"""
各大学の正しいオープンキャンパス URL を検索・検証
sources.yaml を更新するための候補 URL を見つける
"""
import json
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def init_driver():
    """Selenium WebDriver を初期化"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# 需要確認的大学と検索キーワード
universities_to_check = {
    "早稲田大学": "早稲田大学 オープンキャンパス",
    "慶應義塾大学": "慶應義塾大学 オープンキャンパス",
    "上智大学": "上智大学 オープンキャンパス",
    "青山学院大学": "青山学院大学 オープンキャンパス",
    "法政大学": "法政大学 オープンキャンパス",
    "学習院大学": "学習院大学 オープンキャンパス",
    "芝浦工業大学": "芝浦工業大学 オープンキャンパス",
    "東京電機大学": "東京電機大学 オープンキャンパス",
    "東京工科大学": "東京工科大学 オープンキャンパス",
}

def search_and_verify(uni_name, search_query):
    """Google 検索でオープンキャンパス URL を探す"""
    print(f"\n🔍 検索中: {uni_name}")
    print(f"   キーワード: {search_query}")
    
    driver = None
    try:
        driver = init_driver()
        
        # Google 検索（site: 指定）
        university_domain = uni_name.replace("大学", "").replace("学院", "")
        search_url = f"https://www.google.co.jp/search?q={search_query}+site:.ac.jp&hl=ja"
        print(f"   検索URL: {search_url}")
        
        driver.get(search_url)
        time.sleep(3)
        
        # 최初の検索結果を取得
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='http']")
            print(f"\n   検索結果（最初の5個）:")
            
            results = []
            for link in links[:5]:
                href = link.get_attribute('href')
                if href and 'http' in href and '.ac.jp' in href:
                    # Google リダイレクトをスキップ
                    if 'google.com/url' in href:
                        # URL をデコード
                        import urllib.parse
                        parsed = urllib.parse.urlparse(href)
                        if 'q=' in parsed.query:
                            real_url = urllib.parse.parse_qs(parsed.query)['q'][0]
                            href = real_url
                    
                    text = link.text
                    print(f"      - {text[:50]}")
                    print(f"        {href[:80]}")
                    results.append(href)
            
            if results:
                print(f"\n   📌 候補URL（最初）: {results[0]}")
                return results[0]
            
        except Exception as e:
            print(f"   ⚠️  検索結果の解析に失敗: {e}")
        
    except Exception as e:
        print(f"   ❌ エラー: {e}")
    finally:
        if driver:
            driver.quit()
    
    return None

def main():
    print("\n" + "="*70)
    print("🚀 各大学のオープンキャンパスURLを検索")
    print("="*70)
    
    results = {}
    for uni_name, search_query in universities_to_check.items():
        url = search_and_verify(uni_name, search_query)
        if url:
            results[uni_name] = url
        time.sleep(2)  # サーバー負荷を軽減
    
    print("\n" + "="*70)
    print("📋 検索結果サマリー")
    print("="*70)
    
    for uni_name, url in results.items():
        print(f"{uni_name}:")
        print(f"  {url}")
        print()

if __name__ == "__main__":
    main()
