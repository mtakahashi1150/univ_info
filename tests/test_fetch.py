#!/usr/bin/env python3
"""
テストスイート
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# スクリプトディレクトリをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import fetch


class TestFetch:
    """fetch.py の単体テスト"""

    def test_load_sources_empty(self, tmp_path):
        """sources.yaml が存在しない場合のテスト"""
        with patch('fetch.SOURCES_FILE', tmp_path / 'nonexistent.yaml'):
            config = fetch.load_sources()
            assert config == {'universities': []}

    def test_load_sources_valid(self, tmp_path):
        """sources.yaml が存在する場合のテスト"""
        sources_file = tmp_path / 'sources.yaml'
        sources_file.write_text("""
universities:
  - name: Test University
    sources:
      - name: Test Source
        url: https://example.com
        type: opencampus
""")
        with patch('fetch.SOURCES_FILE', sources_file):
            config = fetch.load_sources()
            assert len(config['universities']) == 1
            assert config['universities'][0]['name'] == 'Test University'

    def test_scraper_extract_events_with_dates(self):
        """日付を含む HTML からイベント抽出テスト"""
        html = """
        <html>
            <head><title>オープンキャンパス 2026年度</title></head>
            <body>
                <h1>オープンキャンパス案内</h1>
                <p>開催日：2026年6月15日</p>
            </body>
        </html>
        """
        scraper = fetch.UniversityScraper()
        events = scraper.extract_events(html, {'name': 'Test', 'url': 'https://example.com'})
        
        assert len(events) > 0
        assert events[0]['date'] == '2026-06-15'

    def test_scraper_extract_events_no_dates(self):
        """日付なし HTML からのイベント抽出テスト"""
        html = "<html><body><h1>No dates here</h1></body></html>"
        scraper = fetch.UniversityScraper()
        events = scraper.extract_events(html, {'name': 'Test', 'url': 'https://example.com'})
        
        # 日付がない場合はイベントが抽出されない
        assert len(events) == 0

    def test_scraper_save_snapshot(self, tmp_path):
        """JSON スナップショット保存テスト"""
        scraper = fetch.UniversityScraper()
        with patch('fetch.SNAPSHOTS_DIR', tmp_path):
            events = [{'title': 'Event 1', 'date': '2026-06-15'}]
            path = scraper.save_snapshot(
                'Test University',
                'Test Source',
                events,
                'https://example.com'
            )
            
            assert path.exists()
            with open(path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
                assert snapshot['university'] == 'Test University'
                assert len(snapshot['events']) == 1

    def test_has_diff_first_fetch(self, tmp_path):
        """初回フェッチ時は常に差分ありテスト"""
        scraper = fetch.UniversityScraper()
        # snapshots_dir を一時ディレクトリに設定
        scraper.snapshots_dir = tmp_path
        events = [{'title': 'Event 1', 'date': '2026-06-15'}]
        has_diff = scraper.has_diff('test_university', events)
        assert has_diff is True

    def test_has_diff_event_date_changed(self, tmp_path):
        """イベント日付が変わったときの差分検知テスト"""
        scraper = fetch.UniversityScraper()
        with patch('fetch.SNAPSHOTS_DIR', tmp_path):
            # 最初のスナップショット
            events1 = [{'title': 'Event 1', 'date': '2026-06-15'}]
            scraper.save_snapshot('Test', 'Source', events1, 'https://example.com')
            
            # 日付が変わったイベント
            events2 = [{'title': 'Event 1', 'date': '2026-07-20'}]
            has_diff = scraper.has_diff('test', events2)
            assert has_diff is True


def run_tests():
    """テスト実行"""
    import pytest
    return pytest.main([__file__, '-v'])


if __name__ == '__main__':
    sys.exit(run_tests())
