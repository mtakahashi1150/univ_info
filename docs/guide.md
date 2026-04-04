# 使い方・URL 追加ルール

## 📝 URL を sources.yaml に追加する手順

### ⚠️ 必須ポリシー：URL は検証済みのもののみ

**以下のルールに従わない限り、URL の追加は受け付けません。**

1. **URL は推測・生成で作らない**
2. **あなた自身がブラウザで開いて、内容が表示されることを確認**
3. **確認日時を `last_verified` に記入**
4. **公式 URL（`.ac.jp` 等）を優先**

### 🖥️ 手順

#### 1. ブラウザで URL が実在することを確認

例えば明治大学の場合：

```
URL: https://www.meiji.ac.jp/exam/event/opencampus/
ブラウザで開く → オープンキャンパス情報が表示される ✓
```

#### 2. sources.yaml を編集

```yaml
universities:
  - name: "明治大学"
    sources:
      - name: "公式オープンキャンパス総合案内"
        url: "https://www.meiji.ac.jp/exam/event/opencampus/"  # ← 確認済み URL
        type: "opencampus"
        region: "Tokyo"
        department: "CS"  # 情報系
        frequency: "monthly"
        last_verified: "2026-04-04"  # 実行した日付
```

#### 3. git で commit・push

```bash
git add sources.yaml
git commit -m "Add meiji university opencampus source (verified 2026-04-04)"
git push
```

GitHub Actions が自動的に情報取得を開始します。

---

## 🚀 ローカルで実行

### 初回セットアップ

```bash
# リポジトリをクローン
git clone <repo-url>
cd univ_info

# Python 仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 依存パッケージをインストール
pip install -r requirements.txt

# .env ファイルを作成
cp .env.example .env
# .env を編集してメール設定を入力
```

### 実行

```bash
# 情報取得・正規化・差分検知・（差分があれば）メール通知
python scripts/fetch.py

# メール通知のテスト
python scripts/notify.py
```

### 静的サイトをローカルでプレビュー

```bash
# MkDocs をインストール
pip install mkdocs mkdocs-material

# ローカルサーバを起動
mkdocs serve

# ブラウザで http://localhost:8000 を開く
```

---

## 🏫 追加対象の例

### 東京・神奈川・千葉・埼玉の情報系

実装者がブラウザで確認したもののみ、以下は参考：

- 明治大学
- 早稲田大学
- 慶応義塾大学
- など

### 将来の拡張

- 学科フィルタリング
- 地域フィルタリング
- 非公式ブログ（要判定）

---

## ❌ NG な URL の例

- ❌ 推測で作った URL （実際にブラウザで確認していない）
- ❌ リンク切れ （HTTP 404）
- ❌ スクレーピング禁止の明記 （robots.txt・利用規約）
- ❌ 非常に古い情報 （前年度の古いページなど）

---

## ✅ OK な URL の例

- ✅ 大学公式サイト（`.ac.jp` 等）の公開ページ
- ✅ 入試サイトのオープンキャンパス案内
- ✅ 大学ブログ（公式アカウント）
- ✅ 過去にスクレーピング可能と確認したドメイン

---

**疑問・問題がある場合は [Issues](https://github.com/your-org/univ_info/issues) で報告してください。**
