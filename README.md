# 大学オープンキャンパス情報アグリケータ

大学のオープンキャンパス情報を、設定に登録した **検証済み URL** から定期的に取得し、リポジトリ内の Markdown と JSON スナップショットに累積保存します。変更があった場合のみ Gmail で通知し、GitHub Pages で静的サイトとして公開できます。

## 🎯 特徴

- **設定駆動**: `sources.yaml` に URL を記入すれば自動的に情報取得
- **累積保存**: すべての取得履歴を JSON・Markdown に保存して GitHub で閲覧可能
- **差分通知**: 更新があったときのみ Gmail で通知
- **静的公開**: GitHub Pages で累積データを表形式で表示
- **定期実行**: GitHub Actions で自動実行（cron 設定）

## 📋 ディレクトリ構造

```
.
├── README.md
├── sources.yaml                 # 大学・URL 設定
├── .github/workflows/
│   └── fetch-and-notify.yml     # GitHub Actions ワークフロー
├── scripts/
│   ├── fetch.py                 # 取得・正規化スクリプト
│   ├── diff.py                  # 差分検知スクリプト
│   └── notify.py                # メール通知スクリプト
├── data/
│   ├── snapshots/               # JSON スナップショット
│   │   └── {university}_{timestamp}.json
│   └── accumulated.md           # 累積 Markdown 表
├── tests/
│   └── test_fetch.py            # テスト
├── docs/                        # GitHub Pages ソース
│   ├── index.md
│   └── mkdocs.yml
├── .env.example
└── .gitignore
```

## 🔐 必要な環境変数

GitHub Actions Secrets または `.env` ファイルに以下を設定：

| 変数名 | 説明 | 例 |
|-------|------|-----|
| `GMAIL_ADDRESS` | 送信元 Gmail アドレス | `your-account@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail "[アプリ用パスワード](https://myaccount.google.com/apppasswords)" | （16文字） |
| `NOTIFY_TO_EMAIL` | 通知先メールアドレス | `recipient@example.com` |

### Gmail アプリパスワード取得方法

1. [Google アカウント](https://myaccount.google.com/) にアクセス
2. **セキュリティ** → **2段階認証を有効化** （未設定の場合）
3. **アプリ パスワード** をコピー
4. リポジトリ Settings > Secrets に `GMAIL_APP_PASSWORD` として登録

## 📝 URL を sources.yaml に追加する手順

### ⚠️ 必須：URL ポリシー

**以下に従わない URL の追加は受け付けません。**

- URL は **推測・生成で作らない**
- **あなた自身がブラウザで開いて、内容が表示されることを確認**
- 確認日時を `last_verified` に記入
- 大学の公式サイト（`.ac.jp` など）の公式情報ページを優先

### 例

```bash
# 1. ブラウザで以下にアクセスして、オープンキャンパス情報が表示されることを確認
#    https://www.meiji.ac.jp/exam/event/opencampus/

# 2. sources.yaml を編集
# 3. 以下のブロックを university セクションに追加

  - name: "明治大学"
    sources:
      - name: "公式オープンキャンパス総合案内"
        url: "https://www.meiji.ac.jp/exam/event/opencampus/"
        type: "opencampus"
        region: "Tokyo"
        department: "CS"
        frequency: "monthly"
        last_verified: "2026-04-04"
```

その後、

```bash
git add sources.yaml
git commit -m "Add waseda university opencampus source (verified 2026-04-04)"
git push
```

## 🚀 ローカルで実行

### 初回セットアップ

```bash
# リポジトリをクローン
git clone <repo-url>
cd univ_info

# Python 仮想環境作成
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# または
# venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt

# .env ファイルを作成（GitIgnore 済み）
cp .env.example .env
# .env を編集して GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_TO_EMAIL を入力
```

### 実行

```bash
# 情報取得・正規化・差分検知・メール通知
python scripts/fetch.py
```

### ローカルで静的サイトをプレビュー（MkDocs）

```bash
pip install mkdocs
mkdocs serve
# http://localhost:8000 を開く
```

## 📊 出力例

### JSON スナップショット（`data/snapshots/meiji_20260404.json`）

```json
{
  "university": "明治大学",
  "fetched_at": "2026-04-04T12:34:56Z",
  "events": [
    {
      "title": "オープンキャンパス 2026年度",
      "date": "2026-06-15",
      "registration_start": "2026-05-10",
      "registration_url": "https://example.com/register",
      "details_url": "https://www.meiji.ac.jp/exam/event/opencampus/"
    }
  ]
}
```

### Markdown 累積表（`data/accumulated.md`）

| 大学名 | 学科 | 申込期間 | オープンキャンパス開催日 | 申込URL | 案内ページ | 最終取得日時 | 更新ステータス |
|---------|------|---------|---------------------------|---------|----------|------------|---------|
| 明治大学 | CS | 2026-05-10 〜 | 2026-06-15 | [link...] | [公式...] | 2026-04-04 12:34 | 2026-04-04 更新あり |

## 🔄 GitHub Actions 定期実行

`.github/workflows/fetch-and-notify.yml` で以下のスケジュール実行：

```yaml
schedule:
  - cron: '0 8 * * *'  # 毎日 08:00 UTC (17:00 JST)
```

手動トリガーも可能：

```bash
# GitHub UI または CLI
gh workflow run fetch-and-notify.yml
```

## 🧪 テスト

```bash
pytest tests/test_fetch.py -v
```

## 📚 今後の拡張

- [ ] sources に複数大学・複数 URL を段階的に追加
- [ ] 学科別フィルタリング
- [ ] 地域別フィルタリング
- [ ] Slack/Discord 通知対応
- [ ] Web UI での sources 管理

## ⚖️ 注釈

- スクレイピングは各サイトの `robots.txt` と利用規約に従う
- robots.txt に明記されたスクレイプ禁止には従う
- User-Agent を設定し、過剰なアクセスは避ける
- 本番運用前に、対象サイト運営者に確認することを推奨

---

**問題報告・改善提案**: Issues で报告してください。
