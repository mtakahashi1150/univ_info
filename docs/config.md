# 設定・スキーマ解説

## sources.yaml スキーマ

### トップレベル

```yaml
universities:  # 大学のリスト
  - ...
```

### university エントリ

```yaml
- name: str               # 大学名（公式表記）
  sources:               # 情報ソースのリスト
    - ...
```

### source エントリ

```yaml
- name: str              # ソース名（"公式オープンキャンパス総合案内" など）
  url: str               # URL（ブラウザで確認済みのもののみ）
  type: str              # ページ種別 (opencampus | event | info)
  region: str            # （任意）地域 (Tokyo | Kanagawa | Chiba | Saitama)
  department: str        # （任意）学科タグ (CS | Engineering | Info | etc.)
  frequency: str         # （任意）更新頻度想定 (daily | weekly | monthly)
  last_verified: date    # （推奨）最後に確認した日付 (YYYY-MM-DD)
```

## 完全な sources.yaml 例

```yaml
universities:
  - name: "明治大学"
    sources:
      - name: "公式オープンキャンパス総合案内"
        url: "https://www.meiji.ac.jp/exam/event/opencampus/"
        type: "opencampus"
        region: "Tokyo"
        department: "CS"
        frequency: "monthly"
        last_verified: "2026-04-04"
      
      - name: "情報系学部案内"
        url: "https://www.meiji.ac.jp/academics/school/info/"
        type: "info"
        region: "Tokyo"
        department: "CS"
        frequency: "monthly"
        last_verified: "2026-04-04"

  - name: "早稲田大学"
    sources:
      - name: "公式オープンキャンパス"
        url: "https://www.waseda.jp/school/admission/events/opencampus/"
        type: "opencampus"
        region: "Tokyo"
        department: "CS"
        frequency: "monthly"
        last_verified: "2026-04-04"
```

## JSON スナップショットスキーマ

ファイル名: `data/snapshots/{university_slug}_{timestamp}.json`

```json
{
  "university": "明治大学",
  "source": "公式オープンキャンパス総合案内",
  "source_url": "https://www.meiji.ac.jp/exam/event/opencampus/",
  "fetched_at": "2026-04-04T12:34:56Z",
  "events": [
    {
      "title": "オープンキャンパス 2026年度",
      "date": "2026-06-15",
      "registration_url": "https://example.com/register",
      "details_url": "https://www.meiji.ac.jp/exam/event/opencampus/",
      "extracted_at": "2026-04-04T12:34:56Z"
    }
  ]
}
```

## Markdown 累積表スキーマ

ファイル: `data/accumulated.md`

| 列 | 説明 |
|---|-----|
| 大学名 | university name |
| 学科 | 情報系・工学部など |
| 申込期間 | registration period (e.g., "2026-05-10 〜 2026-06-10") |
| オープンキャンパス開催日 | event date (YYYY-MM-DD) |
| 申込URL | registration link |
| 案内ページ | details link |
| 最終取得日時 | last fetched datetime |
| 更新ステータス | "2026-04-04 更新あり" / "3日更新なし" |

## 環境変数・Secrets 一覧

### GitHub Actions Secrets に登録する変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `GMAIL_ADDRESS` | 送信元 Gmail アドレス | `your-account@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail "[アプリ用パスワード](https://myaccount.google.com/apppasswords)" | `xxxx xxxx xxxx xxxx` |
| `NOTIFY_TO_EMAIL` | 通知先メールアドレス | `recipient@example.com` |

### ローカル .env ファイル（GitIgnore 済み）

```bash
GMAIL_ADDRESS=your-account@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFY_TO_EMAIL=recipient@example.com
DEBUG=false
```

---

## CI/CD ワークフロー

### GitHub Actions

`.github/workflows/fetch-and-notify.yml`

**トリガー:**
- Cron: 毎日 08:00 UTC
- 手動: `gh workflow run fetch-and-notify.yml`

**ステップ:**
1. リポジトリをチェックアウト
2. Python 環境をセットアップ
3. 依存パッケージをインストール
4. 情報取得・正規化（`scripts/fetch.py`）
5. 変更を commit・push
6. 差分があれば Gmail 通知（`scripts/notify.py`）

### ローカル cron（代替）

`.env` ファイルを配置のうえ、以下を実行：

```bash
0 8 * * * cd /path/to/univ_info && source venv/bin/activate && python scripts/fetch.py
```

---

## 拡張可能性

### 今後のプラグイン・パーサー

各大学の HTML 構造は異なるため、`scripts/fetch.py` の `extract_events()` メソッドを拡張：

```python
# 例：サイト別パーサー
if 'meiji.ac.jp' in url:
    events = parse_meiji(html)
elif 'waseda.jp' in url:
    events = parse_waseda(html)
```

### Secrets の追加

Gmail 以外のメール（SMTP）、Slack、Discord など：

```yaml
env:
  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
  ...
```

---

**ご質問は [GitHub Discussions](https://github.com/your-org/univ_info/discussions) をご利用ください。**
