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

echo "🔄 ベクトルストア自動準備ロジック..."
# Django を起動前にインポートしないため Bash で確認する
VECTOR_STORE_DIR=${VECTOR_STORE_DIR:-/code/RAG_test/aozora_faiss_index}
if [ "${SKIP_VECTORSTORE_BOOT:-0}" = "1" ]; then
  echo "⏭️ SKIP_VECTORSTORE_BOOT=1 のためベクトルストア準備をスキップします"
else
  if [ -d "$VECTOR_STORE_DIR" ] && [ -n "$(find "$VECTOR_STORE_DIR" -type f -maxdepth 1 2>/dev/null | head -n1)" ]; then
    EXISTS=0
  else
    EXISTS=1
  fi
  echo "🧾 事前状態: path=$VECTOR_STORE_DIR exists=$([ $EXISTS -eq 0 ] && echo true || echo false) files=$(find "$VECTOR_STORE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ') size_kb=$(du -sk "$VECTOR_STORE_DIR" 2>/dev/null | awk '{print $1}')"
  if [ $EXISTS -ne 0 ]; then
    if [ -n "${GOOGLE_DRIVE_FILE_ID:-}" ]; then
      echo "📥 ベクトルストア未検出。Google Drive からダウンロードします..."
      if [ "${VECTORSTORE_FORCE_DOWNLOAD:-0}" = "1" ]; then
        DL_FORCE=--force
      else
        DL_FORCE=
      fi
      REQUIRED=${VECTORSTORE_REQUIRED:-0}
      BG=${VECTORSTORE_BACKGROUND:-1}
      if [ "$REQUIRED" = "1" ]; then
        echo "⏳ 必須モード: 完了まで待機します (VECTORSTORE_REQUIRED=1)"
        if command -v timeout >/dev/null 2>&1; then
          TO=${VECTORSTORE_DOWNLOAD_TIMEOUT:-600}
          if timeout ${TO}s python -u manage.py download_vectorstore $DL_FORCE | sed -n '1,200p'; then
            echo "✅ ベクトルストアのダウンロード完了"
          else
            echo "❌ ベクトルストアのダウンロードに失敗 (timeout=${TO}s)"
            echo "⛔ 起動を中止します"
            exit 1
          fi
        else
          if python -u manage.py download_vectorstore $DL_FORCE | sed -n '1,200p'; then
            echo "✅ ベクトルストアのダウンロード完了"
          else
            echo "❌ ベクトルストアのダウンロードに失敗"
            echo "⛔ 起動を中止します"
            exit 1
          fi
        fi
      else
        if [ "$BG" = "1" ]; then
          echo "🚀 バックグラウンドでダウンロードを開始します (ログ: /code/vectorstore_download.log)"
          nohup sh -c "python -u manage.py download_vectorstore $DL_FORCE >> /code/vectorstore_download.log 2>&1" >/dev/null 2>&1 &
        else
          echo "⏳ フォアグラウンドでダウンロードします (必要に応じて VECTORSTORE_BACKGROUND=1 を設定)"
          if command -v timeout >/dev/null 2>&1; then
            TO=${VECTORSTORE_DOWNLOAD_TIMEOUT:-600}
            timeout ${TO}s python -u manage.py download_vectorstore $DL_FORCE | sed -n '1,200p' || echo "⚠️ ダウンロードが失敗またはタイムアウトしました"
          else
            python -u manage.py download_vectorstore $DL_FORCE | sed -n '1,200p' || echo "⚠️ ダウンロードが失敗しました"
          fi
        fi
      fi
    else
      echo "ℹ️ GOOGLE_DRIVE_FILE_ID が未設定のため自動ダウンロードをスキップします"
    fi
  fi
  echo "🧾 事後状態: path=$VECTOR_STORE_DIR exists=$([ -d "$VECTOR_STORE_DIR" ] && [ -n "$(find "$VECTOR_STORE_DIR" -type f -maxdepth 1 2>/dev/null | head -n1)" ] && echo true || echo false) files=$(find "$VECTOR_STORE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ') size_kb=$(du -sk "$VECTOR_STORE_DIR" 2>/dev/null | awk '{print $1}')"
fi
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

# ここまでで Django を一切インポートしていないため、起動前クラッシュを回避

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