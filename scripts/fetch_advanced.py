#!/usr/bin/env python3
"""
高度な大学オープンキャンパス情報スクレイパー
- 大学別カスタムプロファイルで確実なデータ抽出
- 学部・学科・キャンパス情報を分離取得
- 複数の抽出技法を組合わせで堅牢性向上
"""

import os
import sys
import json
import yaml
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SOURCES_FILE = REPO_ROOT / 'sources.yaml'
SNAPSHOTS_DIR = REPO_ROOT / 'data' / 'snapshots'
ACCUMULATED_FILE = REPO_ROOT / 'data' / 'accumulated.md'
DIFF_FLAG_FILE = REPO_ROOT / 'data' / '.has_diff'

HTTP_TIMEOUT = 10
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)

# ============ 大学別のカスタム抽出プロファイル ============
UNIVERSITY_PROFILES = {
    "東京理科大学": {
        "name": "東京理科大学",
        "departments": ["創域情報学部", "工学部", "先進工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})/(\d{1,2})/(\d{4})",
        ],
        "extractors": ["text_search", "meta_tags", "table_parse"]
    },
    "明治大学": {
        "name": "明治大学",
        "departments": ["理工学部", "総合数理学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})月(\d{1,2})日",
        ],
        "extractors": ["text_search", "link_text", "json_ld"]
    },
    "電気通信大学": {
        "name": "電気通信大学",
        "departments": ["情報理工学域", "工学域"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "heading_parse"]
    },
    "東京都市大学": {
        "name": "東京都市大学",
        "departments": ["情報工学部", "理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})/(\d{1,2})",
        ],
        "extractors": ["text_search", "table_parse"]
    },
    "中央大学": {
        "name": "中央大学",
        "departments": ["国際情報学部", "基幹理工学部", "社会理工学部", "先進理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})月(\d{1,2})日",
        ],
        "extractors": ["text_search", "link_text"]
    },
    "早稲田大学": {
        "name": "早稲田大学",
        "departments": ["基幹理工学部", "創造理工学部", "先進理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "table_parse"]
    },
    "慶應義塾大学": {
        "name": "慶應義塾大学",
        "departments": ["理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})/(\d{1,2})",
        ],
        "extractors": ["text_search", "link_parse"]
    },
    "上智大学": {
        "name": "上智大学",
        "departments": ["理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
            r"(\d{1,2})月(\d{1,2})日",
        ],
        "extractors": ["text_search"]
    },
    "青山学院大学": {
        "name": "青山学院大学",
        "departments": ["理工学部", "社会情報学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "table_parse"]
    },
    "立教大学": {
        "name": "立教大学",
        "departments": ["人工知能科学部", "理学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "link_text"]
    },
    "法政大学": {
        "name": "法政大学",
        "departments": ["情報科学部", "理工学部", "デザイン工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search"]
    },
    "学習院大学": {
        "name": "学習院大学",
        "departments": ["理学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search"]
    },
    "芝浦工業大学": {
        "name": "芝浦工業大学",
        "departments": ["工学部", "システム理工学域"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "table_parse"]
    },
    "東京電機大学": {
        "name": "東京電機大学",
        "departments": ["システムデザイン工学部", "未来科学部", "工学部", "理工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search"]
    },
    "工学院大学": {
        "name": "工学院大学",
        "departments": ["工学部", "先端工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search", "link_parse"]
    },
    "東京工科大学": {
        "name": "東京工科大学",
        "departments": ["コンピュータサイエンス学部", "工学部"],
        "date_patterns": [
            r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})",
        ],
        "extractors": ["text_search"]
    },
}


class AdvancedUniversityScraper:
    """高度なスクレイパー（複数抽出技法を組合わせ）"""

    def __init__(self):
        self.snapshots_dir = SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def fetch_url(self, url: str) -> Optional[str]:
        """URL から HTML を取得"""
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(
                url,
                headers=headers,
                timeout=HTTP_TIMEOUT
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            logger.info(f"✓ Fetched: {url}")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to fetch {url}: {e}")
            return None

    def normalize_date(self, year: str, month: str, day: str) -> str:
        """日付を正規化（YYYY-MM-DD）"""
        try:
            m = int(month)
            d = int(day)
            y = int(year) if len(year) == 4 else int("20" + year)
            return f"{y:04d}-{m:02d}-{d:02d}"
        except:
            return None

    def extract_date_from_patterns(
        self,
        text: str,
        patterns: List[str],
        current_year: int = 2026
    ) -> Optional[str]:
        """パターンマッチングで日付を抽出"""
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # マッチ結果が複数の場合（グループがある）
                if isinstance(matches[0], tuple):
                    for match in matches:
                        if len(match) == 3:
                            year, month, day = match
                            date = self.normalize_date(year, month, day)
                            if date:
                                return date
                        elif len(match) == 2:
                            month, day = match
                            date = self.normalize_date(str(current_year), month, day)
                            if date:
                                return date
        return None

    def extract_from_text_search(
        self,
        soup: BeautifulSoup,
        profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """テキスト検索で情報を抽出"""
        text = soup.get_text()
        
        # 日付を抽出
        date_patterns = profile.get("date_patterns", [])
        dates_found = []
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 3:
                    year, month, day = match
                    date = self.normalize_date(year, month, day)
                    if date and date not in dates_found:
                        dates_found.append(date)
                elif len(match) == 2:
                    month, day = match
                    date = self.normalize_date("2026", month, day)
                    if date and date not in dates_found:
                        dates_found.append(date)
        
        if dates_found:
            # 複数の日付がある場合、最も近い将来の日付を選ぶ
            dates_found.sort()
            return {
                "date": dates_found[0],
                "method": "text_search",
                "all_dates": dates_found
            }
        return None

    def extract_from_table_parse(
        self,
        soup: BeautifulSoup,
        profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """テーブル解析で情報を抽出"""
        tables = soup.find_all('table')
        
        date_patterns = profile.get("date_patterns", [])
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                row_text = ' '.join(cells)
                
                # 日付パターンをマッチ
                for pattern in date_patterns:
                    matches = re.findall(pattern, row_text)
                    if matches:
                        match = matches[0]
                        if len(match) == 3:
                            year, month, day = match
                            date = self.normalize_date(year, month, day)
                            if date:
                                return {
                                    "date": date,
                                    "method": "table_parse",
                                    "row": row_text
                                }
        return None

    def extract_from_link_text(
        self,
        soup: BeautifulSoup,
        profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """リンクテキストから情報を抽出"""
        date_patterns = profile.get("date_patterns", [])
        
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            combined = f"{link_text} {href}"
            
            for pattern in date_patterns:
                matches = re.findall(pattern, combined)
                if matches:
                    match = matches[0]
                    if len(match) == 3:
                        year, month, day = match
                        date = self.normalize_date(year, month, day)
                        if date:
                            return {
                                "date": date,
                                "method": "link_text",
                                "link": link_text
                            }
        return None

    def extract_events(
        self,
        html: str,
        source_info: Dict[str, Any],
        university_name: str
    ) -> List[Dict[str, Any]]:
        """複数の技法を組み合わせてイベント情報を抽出"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # プロファイルを取得
        profile = UNIVERSITY_PROFILES.get(university_name, {
            "departments": [],
            "date_patterns": [r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})'],
            "extractors": ["text_search", "table_parse"]
        })
        
        extractors = profile.get("extractors", ["text_search"])
        
        # 複数の抽出方法を試行（優先度順）
        result = None
        
        for extractor_name in extractors:
            if extractor_name == "text_search":
                result = self.extract_from_text_search(soup, profile)
            elif extractor_name == "table_parse":
                result = self.extract_from_table_parse(soup, profile)
            elif extractor_name == "link_text":
                result = self.extract_from_link_text(soup, profile)
            
            if result:
                logger.info(f"   ✓ Extracted via {extractor_name}: {result['date']}")
                break
        
        if not result:
            logger.warning(f"   ⚠ No date found for {university_name}")
            return []
        
        # イベント情報を構築
        events = [{
            'title': f"{university_name} - {source_info.get('name', 'オープンキャンパス')}",
            'date': result['date'],
            'departments': profile.get("departments", []),
            'registration_url': source_info.get('url'),
            'details_url': source_info.get('url'),
            'extraction_method': result.get('method'),
            'extracted_at': datetime.utcnow().isoformat() + 'Z'
        }]
        
        return events

    def save_snapshot(
        self,
        university_name: str,
        source_name: str,
        events: List[Dict[str, Any]],
        source_url: str
    ) -> Path:
        """JSON スナップショットを保存"""
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

        logger.info(f"✓ Saved snapshot: {filepath}")
        return filepath

    def load_last_snapshot(self, university_slug: str) -> Optional[Dict[str, Any]]:
        """最新のスナップショットを読み込む"""
        snapshots = sorted(
            self.snapshots_dir.glob(f"{university_slug}_*.json"),
            reverse=True
        )
        if snapshots:
            with open(snapshots[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def has_diff(self, university_slug: str, current_events: List[Dict[str, Any]]) -> bool:
        """前回スナップショットとの差分を検知"""
        last_snapshot = self.load_last_snapshot(university_slug)
        if not last_snapshot:
            logger.info(f"[{university_slug}] First fetch")
            return True

        last_events = last_snapshot.get('events', [])
        
        if len(last_events) != len(current_events):
            return True
        
        if current_events and last_events:
            if current_events[0].get('date') != last_events[0].get('date'):
                return True

        return False


def load_sources() -> Dict[str, Any]:
    """sources.yaml を読み込む"""
    if not SOURCES_FILE.exists():
        logger.error(f"sources.yaml not found: {SOURCES_FILE}")
        return {'universities': []}
    
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
    
    return config


def generate_accumulated_markdown(all_snapshots: List[Dict[str, Any]]) -> str:
    """累積 Markdown 表を生成"""
    lines = [
        "# 大学オープンキャンパス情報（累積）",
        "",
        "| 大学名 | 学科 | オープンキャンパス開催日 | 申込URL | 案内ページ | 最終取得日時 | 抽出方法 |",
        "|-------|------|---------------------------|---------|----------|------------|---------|",
    ]

    for snapshot in sorted(all_snapshots, key=lambda x: x.get('fetched_at', ''), reverse=True):
        university = snapshot.get('university', '不明')
        fetched_at = snapshot.get('fetched_at', '')[:10]
        source_url = snapshot.get('source_url', '')
        events = snapshot.get('events', [])

        if events:
            event = events[0]
            event_date = event.get('date', '-')
            departments = ', '.join(event.get('departments', ['情報系'])[:2])
            reg_url = event.get('registration_url', '')
            details_url = event.get('details_url', '')
            extraction_method = event.get('extraction_method', '不明')
            
            reg_link = f"[link]({reg_url})" if reg_url else "-"
            details_link = f"[案内]({details_url})" if details_url else "-"
            
            line = (
                f"| {university} | {departments} | {event_date} | {reg_link} | "
                f"{details_link} | {fetched_at} | {extraction_method} |"
            )
            lines.append(line)

    return "\n".join(lines) + "\n"


def main():
    """メイン処理"""
    logger.info("=" * 70)
    logger.info("【高度な】大学オープンキャンパス情報スクレーピング開始")
    logger.info("=" * 70)

    config = load_sources()
    universities = config.get('universities', [])

    if not universities:
        logger.warning("⚠ No universities configured in sources.yaml")
        return

    scraper = AdvancedUniversityScraper()
    all_snapshots = []
    has_any_diff = False
    success_count = 0
    fail_count = 0

    for uni in universities:
        uni_name = uni.get('name', 'Unknown')
        uni_slug = uni_name.replace(' ', '_').replace('大学', '').lower()
        
        logger.info(f"\n[{uni_name}]")
        
        sources = uni.get('sources', [])
        for source in sources:
            source_name = source.get('name', 'Unknown')
            source_url = source.get('url')

            if not source_url:
                logger.warning(f"  ⚠ Skipping {source_name}: no URL")
                continue

            html = scraper.fetch_url(source_url)
            if not html:
                logger.warning(f"  ✗ Failed to fetch {source_name}")
                fail_count += 1
                continue

            events = scraper.extract_events(html, source, uni_name)
            if not events:
                logger.warning(f"  ⚠ No events extracted from {source_name}")
                fail_count += 1
                continue

            snapshot_path = scraper.save_snapshot(
                university_name=uni_name,
                source_name=source_name,
                events=events,
                source_url=source_url
            )

            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
                all_snapshots.append(snapshot)

            if scraper.has_diff(uni_slug, events):
                logger.info(f"  → 差分あり: {source_name}")
                has_any_diff = True
            else:
                logger.info(f"  → 差分なし: {source_name}")

            success_count += 1

    accumulated_md = generate_accumulated_markdown(all_snapshots)
    ACCUMULATED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCUMULATED_FILE, 'w', encoding='utf-8') as f:
        f.write(accumulated_md)
    logger.info(f"\n✓ Generated accumulated markdown: {ACCUMULATED_FILE}")

    if has_any_diff:
        DIFF_FLAG_FILE.write_text('1')
        logger.info("✓ Difference detected - will send notification")
    else:
        DIFF_FLAG_FILE.write_text('0')
        logger.info("✓ No difference detected - no notification")

    logger.info("=" * 70)
    logger.info(f"スクレーピング完了: 成功 {success_count}件 / 失敗 {fail_count}件")
    logger.info("=" * 70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
