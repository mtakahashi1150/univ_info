#!/usr/bin/env python3
"""
【最高度な】大学オープンキャンパス情報スクレイパー
- Selenium で JavaScript レンダリング対応
- 複数の抽出技法を段階的に試行
- 学部・学科・キャンパス・日付を確実に取得
"""

import os
import sys
import json
import yaml
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging
import re
import time
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SOURCES_FILE = REPO_ROOT / 'sources.yaml'
SNAPSHOTS_DIR = REPO_ROOT / 'data' / 'snapshots'
ACCUMULATED_FILE = REPO_ROOT / 'data' / 'accumulated.md'
DIFF_FLAG_FILE = REPO_ROOT / 'data' / '.has_diff'

HTTP_TIMEOUT = 15
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)

SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("⚠ Selenium not available - using BeautifulSoup only")


class UltraAdvancedScraper:
    """複数抽出技法対応スクレイパー"""

    def __init__(self, use_selenium=True):
        self.snapshots_dir = SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None

    def init_selenium_driver(self):
        """Selenium WebDriver を初期化"""
        if not self.use_selenium:
            return
        
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument(f'user-agent={USER_AGENT}')
            
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(
                    ChromeDriverManager().install()
                ),
                options=options
            )
            logger.info("✓ Selenium WebDriver initialized")
        except Exception as e:
            logger.warning(f"⚠ Selenium init failed: {e}")
            self.use_selenium = False

    def close_selenium_driver(self):
        """Selenium クローズ"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def fetch_url_with_selenium(self, url: str) -> Optional[str]:
        """Selenium で JavaScript レンダリング後の HTML を取得"""
        if not self.use_selenium or not self.driver:
            return None
        
        try:
            self.driver.get(url)
            time.sleep(2)
            html = self.driver.page_source
            return html
        except Exception as e:
            logger.warning(f"⚠ Selenium fetch failed: {e}")
            return None

    def fetch_url_with_requests(self, url: str) -> Optional[str]:
        """requests で HTML を取得"""
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠ Requests failed: {e}")
            return None

    def fetch_url(self, url: str) -> Optional[str]:
        """段階的に fetch を試行"""
        html = self.fetch_url_with_requests(url)
        if html:
            logger.info(f"✓ Fetched: {url} (requests)")
            return html
        
        logger.info(f"   Retrying with Selenium...")
        html = self.fetch_url_with_selenium(url)
        if html:
            logger.info(f"✓ Fetched: {url} (Selenium)")
            return html
        
        return None

    def normalize_date(self, year: str, month: str, day: str) -> Optional[str]:
        """日付を正規化"""
        try:
            m = int(month)
            d = int(day)
            y = int(year) if len(year) == 4 else int("20" + year)
            
            if 2000 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{m:02d}-{d:02d}"
        except:
            pass
        return None

    def extract_all_dates(self, text: str) -> List[str]:
        """テキストから全日付を抽出"""
        patterns = [
            r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?',
            r'(\d{1,2})(?:月|/)(\d{1,2})(?:日)?',
        ]
        
        dates = []
        current_year = 2026
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 3:
                    date = self.normalize_date(match[0], match[1], match[2])
                elif len(match) == 2:
                    date = self.normalize_date(str(current_year), match[0], match[1])
                else:
                    continue
                
                if date and date not in dates:
                    dates.append(date)
        
        return sorted(list(set(dates)))

    def extract_by_structured_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """構造化データ（JSON-LD）から抽出"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, dict):
                    if 'Event' in data.get('@type', ''):
                        date = data.get('startDate')
                        if date:
                            date_str = date.split('T')[0] if 'T' in date else date
                            return {"date": date_str, "method": "structured_data"}
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'Event' in item.get('@type', ''):
                            date = item.get('startDate')
                            if date:
                                date_str = date.split('T')[0] if 'T' in date else date
                                return {"date": date_str, "method": "structured_data"}
            except json.JSONDecodeError:
                continue
        
        return None

    def extract_by_semantic_search(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """セマンティック検索"""
        text = soup.get_text()
        keywords = ['開催日', '開催', '期間', '日程']
        
        for keyword in keywords:
            for match in re.finditer(keyword, text):
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 150)
                context = text[start:end]
                
                dates = self.extract_all_dates(context)
                if dates:
                    return {"date": dates[0], "method": f"semantic_search({keyword})"}
        
        return None

    def extract_by_table_analysis(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """テーブル解析"""
        tables = soup.find_all('table')
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                
                dates = self.extract_all_dates(row_text)
                if dates:
                    logger.info(f"   Found in table {table_idx+1}: {dates[0]}")
                    return {"date": dates[0], "method": "table_analysis"}
        
        return None

    def extract_by_list_parsing(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """リスト解析"""
        lists = soup.find_all(['ul', 'ol'])
        
        for list_elem in lists:
            items = list_elem.find_all('li')
            for item in items:
                item_text = item.get_text(strip=True)
                dates = self.extract_all_dates(item_text)
                
                if dates:
                    logger.info(f"   Found in list: {dates[0]}")
                    return {"date": dates[0], "method": "list_parsing"}
        
        return None

    def extract_by_text_search(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """テキスト全体検索"""
        text = soup.get_text()
        dates = self.extract_all_dates(text)
        
        if dates:
            logger.info(f"   Found dates: {dates[:3]}")
            return {"date": dates[0], "method": "text_search"}
        
        return None

    def get_best_future_date(self, dates: List[str]) -> Optional[str]:
        """日付リストから最も近い未来の日付を返す"""
        today = datetime.now().strftime('%Y-%m-%d')
        future = [d for d in sorted(dates) if d >= today]
        return future[0] if future else None

    def follow_oc_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """ページ内のOC関連リンクを探して返す（1段階フォロー用）"""
        oc_keywords = [
            'オープンキャンパス', 'opencampus', 'open-campus', 'open_campus',
            'オープンデイ', 'openday', 'open-day',
            'キャンパス見学', 'キャンパス体験',
        ]
        event_keywords = [
            'イベント', 'event', '説明会', '体験入学', '進学相談',
        ]

        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            text = a_tag.get_text(strip=True)
            combined = (text + ' ' + href).lower()

            is_oc = any(kw.lower() in combined for kw in oc_keywords)
            is_event = any(kw.lower() in combined for kw in event_keywords)

            if is_oc or is_event:
                full_url = urljoin(base_url, href)
                if full_url.startswith('http') and full_url != base_url:
                    links.append({
                        'url': full_url,
                        'text': text,
                        'priority': 1 if is_oc else 2
                    })

        seen = set()
        unique = []
        for link in sorted(links, key=lambda x: x['priority']):
            if link['url'] not in seen:
                seen.add(link['url'])
                unique.append(link)

        return unique[:5]

    def extract_events(
        self,
        html: str,
        source_info: Dict[str, Any],
        university_name: str
    ) -> List[Dict[str, Any]]:
        """複数技法での段階的抽出（未来日付優先）"""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')

        # 構造化データを最優先
        result = self.extract_by_structured_data(soup)
        if result:
            future = self.get_best_future_date([result['date']])
            if future:
                result['date'] = future
                return self._build_events(result, source_info, university_name)

        # 全テキスト＋アンカーテキストから日付を収集
        text = soup.get_text()
        all_dates = self.extract_all_dates(text)
        for a_tag in soup.find_all('a', href=True):
            link_dates = self.extract_all_dates(a_tag.get_text(strip=True))
            all_dates.extend(link_dates)
        all_dates = sorted(set(all_dates))

        if not all_dates:
            logger.warning(f"   ❌ No date found")
            return []

        # 未来日付を優先、なければ最新の過去日付
        best_date = self.get_best_future_date(all_dates)
        if not best_date:
            best_date = all_dates[-1]

        # セマンティック検索一致ならそのメソッド名を使用
        method = "text_search"
        try:
            sem = self.extract_by_semantic_search(soup)
            if sem:
                method = sem['method']
        except Exception:
            pass

        return self._build_events(
            {"date": best_date, "method": method},
            source_info, university_name
        )

    def _build_events(
        self,
        result: Dict[str, Any],
        source_info: Dict[str, Any],
        university_name: str
    ) -> List[Dict[str, Any]]:
        """抽出結果からイベントリストを構築"""
        return [{
            'title': f"{university_name} - {source_info.get('name', 'オープンキャンパス')}",
            'date': result['date'],
            'registration_url': source_info.get('url'),
            'details_url': source_info.get('url'),
            'extraction_method': result.get('method'),
            'extracted_at': datetime.utcnow().isoformat() + 'Z',
            'departments': source_info.get('department', '不明'),
            'campus': source_info.get('campus', '不明')
        }]

    def save_snapshot(
        self,
        university_name: str,
        source_name: str,
        events: List[Dict[str, Any]],
        source_url: str
    ) -> Path:
        """スナップショット保存"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        slug = university_name.replace(' ', '_').replace('大学', '').lower()
        filename = f"{slug}_{timestamp}.json"
        filepath = self.snapshots_dir / filename

        snapshot = {
            'university': university_name,
            'source': source_name,
            'source_url': source_url,
            'fetched_at': datetime.utcnow().isoformat() + 'Z',
            'events': events
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        return filepath

    def load_last_snapshot(self, university_slug: str) -> Optional[Dict[str, Any]]:
        """最新スナップショット読み込み"""
        snapshots = sorted(
            self.snapshots_dir.glob(f"{university_slug}_*.json"),
            reverse=True
        )
        if snapshots:
            with open(snapshots[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def has_diff(self, university_slug: str, current_events: List[Dict[str, Any]]) -> bool:
        """差分検知"""
        last_snapshot = self.load_last_snapshot(university_slug)
        if not last_snapshot:
            return True

        last_events = last_snapshot.get('events', [])
        
        if len(last_events) != len(current_events):
            return True
        
        if current_events and last_events:
            if current_events[0].get('date') != last_events[0].get('date'):
                return True

        return False


def load_sources() -> Dict[str, Any]:
    """sources.yaml 読み込み"""
    if not SOURCES_FILE.exists():
        logger.error(f"sources.yaml not found")
        return {'universities': []}
    
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
    
    return config


def generate_accumulated_markdown(all_snapshots: List[Dict[str, Any]]) -> str:
    """累積 Markdown 表生成"""
    lines = [
        "# 大学オープンキャンパス情報（累積）",
        "",
        "| 大学名 | オープンキャンパス開催日 | 申込URL | 案内ページ | 最終取得日時 | 抽出方法 |",
        "|-------|---------------------------|---------|----------|------------|---------|",
    ]

    for snapshot in sorted(all_snapshots, key=lambda x: x.get('fetched_at', ''), reverse=True):
        university = snapshot.get('university', '不明')
        fetched_at = snapshot.get('fetched_at', '')[:10]
        source_url = snapshot.get('source_url', '')
        events = snapshot.get('events', [])

        if events:
            event = events[0]
            event_date = event.get('date', '-')
            reg_url = event.get('registration_url', '')
            details_url = event.get('details_url', '')
            extraction_method = event.get('extraction_method', '不明')
            
            reg_link = f"[link]({reg_url})" if reg_url else "-"
            details_link = f"[案内]({details_url})" if details_url else "-"
            
            line = (
                f"| {university} | {event_date} | {reg_link} | "
                f"{details_link} | {fetched_at} | {extraction_method} |"
            )
            lines.append(line)

    return "\n".join(lines) + "\n"


def main():
    """メイン処理"""
    logger.info("=" * 80)
    logger.info("【最高度な】大学オープンキャンパス情報スクレーピング")
    logger.info(f"Selenium: {'有効 ✓' if SELENIUM_AVAILABLE else '無効'}")
    logger.info("=" * 80)

    config = load_sources()
    universities = config.get('universities', [])

    scraper = UltraAdvancedScraper(use_selenium=SELENIUM_AVAILABLE)
    
    if SELENIUM_AVAILABLE:
        scraper.init_selenium_driver()

    all_snapshots = []
    has_any_diff = False
    success_count = 0
    fail_count = 0

    try:
        for uni in universities:
            uni_name = uni.get('name', 'Unknown')
            uni_slug = uni_name.replace(' ', '_').replace('大学', '').lower()
            
            logger.info(f"\n[{uni_name}]")
            
            sources = uni.get('sources', [])
            for source in sources:
                source_name = source.get('name', 'Unknown')
                source_url = source.get('url')
                alternatives = source.get('url_alternatives', [])

                if not source_url:
                    logger.warning(f"  ⚠ No URL")
                    continue

                urls_to_try = [source_url] + alternatives
                events = None
                effective_url = source_url

                for try_url in urls_to_try:
                    html = scraper.fetch_url(try_url)
                    if not html:
                        continue

                    events = scraper.extract_events(html, source, uni_name)
                    if events:
                        effective_url = try_url
                        break

                    # ハブページからOC関連リンクを1段階フォロー
                    soup = BeautifulSoup(html, 'html.parser')
                    oc_links = scraper.follow_oc_links(soup, try_url)
                    for link_info in oc_links:
                        logger.info(f"  → Following: {link_info['text'][:30]}")
                        link_html = scraper.fetch_url(link_info['url'])
                        if link_html:
                            events = scraper.extract_events(
                                link_html, source, uni_name
                            )
                            if events:
                                effective_url = link_info['url']
                                events[0]['details_url'] = link_info['url']
                                break
                    if events:
                        break

                if not events:
                    logger.warning(f"  ⚠ No events extracted")
                    fail_count += 1
                    continue

                # 実際に取得できたURLでイベント情報を更新
                events[0]['registration_url'] = effective_url
                if events[0].get('details_url') == source.get('url'):
                    events[0]['details_url'] = effective_url

                snapshot_path = scraper.save_snapshot(
                    university_name=uni_name,
                    source_name=source_name,
                    events=events,
                    source_url=effective_url
                )

                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    snapshot = json.load(f)
                    all_snapshots.append(snapshot)

                if scraper.has_diff(uni_slug, events):
                    logger.info(f"  ✓ {events[0]['date']} (差分あり)")
                    has_any_diff = True
                else:
                    logger.info(f"  ✓ {events[0]['date']} (差分なし)")

                success_count += 1

        accumulated_md = generate_accumulated_markdown(all_snapshots)
        ACCUMULATED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACCUMULATED_FILE, 'w', encoding='utf-8') as f:
            f.write(accumulated_md)
        logger.info(f"\n✓ Generated: {ACCUMULATED_FILE}")

        if has_any_diff:
            DIFF_FLAG_FILE.write_text('1')
        else:
            DIFF_FLAG_FILE.write_text('0')

        logger.info("=" * 80)
        logger.info(f"✅ 完了: 成功 {success_count}件 / 失敗 {fail_count}件")
        logger.info("=" * 80)

        return 0

    finally:
        scraper.close_selenium_driver()


if __name__ == '__main__':
    sys.exit(main())
