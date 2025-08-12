#!/bin/bash

# Railway起動スクリプト
set -euo pipefail

echo "🚀 Railway起動スクリプト開始"
echo "PORT: ${PORT:-8000}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"
echo "PWD: $(pwd)"
echo "Python version: $(python --version)"

# 依存関係の確認
echo "📦 依存関係確認中..."
pip list | sed -n '1,50p'

# ベクトルストアの状態を表示（RAG未使用でもログで可視化）
echo "🧾 ベクトルストア状態チェック..."
python - << 'PY'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()
from main import rag_service
try:
    rag_service._vectorstore_status()
except Exception as e:
    print(f"⚠️ ベクトルストア状態の取得に失敗: {e}")
PY

# ベクトルストアが無い場合、自動ダウンロード（GOOGLE_DRIVE_FILE_ID が設定されているとき）
echo "🔄 ベクトルストア自動準備ロジック..."
python - << 'PY'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()
from main import rag_service
status = rag_service._vectorstore_status()
sys.exit(0 if status.get('exists') else 1)
PY
VECTORSTORE_EXISTS=$?
if [ "$VECTORSTORE_EXISTS" -ne 0 ]; then
  if [ -n "${GOOGLE_DRIVE_FILE_ID:-}" ]; then
    echo "📥 ベクトルストア未検出。Google Drive からダウンロードします..."
    if [ "${VECTORSTORE_FORCE_DOWNLOAD:-0}" = "1" ]; then
      DL_FORCE=--force
    else
      DL_FORCE=
    fi
    if python -u manage.py download_vectorstore $DL_FORCE; then
      echo "✅ ベクトルストアのダウンロード完了"
    else
      echo "❌ ベクトルストアのダウンロードに失敗"
      if [ "${VECTORSTORE_REQUIRED:-0}" = "1" ]; then
        echo "⛔ VECTORSTORE_REQUIRED=1 のため起動を中止します"
        exit 1
      fi
    fi
  else
    echo "ℹ️ GOOGLE_DRIVE_FILE_ID が未設定のため自動ダウンロードをスキップします"
  fi
fi

# ダウンロード後の最終状態を表示
python - << 'PY'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()
from main import rag_service
try:
    rag_service._vectorstore_status()
except Exception as e:
    print(f"⚠️ ベクトルストア状態の取得に失敗(2): {e}")
PY

# DB接続の事前チェック（どのDBを使うかと接続可否を表示）
echo "🧪 DB接続プリフライトチェック..."
python - << 'PY'
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
try:
    django.setup()
    from django.conf import settings
    from django.db import connection
    cfg = settings.DATABASES['default']
    engine = cfg.get('ENGINE')
    name = cfg.get('NAME')
    user = cfg.get('USER')
    host = cfg.get('HOST')
    port = cfg.get('PORT')
    print(f"DB Engine: {engine}")
    print(f"DB Name: {name}")
    print(f"DB Host: {host}:{port}")
    # 実接続
    connection.connect()
    print("✅ DB接続成功")
except Exception as e:
    print(f"❌ DB接続失敗: {e}")
    sys.exit(1)
PY

# データベースマイグレーション
echo "🗄️ データベースマイグレーション実行中..."
python -u manage.py migrate --noinput --verbosity 2

# 静的ファイル収集
echo "📁 静的ファイル収集中..."
python -u manage.py collectstatic --noinput --verbosity 1

# アプリケーション起動
echo "🌐 Djangoサーバー起動中..."
echo "ポート: ${PORT:-8000}"
python -u manage.py runserver 0.0.0.0:${PORT:-8000}