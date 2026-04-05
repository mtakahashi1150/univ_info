#!/usr/bin/env python3
"""
各大学の代替URL候補を検証
404 が返される場合は、複数の候補URL を試す
"""
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def init_driver(headless=True):
    """Selenium WebDriver を初期化"""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# 各大学の URL 候補
university_candidates = {
    "早稲田大学": [
        "https://www.waseda.jp/inst/admission/event/oc/",
        "https://www.waseda.jp/admission/",
        "https://www.waseda.jp/inst/admission/",
        "https://www.waseda.jp/admission/event/",
    ],
    "慶應義塾大学": [
        "https://www.keio.ac.jp/ja/admission/guide/experience/",
        "https://www.keio.ac.jp/ja/admission/",
        "https://www.keio.ac.jp/admissions/",
    ],
    "上智大学": [
        "https://www.sophia.ac.jp/jpn/admission/",
        "https://www.sophia.ac.jp/admissions/",
        "https://www.sophia.ac.jp/jpn/admissions/",
    ],
    "青山学院大学": [
        "https://www.aoyama.ac.jp/exam/event/",
        "https://www.aoyama.ac.jp/admissions/",
        "https://www.aoyama.ac.jp/admission/",
    ],
    "法政大学": [
        "https://www.hosei.ac.jp/admissions/event/",
        "https://www.hosei.ac.jp/admissions/",
        "https://www.hosei.ac.jp/exam/",
    ],
    "学習院大学": [
        "https://www.gakushuin.ac.jp/admission/",
        "https://www.gakushuin.ac.jp/admissions/",
        "https://www.gakushuin.ac.jp/exam/",
    ],
    "芝浦工業大学": [
        "https://www.shibaura-it.ac.jp/admission/",
        "https://www.shibaura-it.ac.jp/admissions/",
        "https://www.shibaura-it.ac.jp/exam/",
    ],
    "東京電機大学": [
        "https://www.dendai.ac.jp/admission/",
        "https://www.dendai.ac.jp/admissions/",
        "https://www.dendai.ac.jp/exam/",
    ],
    "東京工科大学": [
        "https://www.teu.ac.jp/admission/",
        "https://www.teu.ac.jp/admissions/",
        "https://www.teu.ac.jp/exam/",
    ],
}

def check_url(url, timeout=10):
    """URL をチェックして HTTP ステータスと日付を確認"""
    driver = None
    try:
        driver = init_driver()
        driver.get(url)
        
        # タイトルから 404 かどうか判定
        title = driver.title
        html = driver.page_source
        
        # 404 インジケーター
        is_404 = any([
            "404" in title,
            "Page Not Found" in title,
            "ページが見つかりません" in title,
            "見つかりませんでした" in title,
            "Not found" in title,
            len(html) < 5000,  # 404ページは通常小さい
        ])
        
        # 日付検出
        import re
        dates = re.findall(r'\d{4}[年\-]\d{1,2}', html)
        
        status = "❌ 404" if is_404 else "✅ VALID"
        date_info = f"(日付: {len(dates)}件)" if dates else "(日付: なし)"
        
        return status, title[:50], date_info
        
    except Exception as e:
        return f"⚠️  ERROR", str(e)[:30], ""
    finally:
        if driver:
            driver.quit()

def main():
    print("\n" + "="*80)
    print("🔍 各大学のURL候補を検証")
    print("="*80)
    
    valid_urls = {}
    
    for uni_name, candidates in university_candidates.items():
        print(f"\n🎯 {uni_name}:")
        
        for url in candidates:
            status, title, date_info = check_url(url)
            print(f"  {status} {url}")
            print(f"      タイトル: {title}")
            print(f"      {date_info}")
            
            if "✅" in status:
                valid_urls[uni_name] = url
                print(f"      ✨ これは利用可能です！")
                break
            
            time.sleep(1)  # レート制限
    
    print("\n" + "="*80)
    print("📋 利用可能な URL")
    print("="*80)
    
    for uni_name, url in valid_urls.items():
        print(f"\n{uni_name}:")
        print(f"  {url}")
    
    # sources.yaml の更新用コード
    print("\n" + "="*80)
    print("📝 sources.yaml 更新用:")
    print("="*80)
    
    for uni_name, url in valid_urls.items():
        print(f'\n  - name: "{uni_name}"')
        print(f'    url: "{url}"')

if __name__ == "__main__":
    main()
