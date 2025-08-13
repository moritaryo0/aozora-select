# 青空セレクト（ベータ版）

> あなたの今に寄り添う短編を、青空文庫から

青空セレクトは、位置情報と天気情報に基づいて青空文庫から最適な短編小説を推薦するWebアプリケーションです。

##  主な機能

###  **天気連動推薦システム**
- リアルタイムの位置情報と天気データを取得
- 天気・季節・時間帯に応じた作品推薦
- AI（Google Gemini）とシンプル推薦の2つのモード

###  **青空文庫との連携**
- 青空文庫の豊富な短編作品ライブラリ
- 作品の本文プレビュー機能
- 人気作品ランキング表示

###  **モダンなUI/UX**
- Material Design 3 準拠のデザイン
- ダークモード対応
- レスポンシブデザイン（モバイル対応）

##  技術スタック

- **Backend**: Django 4.2.7 + Django REST Framework
- **Frontend**: HTML/CSS/JavaScript（Material Design 3）
- **Database**: PostgreSQL（本番）/ SQLite（開発）
- **AI**: Google Gemini API + LangChain
- **天気API**: OpenWeatherMap API
- **Deploy**: Railway

##  クイックスタート

### 1. リポジトリのクローン
```bash
git clone https://github.com/yourusername/aozora-select.git
cd aozora-select
```

### 2. 環境変数の設定
```bash
# .envファイルの作成
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# OPENWEATHERMAP_API_KEY=あなたのAPIキー
# GOOGLE_API_KEY=あなたのAPIキー
```

### 3. 開発方法の選択

####  **Docker での開発（推奨）**
```bash
# Dockerコンテナを起動
docker-compose up -d

# 環境変数の確認
docker-compose exec aozora-short-test python manage.py check_env

# API接続をテスト
docker-compose exec aozora-short-test python manage.py test_apis

# データベースのマイグレーション
docker-compose exec aozora-short-test python manage.py migrate
```

http://localhost:8001 でアプリケーションにアクセスできます。

#### **ローカル環境での開発**
```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の確認
python manage.py check_env

# API接続をテスト
python manage.py test_apis

# データベースの準備
python manage.py migrate
python manage.py createsuperuser

# 開発サーバーの起動
python manage.py runserver
```

http://localhost:8000 でアプリケーションにアクセスできます。

##  環境変数

`.env.example`をコピーして`.env`を作成し、以下の値を設定してください：

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# API設定
OPENWEATHERMAP_API_KEY=your-openweather-api-key
GOOGLE_API_KEY=your-google-api-key
```

### APIキーの取得方法

1. **OpenWeatherMap API**: https://openweathermap.org/api
2. **Google Gemini API**: https://ai.google.dev/

## 📱 使い方

1. **位置情報の許可**: ブラウザで位置情報の使用を許可
2. **天気情報の表示**: 現在地の天気が自動表示
3. **推薦モードの選択**: 
   -  シンプル版：ルールベースの高速推薦
   - AI版：Google Geminiによる詳細な推薦
4. **作品の取得**: 「今すぐ作品を推薦してもらう」ボタンをクリック

##  デプロイ

### Railway での本番デプロイ

1. GitHubリポジトリをRailwayに接続
2. PostgreSQLデータベースを追加
3. 環境変数を設定：
   ```
   SECRET_KEY=新しいランダムキー
   DEBUG=False
   ALLOWED_HOSTS=.railway.app
   OPENWEATHERMAP_API_KEY=あなたのAPIキー
   GOOGLE_API_KEY=あなたのAPIキー
   ```
4. 自動デプロイが開始されます

##  今後の予定

- [ ] ユーザー認証とお気に入り機能
- [ ] 読書履歴の記録
- [ ] SNS機能（感想共有）
- [ ] 通勤時間に合わせた作品検索
- [ ] パーソナライズド推薦
- [ ] 自作小説投稿機能

##  開発に参加

プルリクエストやIssueは大歓迎です！

##  ライセンス

このプロジェクトはMITライセンスの下で公開されています。

##  クレジット

- [青空文庫](https://www.aozora.gr.jp/): 作品データの提供
- [OpenWeatherMap](https://openweathermap.org/): 天気情報API
- [Google AI](https://ai.google.dev/): Gemini API
- [Material Design](https://m3.material.io/): UIデザインシステム

---

**青空セレクト開発チーム** 📚✨ 