# news-app
RSSフィードからニュースを取得し、Google Gemini APIを使用して自動でタグ付けと要約を生成するWebアプリケーションです。

## システム構成

```
フロントエンド (HTML/CSS/JS)
       ↓ カテゴリ選択
Flask バックエンド (Python)
       ↓
┌──────┴──────┐
│             │
RSS取得    Gemini API
(Yahoo!/Google)  (タグ・要約生成)
```

## 処理フロー

1. **カテゴリ選択**: ユーザーがドロップダウンからカテゴリを選択
2. **RSS取得**: バックエンドがYahoo!ニュースRSSから最大8件、不足分をGoogle News RSSから補完して10件取得
3. **LLM処理**: 10件のニュースタイトルを1回のGemini APIコールでバッチ処理し、各記事の要約とタグを生成
4. **レスポンス**: JSON形式でフロントエンドに返却
5. **表示**: ニュースカードとしてグリッド表示

## セットアップ

### 必要条件
- Python 3.8以上
- Google Gemini API キー

### インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd news-classification-app

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .env ファイルを編集し、GEMINI_API_KEY を設定
```

### 起動

```bash
python app.py
```

ブラウザで `http://127.0.0.1:5000` にアクセス

## 注意事項

- Gemini API無料枠は **1日20リクエスト** の制限があります
- 本アプリは1カテゴリ切り替えにつき1リクエストを消費します
