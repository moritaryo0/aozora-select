# PythonベースのDockerイメージ
FROM python:3.9

# Node.jsをインストール（curl を先に導入）
RUN apt-get update -y && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの作成
WORKDIR /code

# Pythonの依存関係をインストール（キャッシュ効率化のため先にコピー）
COPY requirements.txt .
RUN pip install -r requirements.txt

# プロジェクトファイルをコピー
COPY . .

# 起動スクリプトに実行権限を付与
RUN chmod +x /code/start.sh

# ポート8000を公開
EXPOSE 8000

# ヘルスチェック（Railway の PORT 環境変数に追従）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD sh -c 'curl -f http://localhost:${PORT:-8000}/health/ || exit 1'

# 起動コマンド（start.sh を使用して migrate/collectstatic 実行後に起動）
CMD ["./start.sh"]
