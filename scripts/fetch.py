#!/usr/bin/env python3
"""
大学オープンキャンパス情報取得・正規化スクリプト

処理フロー：
  1. sources.yaml を読み込む
  2. 各 URL から HTML を取得
  3. イベント情報を抽出・正規化
  4. JSON スナップショットで保存
  5. Markdown 累積表を生成
  6. 差分を検知して通知フラグを立てる
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

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# リポジトリルート
REPO_ROOT = Path(__file__).parent.parent
SOURCES_FILE = REPO_ROOT / 'sources.yaml'
SNAPSHOTS_DIR = REPO_ROOT / 'data' / 'snapshots'
ACCUMULATED_FILE = REPO_ROOT / 'data' / 'accumulated.md'
DIFF_FLAG_FILE = REPO_ROOT / 'data' / '.has_diff'

# HTTP タイムアウト・User-Agent
HTTP_TIMEOUT = 10
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)


class UniversityScraper:
    """大学オープンキャンパス情報スクレイパー"""

    def __init__(self):
        self.snapshots_dir = SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def fetch_url(self, url: str) -> Optional[str]:
        """
        URL から HTML を取得
        
        Args:
            url: 対象 URL
        
        Returns:
            HTML テキスト、失敗時は None
        """
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(
                url,
                headers=headers,
                timeout=HTTP_TIMEOUT
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            logger.info(f"✓ Fetched: {url} (HTTP {response.status_code})")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to fetch {url}: {e}")
            return None

    def extract_events(self, html: str, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        HTML からイベント情報を抽出・正規化
        
        MVP では簡易版：meta タグや <h1>、<p> 等のテキストから日付を抽出
        実装時は、各大学ごとにカスタマイズ可能化する
        
        Args:
            html: HTML テキスト
            source_info: sources.yaml の source エントリ
        
        Returns:
            正規化されたイベント情報のリスト
        """
        soup = BeautifulSoup(html, 'html.parser')
        events = []

        # ページタイトル・説明から基本情報を取得
        title_tag = soup.find('title')
        og_desc = soup.find('meta', property='og:description')
        
        page_title = title_tag.string if title_tag else "不明"
        page_desc = og_desc.get('content', '') if og_desc else ""

        # 簡易版：<h1>～<p> 内のテキストから日付パターンを検索
        # 実運用では、大学サイトの DOM 構造に合わせた抽出ロジックが必要
        import re
        date_pattern = r'(\d{4})[年-](\d{1,2})[月-](\d{1,2})[日]?'
        
        text_content = soup.get_text()
        date_matches = re.findall(date_pattern, text_content)

        if date_matches:
            # 最初に見つかった日付をイベント日付としてセット
            year, month, day = date_matches[0]
            event_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            events.append({
                'title': page_title or source_info.get('name', '不明'),
                'date': event_date,
                'registration_url': source_info.get('url'),
                'details_url': source_info.get('url'),
                'extracted_at': datetime.utcnow().isoformat() + 'Z'
            })
        else:
            logger.warning(f"No date found in {source_info.get('url')}")

        return events

    def save_snapshot(
        self,
        university_name: str,
        source_name: str,
        events: List[Dict[str, Any]],
        source_url: str
    ) -> Path:
        """
        JSON スナップショットを保存
        
        ファイル名: data/snapshots/{university}_{timestamp}.json
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        # 大学名をスラッグ化
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
        """
        最新のスナップショットを読み込む（差分検知用）
        """
        snapshots = sorted(self.snapshots_dir.glob(f"{university_slug}_*.json"), reverse=True)
        if snapshots:
            with open(snapshots[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def has_diff(
        self,
        university_slug: str,
        current_events: List[Dict[str, Any]]
    ) -> bool:
        """
        前回スナップショットとの差分を検知
        
        イベント日付・登録URL が変わったら差分として検知
        """
        last_snapshot = self.load_last_snapshot(university_slug)
        if not last_snapshot:
            logger.info(f"[{university_slug}] First fetch - no previous snapshot")
            return True  # 初回は常に「差分あり」扱い

        last_events = last_snapshot.get('events', [])
        
        # 簡易版：イベント件数が異なる、または最初のイベント情報が異なる
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
    """
    すべてのスナップショットから累積 Markdown 表を生成
    """
    lines = [
        "# 大学オープンキャンパス情報（累積）",
        "",
        "| 大学名 | 学科 | 申込期間 | オープンキャンパス開催日 | 申込URL | 案内ページ | 最終取得日時 | 更新ステータス |",
        "|-------|------|---------|---------------------------|---------|----------|------------|---------|",
    ]

    for snapshot in sorted(all_snapshots, key=lambda x: x.get('fetched_at', ''), reverse=True):
        university = snapshot.get('university', '不明')
        fetched_at = snapshot.get('fetched_at', '')[:10]  # 日付のみ
        source_url = snapshot.get('source_url', '')
        events = snapshot.get('events', [])

        if events:
            event = events[0]
            event_date = event.get('date', '-')
            reg_url = event.get('registration_url', '')
            details_url = event.get('details_url', '')
            
            reg_link = f"[link]({reg_url})" if reg_url else "-"
            details_link = f"[案内]({details_url})" if details_url else "-"
            
            status = f"{fetched_at} 更新あり"  # TODO: 差分検知結果で更新
            
            line = (
                f"| {university} | 情報系 | - | {event_date} | {reg_link} | {details_link} | "
                f"{fetched_at} | {status} |"
            )
            lines.append(line)

    return "\n".join(lines) + "\n"


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("大学オープンキャンパス情報スクレーピング開始")
    logger.info("=" * 60)

    # sources.yaml を読み込む
    config = load_sources()
    universities = config.get('universities', [])

    if not universities:
        logger.warning("⚠ No universities configured in sources.yaml")
        return

    scraper = UniversityScraper()
    all_snapshots = []
    has_any_diff = False

    # 各大学のソースを処理
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

            # URL を取得
            html = scraper.fetch_url(source_url)
            if not html:
                logger.warning(f"  ✗ Failed to fetch {source_name}")
                continue

            # イベント情報を抽出
            events = scraper.extract_events(html, source)
            if not events:
                logger.warning(f"  ⚠ No events extracted from {source_name}")
                continue

            # JSON スナップショットを保存
            snapshot_path = scraper.save_snapshot(
                university_name=uni_name,
                source_name=source_name,
                events=events,
                source_url=source_url
            )

            # スナップショット読み込みてメモリに保持
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
                all_snapshots.append(snapshot)

            # 差分検知
            if scraper.has_diff(uni_slug, events):
                logger.info(f"  → 差分あり: {source_name}")
                has_any_diff = True
            else:
                logger.info(f"  → 差分なし: {source_name}")

    # 累積 Markdown を生成
    accumulated_md = generate_accumulated_markdown(all_snapshots)
    ACCUMULATED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCUMULATED_FILE, 'w', encoding='utf-8') as f:
        f.write(accumulated_md)
    logger.info(f"\n✓ Generated accumulated markdown: {ACCUMULATED_FILE}")

    # 差分フラグを記録（GitHub Actions で通知判定に使用）
    if has_any_diff:
        DIFF_FLAG_FILE.write_text('1')
        logger.info("✓ Difference detected - will send notification")
    else:
        DIFF_FLAG_FILE.write_text('0')
        logger.info("✓ No difference detected - no notification")

    logger.info("=" * 60)
    logger.info("スクレーピング完了")
    logger.info("=" * 60)

    return 0 if has_any_diff else 1  # ステータスコード（通知判定用）


if __name__ == '__main__':
    sys.exit(main())
