#!/usr/bin/env python3
"""
GitHub Pages 用の docs/index.md を生成
data/accumulated.md の内容を埋め込む
"""
import json
from pathlib import Path
from datetime import datetime

accumulated_file = Path('data/accumulated.md')
output_file = Path('docs/index.md')

# Get current time JST
now_jst = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

# Read accumulated data
if accumulated_file.exists():
    accumulated_content = accumulated_file.read_text()
    # Extract table (skip first line which is "# title")
    lines = accumulated_content.split('\n')
    table_content = '\n'.join(lines[1:]).strip()  # Skip title, keep everything else
else:
    table_content = "| （データ取得中...） | | | | | | |"

# Generate index.md
output = f"""# 大学オープンキャンパス情報

このページは、定期的に自動収集された大学オープンキャンパス情報を表示しています。

**最終更新**: {now_jst} に自動更新

---

## 収集対象大学とイベント情報

{table_content}

---

## 📊 データについて

- **ソース**: `sources.yaml` に登録された検証済みURL からの自動スクレイピング
- **更新頻度**: 1日1回（朝5時 JST）
- **形式**: Markdown テーブル + JSON スナップショット
- **履歴保管**: GitHub リポジトリに完全履歴を蓄積

## 📧 新規情報通知

テーブルデータに新規追加があった場合、メール通知が送信されます。

---

**詳細**: [GitHub リポジトリ](https://github.com/mtakahashi1150/univ_info/tree/main/data)
"""

output_file.write_text(output)
print(f"✅ docs/index.md を生成しました")
print(f"   更新日時: {now_jst}")
print(f"   行数: {len(output.split(chr(10)))}")
