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

# Generate index.md (シンプル版 - データテーブルのみ)
output = f"""{table_content}

---

*最終更新: {now_jst}*
"""

output_file.write_text(output)
print(f"✅ docs/index.md を生成しました")
print(f"   更新日時: {now_jst}")
print(f"   行数: {len(output.split(chr(10)))}")
