#!/usr/bin/env python3
"""
GitHub Pages 用の docs/index.md を生成
UX重視の設計：
- サマリービューと詳細ビューを分離
- スマートフォン対応
- 大学名は詳細セクションのアンカーリンク
- 新しいウィンドウで外部リンク開放
"""
import json
from pathlib import Path
from datetime import datetime

snapshots_dir = Path('data/snapshots')
output_file = Path('docs/index.md')

# Get current time JST
now_jst = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

# Load the latest snapshot for each university
universities_data = {}

for snapshot_file in sorted(snapshots_dir.glob('*.json'), reverse=True):
    try:
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
            uni_name = snapshot.get('university')
            # Skip Test entries
            if uni_name and 'test' not in uni_name.lower() and uni_name not in universities_data:
                universities_data[uni_name] = snapshot
    except:
        continue

# Build summary table
summary_rows = []
for uni_name in sorted(universities_data.keys()):
    snapshot = universities_data[uni_name]
    events = snapshot.get('events', [])
    fetched_at = snapshot.get('fetched_at', '')[:10]
    
    if events:
        event = events[0]
        event_date = event.get('date', '-')
        departments = event.get('departments', '不明')
        campus = event.get('campus', '不明')
        
        # Compact display: abbreviate for table
        # Split departments and campus by slash, take first few
        dept_short = departments.split('・')[0][:10] if '・' in departments else departments[:10]
        campus_short = campus.split('・')[0][:8] if '・' in campus else campus[:8]
        dept_campus = f"{dept_short}\n{campus_short}"
        
        # Create anchor link to details section
        anchor_id = uni_name.replace(' ', '_').replace('大学', '').lower()
        summary_rows.append(f"| [{uni_name}](#{anchor_id}) | {dept_campus} | {event_date} | {fetched_at} |")

# Build summary table header
summary_table = """| 大学名 | 対象学部・キャンパス | 最新開催予定日 | 更新日 |
|-------|----------|------------|--------|
"""
summary_table += '\n'.join(summary_rows)

# Build details sections
details_sections = []

for uni_name in sorted(universities_data.keys()):
    snapshot = universities_data[uni_name]
    events = snapshot.get('events', [])
    source_url = snapshot.get('source_url', '')
    fetched_at = snapshot.get('fetched_at', '')
    
    if events:
        event = events[0]
        extraction_method = event.get('extraction_method', '-')
        departments = event.get('departments', '不明')
        campus = event.get('campus', '不明')
    else:
        extraction_method = '-'
        departments = '不明'
        campus = '不明'
    
    anchor_id = uni_name.replace(' ', '_').replace('大学', '').lower()
    
    details_section = f"""### {uni_name}

- **最終更新**: {fetched_at}
- **最新開催日**: {events[0].get('date', '-') if events else '-'}
- **対象学部**: {departments}
- **キャンパス**: {campus}
- **抽出方法**: {extraction_method}
- **詳細情報**: [オープンキャンパス案内ページ]({source_url}){{: target="_blank"}}

---
"""
    
    details_sections.append(details_section)

# Generate index.md
output = f"""# 大学オープンキャンパス情報

**最終更新**: {now_jst}

## 📋 開催予定一覧

{summary_table}

---

## 📍 詳細情報

{chr(10).join(details_sections)}

*このページは毎日朝5時（JST）に自動更新されます。*
"""

output_file.write_text(output)
print(f"✅ docs/index.md を生成しました")
print(f"   更新日時: {now_jst}")
print(f"   大学数: {len(universities_data)}")
print(f"   行数: {len(output.split(chr(10)))}")
