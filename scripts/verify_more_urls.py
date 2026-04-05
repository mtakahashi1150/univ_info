#!/usr/bin/env python3
"""
見つからない大学の追加候補を試す
"""
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import re

def init_driver(headless=True):
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

# 追加候補
additional_candidates = {
    "慶應義塾大学": [
        "https://www.keio.ac.jp/fa/admissions/",
        "https://www.keio.ac.jp/environments/admissions/",
        "https://www.keio.ac.jp/admissions/",
    ],
    "法政大学": [
        "https://www.hosei.ac.jp/admission/event/",
        "https://www.hosei.ac.jp/exam/event/oc/",
    ],
    "学習院大学": [
        "https://www.gakushuin.ac.jp/exam/",
        "https://www.gakushuin.ac.jp/about/",
    ],
    "芝浦工業大学": [
        "https://www.shibaura-it.ac.jp/exam/",
        "https://www.shibaura-it.ac.jp/en/admissions/",
    ],
    "東京電機大学": [
        "https://www.dendai.ac.jp/exam/",
        "https://www.dendai.ac.jp/admissions/oc/",
    ],
    "東京工科大学": [
        "https://www.teu.ac.jp/exam/",
        "https://www.teu.ac.jp/admissions/",
    ],
}

def check_url(url):
    driver = None
    try:
        driver = init_driver()
        driver.get(url)
        
        title = driver.title
        html = driver.page_source
        
        is_404 = any([
            "404" in title,
            "Page Not Found" in title,
            "ページが見つかりません" in title,
            "見つかりませんでした" in title,
            "Not found" in title,
            len(html) < 5000,
        ])
        
        dates = re.findall(r'\d{4}[年\-]\d{1,2}', html)
        
        return "✅" if not is_404 else "❌", title[:40], len(dates)
        
    except Exception as e:
        return "⚠️", str(e)[:20], 0
    finally:
        if driver:
            driver.quit()

print("\n進る候補テスト:\n")

for uni_name, candidates in additional_candidates.items():
    print(f"🎯 {uni_name}:")
    for url in candidates:
        status, title, dates = check_url(url)
        print(f"  {status} {url}")
        print(f"      {title[:30]} (日付: {dates}件)")
        time.sleep(1)
