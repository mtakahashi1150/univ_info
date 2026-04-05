#!/usr/bin/env python3
"""
各大学のウェブサイトを人間と同じようにナビゲートして
オープンキャンパス情報ページの正しいURLを特定する。

戦略:
  トップページ → 入試/受験生 → イベント/オープンキャンパス
  リンクテキストに「入試」「受験」「イベント」「オープンキャンパス」等を含むリンクを辿る
"""
import re
import time
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 失敗している6大学 + 日付取得できていない2大学
TARGET_UNIVERSITIES = {
    "慶應義塾大学": "https://www.keio.ac.jp/ja/",
    "上智大学": "https://www.sophia.ac.jp/jpn/",
    "青山学院大学": "https://www.aoyama.ac.jp/",
    "法政大学": "https://www.hosei.ac.jp/",
    "学習院大学": "https://www.univ.gakushuin.ac.jp/",
    "芝浦工業大学": "https://www.shibaura-it.ac.jp/",
    "東京電機大学": "https://www.dendai.ac.jp/",
    "東京工科大学": "https://www.teu.ac.jp/",
}

# ナビゲーション用キーワード（優先度順）
NAV_KEYWORDS_PHASE1 = [
    'オープンキャンパス',
    'opencampus',
    'open campus',
    'open_campus',
]

NAV_KEYWORDS_PHASE2 = [
    '入試', '受験生', '入学案内', 'admissions', 'admission',
    '受験情報', '入試情報',
]

NAV_KEYWORDS_PHASE3 = [
    'イベント', 'event', 'キャンパス見学', '説明会',
    '体験', '進学', 'oc',
]

# 日付パターン
DATE_PATTERNS = [
    r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})',
    r'(?:20\d{2})[年]?\s*(\d{1,2})[月/](\d{1,2})',
]

OC_KEYWORDS = ['オープンキャンパス', 'opencampus', 'open campus', 'OC', 'oc']


def init_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_page(driver, url, wait=3):
    """ページ取得 + JS実行待ち"""
    try:
        driver.get(url)
        time.sleep(wait)
        return driver.page_source
    except Exception as e:
        print(f"      ⚠ ページ取得失敗: {e}")
        return None


def find_links_by_keywords(html, base_url, keywords):
    """HTMLからキーワードを含むリンクを抽出"""
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        link_text = a_tag.get_text(strip=True).lower()
        href_lower = href.lower()
        
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in link_text or kw_lower in href_lower:
                full_url = urljoin(base_url, href)
                # 外部サイトやPDFを除外
                if urlparse(full_url).netloc == urlparse(base_url).netloc or '.ac.jp' in urlparse(full_url).netloc:
                    if not full_url.endswith('.pdf'):
                        found.append({
                            'url': full_url,
                            'text': a_tag.get_text(strip=True)[:60],
                            'keyword': kw,
                        })
                        break
    
    # 重複除去
    seen = set()
    unique = []
    for item in found:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    
    return unique


def check_page_for_oc_dates(html):
    """ページにオープンキャンパス関連の日付があるか検査"""
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    # まず「オープンキャンパス」というキーワードがあるか
    has_oc_keyword = any(kw.lower() in text.lower() for kw in OC_KEYWORDS)
    
    # 日付を抽出
    dates = []
    for pattern in DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            try:
                if len(groups) == 3:
                    y, m, d = int(groups[0]), int(groups[1]), int(groups[2])
                elif len(groups) == 2:
                    y, m, d = 2026, int(groups[0]), int(groups[1])
                else:
                    continue
                
                if 2025 <= y <= 2027 and 1 <= m <= 12 and 1 <= d <= 31:
                    date_str = f"{y:04d}-{m:02d}-{d:02d}"
                    dates.append(date_str)
            except:
                continue
    
    # 2025年4月以降の日付のみ（古すぎるものは除外）
    future_dates = [d for d in dates if d >= "2025-04-01"]
    
    if has_oc_keyword and future_dates:
        return {
            'has_oc': True,
            'dates': sorted(set(future_dates)),
            'total_dates_found': len(future_dates),
        }
    elif future_dates:
        return {
            'has_oc': False,
            'dates': sorted(set(future_dates)),
            'total_dates_found': len(future_dates),
        }
    
    return None


