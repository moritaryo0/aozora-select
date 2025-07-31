# PythonベースのDockerイメージ
FROM python:3.9

# Node.jsをインストール
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# 作業ディレクトリの作成
WORKDIR /code

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# ポート8000を公開
EXPOSE 8000

# 起動コマンド
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
