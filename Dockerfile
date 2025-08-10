# PythonベースのDockerイメージ
FROM python:3.9

# Node.jsをインストール
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# 作業ディレクトリの作成
WORKDIR /code

# Pythonの依存関係をインストール（キャッシュ効率化のため先にコピー）
COPY requirements.txt .
RUN pip install -r requirements.txt

# プロジェクトファイルをコピー
COPY . .

# ポート8000を公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

# 起動コマンド
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
