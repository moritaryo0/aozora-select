#!/bin/bash

# Railway起動スクリプト
set -e

echo "🚀 Railway起動スクリプト開始"
echo "PORT: ${PORT:-8000}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"
echo "PWD: $(pwd)"
echo "Python version: $(python --version)"

# 依存関係の確認
echo "📦 依存関係確認中..."
pip list

# データベースマイグレーション
echo "🗄️ データベースマイグレーション実行中..."
python manage.py migrate --noinput

# 静的ファイル収集
echo "📁 静的ファイル収集中..."
python manage.py collectstatic --noinput

# アプリケーション起動
echo "🌐 Djangoサーバー起動中..."
echo "ポート: ${PORT:-8000}"
python manage.py runserver 0.0.0.0:${PORT:-8000} 