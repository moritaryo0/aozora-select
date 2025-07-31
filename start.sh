#!/bin/bash
set -e

echo "🚀 Starting Container with detailed logging"
echo "📅 Current time: $(date)"
echo "💾 Available memory: $(free -m || echo 'Memory info not available')"
echo "📍 Working directory: $(pwd)"
echo "🐍 Python version: $(python --version)"

echo "🔧 Step 1: Running Django migrations..."
python manage.py migrate
echo "✅ Step 1 completed: Migrations finished"

echo "🔧 Step 2: Starting Django development server..."
echo "🌐 PORT environment variable: $PORT"
echo "📡 Starting server on 0.0.0.0:$PORT"
python manage.py runserver 0.0.0.0:$PORT
echo "❌ Step 2: Server stopped unexpectedly" 