def navigate_university(uni_name, top_url, driver):
    """大学サイトをナビゲートしてOCページを特定"""
    print(f"\n{'='*70}")
    print(f"🏫 {uni_name}")
    print(f"   トップ: {top_url}")
    print(f"{'='*70}")
    
    results = {
        'university': uni_name,
        'top_url': top_url,
        'found_pages': [],
        'best_url': None,
        'navigation_path': [],
    }
    
    # Phase 0: トップページを取得
    print(f"\n   📍 Phase 0: トップページ取得")
    html = get_page(driver, top_url)
    if not html:
        print(f"   ❌ トップページ取得失敗")
        return results
    
    # トップページ自体にOC情報があるか
    oc_info = check_page_for_oc_dates(html)
    if oc_info and oc_info.get('has_oc'):
        print(f"   ✅ トップページにOC情報あり: {oc_info['dates'][:3]}")
    
    # Phase 1: トップページから直接「オープンキャンパス」リンクを探す
    print(f"\n   📍 Phase 1: トップページからOCリンクを直接探す")
    oc_links = find_links_by_keywords(html, top_url, NAV_KEYWORDS_PHASE1)
    
    if oc_links:
        for link in oc_links[:3]:
            print(f"      🔗 [{link['text']}] → {link['url']}")
            
            link_html = get_page(driver, link['url'], wait=2)
            link_oc = check_page_for_oc_dates(link_html)
            
            if link_oc:
                print(f"         ✅ OC日付あり: {link_oc['dates'][:5]}")
                results['found_pages'].append({
                    'url': link['url'],
                    'path': f"トップ → {link['text']}",
                    'dates': link_oc['dates'],
                    'has_oc_keyword': link_oc.get('has_oc', False),
                })
            else:
                print(f"         ⚠ 日付なし - さらにリンクを探す")
                # このページからさらにOCリンクを探す
                if link_html:
                    sub_links = find_links_by_keywords(link_html, link['url'], NAV_KEYWORDS_PHASE1 + NAV_KEYWORDS_PHASE3)
                    for sub in sub_links[:3]:
                        if sub['url'] != link['url']:
                            print(f"            🔗 [{sub['text']}] → {sub['url']}")
                            sub_html = get_page(driver, sub['url'], wait=2)
                            sub_oc = check_page_for_oc_dates(sub_html)
                            if sub_oc:
                                print(f"               ✅ OC日付あり: {sub_oc['dates'][:5]}")
                                results['found_pages'].append({
                                    'url': sub['url'],
                                    'path': f"トップ → {link['text']} → {sub['text']}",
                                    'dates': sub_oc['dates'],
                                    'has_oc_keyword': sub_oc.get('has_oc', False),
                                })
    
    # Phase 2: 「入試情報」「受験生」系リンクを探す
    print(f"\n   📍 Phase 2: 入試情報リンクを探す")
    admission_links = find_links_by_keywords(html, top_url, NAV_KEYWORDS_PHASE2)
    
    for link in admission_links[:3]:
        print(f"      🔗 [{link['text']}] → {link['url']}")
        
        adm_html = get_page(driver, link['url'], wait=2)
        if not adm_html:
            continue
        
        # 入試ページにOC情報があるか
        adm_oc = check_page_for_oc_dates(adm_html)
        if adm_oc and adm_oc.get('has_oc'):
            print(f"         ✅ 入試ページにOC情報: {adm_oc['dates'][:3]}")
            results['found_pages'].append({
                'url': link['url'],
                'path': f"トップ → {link['text']}",
                'dates': adm_oc['dates'],
                'has_oc_keyword': True,
            })
        
        # 入試ページからOC/イベントリンクを探す
        oc_from_adm = find_links_by_keywords(adm_html, link['url'], NAV_KEYWORDS_PHASE1 + NAV_KEYWORDS_PHASE3)
        
        for oc_link in oc_from_adm[:5]:
            if oc_link['url'] != link['url']:
                print(f"         🔗 [{oc_link['text']}] → {oc_link['url']}")
                
                oc_html = get_page(driver, oc_link['url'], wait=2)
                oc_info_deep = check_page_for_oc_dates(oc_html)
                
                if oc_info_deep:
                    has_oc = oc_info_deep.get('has_oc', False)
                    emoji = "✅" if has_oc else "📅"
                    print(f"            {emoji} 日付: {oc_info_deep['dates'][:5]}")
                    results['found_pages'].append({
                        'url': oc_link['url'],
                        'path': f"トップ → {link['text']} → {oc_link['text']}",
                        'dates': oc_info_deep['dates'],
                        'has_oc_keyword': has_oc,
                    })
                    
                    # さらに深く1段
                    if oc_html and not has_oc:
                        deeper = find_links_by_keywords(oc_html, oc_link['url'], NAV_KEYWORDS_PHASE1)
                        for d in deeper[:2]:
                            if d['url'] != oc_link['url']:
                                print(f"               🔗 [{d['text']}]")
                                d_html = get_page(driver, d['url'], wait=2)
                                d_oc = check_page_for_oc_dates(d_html)
                                if d_oc:
                                    results['found_pages'].append({
                                        'url': d['url'],
                                        'path': f"トップ → {link['text']} → {oc_link['text']} → {d['text']}",
                                        'dates': d_oc['dates'],
                                        'has_oc_keyword': d_oc.get('has_oc', False),
                                    })
    
    # ベストURLを選定
    if results['found_pages']:
        # OC キーワードを含むページを優先
        oc_pages = [p for p in results['found_pages'] if p['has_oc_keyword']]
        if oc_pages:
            # 日付が多い順
            best = max(oc_pages, key=lambda p: len(p['dates']))
        else:
            best = max(results['found_pages'], key=lambda p: len(p['dates']))
        
        results['best_url'] = best['url']
        results['best_path'] = best['path']
        results['best_dates'] = best['dates']
    
    # サマリー
    print(f"\n   📋 結果サマリー:")
    if results['best_url']:
        print(f"      🏆 ベストURL: {results['best_url']}")
        print(f"      📍 経路: {results.get('best_path', 'N/A')}")
        print(f"      📅 日付: {results.get('best_dates', [])[:5]}")
    else:
        print(f"      ❌ OC情報ページが見つかりませんでした")
    
    return results


def main():
    print("\n" + "="*70)
    print("🚀 大学オープンキャンパスURL探索（ナビゲーション方式）")
    print("   人間と同じように: トップ → 入試 → イベント → OC")
    print("="*70)
    
    driver = init_driver()
    all_results = {}
    
    try:
        for uni_name, top_url in TARGET_UNIVERSITIES.items():
            result = navigate_university(uni_name, top_url, driver)
            all_results[uni_name] = result
            time.sleep(1)
    finally:
        driver.quit()
    
    # 最終サマリー
    print("\n\n" + "="*70)
    print("📋 最終結果サマリー")
    print("="*70)
    
    for uni_name, result in all_results.items():
        status = "✅" if result['best_url'] else "❌"
        url = result.get('best_url', 'N/A')
        dates = result.get('best_dates', [])[:3]
        path = result.get('best_path', '')
        print(f"\n{status} {uni_name}")
        print(f"   URL: {url}")
        print(f"   経路: {path}")
        print(f"   日付: {dates}")
    
    # JSON出力
    output_path = 'data/url_discovery.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 詳細結果: {output_path}")


if __name__ == "__main__":
    main()
