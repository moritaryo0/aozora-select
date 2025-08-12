import os
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.http import require_http_methods
import os
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import AozoraBook
from .utils import (
    update_book_rankings, get_book_text, clean_aozora_text, POPULAR_BOOKS,
    get_weather_data, get_weather_icon_emoji, get_weather_recommendation, get_mock_weather_data,
    recommend_books_by_weather_and_time, get_simple_weather_recommendation
)
from django.views.decorators.http import require_http_methods
from .rag_service import ask as rag_ask
from .integrated_recommendation import get_integrated_recommendation
from . import rag_service

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """ヘルスチェックエンドポイント"""
    try:
        # 基本的なアプリケーション状態を確認
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'ok', 
            'message': 'API is working',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def rag_status(request):
    """RAGの有効化状況と前提条件を返す簡易ステータスAPI"""
    try:
        railway = bool(os.environ.get('RAILWAY_ENVIRONMENT'))
        enabled_flag = bool(os.environ.get('ENABLE_RAG_IN_RAILWAY'))
        google_key_set = bool(getattr(settings, 'GOOGLE_API_KEY', '') or os.environ.get('GOOGLE_API_KEY', ''))
        try:
            vs = rag_service._vectorstore_status()
        except Exception as e:
            vs = {'error': str(e)}

        status = {
            'railway': railway,
            'enabled_flag': enabled_flag,
            'google_api_key_set': google_key_set,
            'vector_store': vs,
        }

        problems = []
        if railway and not enabled_flag:
            problems.append('ENABLE_RAG_IN_RAILWAY を true に設定してください')
        if not google_key_set:
            problems.append('GOOGLE_API_KEY を設定してください')
        if isinstance(vs, dict) and not vs.get('exists', False):
            problems.append('VECTOR_STORE_PATH にベクトルストアが存在しません')

        status['problems'] = problems
        status['ok'] = len(problems) == 0
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def welcome_page(request):
    """青空セレクトのウェルカムページ（天気情報付き）"""
    weather_data = None
    weather_emoji = '🌤️'
    weather_recommendation = "今日もあなたにぴったりの作品をお届けします"
    
    # クエリパラメータから緯度経度を取得（フロントエンドから送信される）
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)
            
            # OpenWeatherMap APIキーの確認
            api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
            
            if api_key and api_key.strip():
                # 実際のAPIから天気情報を取得
                weather_data = get_weather_data(lat, lon, api_key)
            else:
                # APIキーが設定されていない場合はモックデータを使用
                weather_data = get_mock_weather_data()
                
            if weather_data:
                weather_emoji = get_weather_icon_emoji(weather_data.get('weather_icon', '01d'))
                weather_recommendation = get_weather_recommendation(weather_data)
                
        except (ValueError, Exception) as e:
            print(f"天気情報取得エラー: {e}")
            # エラーの場合はモックデータを使用
            weather_data = get_mock_weather_data()
            weather_emoji = get_weather_icon_emoji(weather_data.get('weather_icon', '01d'))
            weather_recommendation = get_weather_recommendation(weather_data)
    
    context = {
        'weather_data': weather_data,
        'weather_emoji': weather_emoji,
        'weather_recommendation': weather_recommendation,
    }
    
    return render(request, 'main/welcome.html', context)

def login_test_page(request):
    """ログイン機能をテストするためのWebページ"""
    return render(request, 'main/login_test.html')

def api_test_page(request):
    """API機能をテストするためのWebページ"""
    return render(request, 'main/api_test.html')

@api_view(['GET'])
@permission_classes([AllowAny])
def popular_books_api(request):
    """人気作品のAPIエンドポイント"""
    # データベースに作品がない場合は初期データを投入
    if not AozoraBook.objects.exists():
        update_book_rankings()
    
    # 上位10作品を取得
    books = AozoraBook.objects.all()[:10]
    
    data = {
        'books': [
            {
                'id': book.book_id,
                'title': book.title,
                'author': book.author,
                'author_id': book.author_id,
                'description': book.description,
                'card_url': book.card_url,
                'access_count': book.access_count,
                'ranking': book.ranking
            }
            for book in books
        ]
    }
    
    return JsonResponse(data)

def popular_books_view(request):
    """人気作品ページのビュー"""
    # データベースに作品がない場合は初期データを投入
    if not AozoraBook.objects.exists():
        update_book_rankings()
    
    books = AozoraBook.objects.all()[:10]
    context = {
        'books': books,
        'title': '青空文庫 人気作品'
    }
    return render(request, 'main/popular_books.html', context)

@api_view(['GET'])
@permission_classes([AllowAny])
def weather_api(request):
    """天気情報取得APIエンドポイント"""
    print(f"🌤️ 天気API リクエスト受信 - IP: {request.META.get('REMOTE_ADDR')}")
    print(f"📊 GETパラメータ: {dict(request.GET)}")
    
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    print(f"📍 受信した座標: lat={lat}, lon={lon}")
    
    if not lat or not lon:
        print("❌ 緯度または経度が不足しています")
        return JsonResponse({
            'error': 'latitude and longitude are required',
            'message': '緯度と経度が必要です'
        }, status=400)
    
    try:
        lat = float(lat)
        lon = float(lon)
        print(f"✅ 座標変換成功: 緯度={lat}, 経度={lon}")
        
        # OpenWeatherMap APIキーの確認
        api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
        print(f"🔑 APIキー確認: {'設定済み' if api_key and api_key.strip() else 'モックデータ使用'}")
        
        if api_key and api_key.strip():
            print("🌐 OpenWeatherMap APIから実際の天気データを取得中...")
            # 実際のAPIから天気情報を取得
            weather_data = get_weather_data(lat, lon, api_key)
        else:
            print("🔄 モックデータを使用します")
            # APIキーが設定されていない場合はモックデータを使用
            weather_data = get_mock_weather_data()
            
        print(f"📊 取得した天気データ: {weather_data}")
            
        if weather_data:
            weather_data['emoji'] = get_weather_icon_emoji(weather_data.get('weather_icon', '01d'))
            weather_data['recommendation'] = get_weather_recommendation(weather_data)
            
            print(f"✅ 天気データ処理完了: {weather_data}")
            
            return JsonResponse({
                'success': True,
                'weather': weather_data
            })
        else:
            print("❌ 天気データの取得に失敗しました")
            return JsonResponse({
                'error': 'Failed to fetch weather data',
                'message': '天気情報の取得に失敗しました'
            }, status=500)
            
    except (ValueError, Exception) as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        return JsonResponse({
            'error': 'Invalid coordinates or API error',
            'message': f'座標が無効か、APIエラーが発生しました: {str(e)}'
        }, status=400)


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def admin_download_vectorstore(request):
    """管理用: ベクターストアを外部URLからダウンロードして展開する
    セキュリティ: 環境変数 ADMIN_TASK_TOKEN とクエリ/ボディの token を一致させる
    使い方:
      - POST /api/admin/download-vectorstore/?token=...  または JSON {"token": "..."}
    """
    try:
        admin_token_env = os.getenv('ADMIN_TASK_TOKEN')
        token = request.GET.get('token') or getattr(request, 'data', {}).get('token') if hasattr(request, 'data') else None
        if not admin_token_env:
            return JsonResponse({'success': False, 'error': 'ADMIN_TASK_TOKEN が未設定です'}, status=400)
        if not token or token != admin_token_env:
            return JsonResponse({'success': False, 'error': '認可エラー: token が不正です'}, status=401)

        # ダウンロードと展開
        # rag_service._ensure_vectorstore_exists() は存在しない場合のみ実行する設計
        # 強制再取得したい場合は VECTORSTORE_URL を更新し、既存ディレクトリを空にする運用とする
        # 現在は存在しない場合の取得に対応
        vector_store_path = rag_service._default_vector_store_path()
        before_exists = os.path.exists(vector_store_path)
        status = rag_service._ensure_vectorstore_exists(force=request.GET.get('force') == '1')
        after_exists = os.path.exists(vector_store_path)

        files = []
        if after_exists:
            try:
                files = os.listdir(vector_store_path)
            except Exception:
                files = []

        return JsonResponse({
            'success': True,
            'vector_store_path': vector_store_path,
            'existed_before': before_exists,
            'exists_now': after_exists,
            'files': files,
            'status': status,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def rag_answer_api(request):
    """
    RAGに質問して回答を返すAPI
    Body: { "question": "..." }
    """
    try:
        data = request.data if hasattr(request, 'data') else {}
        question = (data.get('question') or '').strip()
        if not question:
            return JsonResponse({
                'success': False,
                'error': 'question is required'
            }, status=400)

        print(f"🔍 RAG質問受信: {question}")
        
        # Google APIキーの確認
        google_api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        if not google_api_key or not google_api_key.strip():
            return JsonResponse({
                'success': False,
                'error': 'Google API key not configured',
                'message': 'RAG機能を使用するにはGOOGLE_API_KEYの設定が必要です。'
            }, status=400)
        
        # Railway環境ではRAG機能を無効化（本番環境での重い処理を避ける）
        if os.environ.get('RAILWAY_ENVIRONMENT') and not os.environ.get('ENABLE_RAG_IN_RAILWAY'):
            return JsonResponse({
                'success': False,
                'error': 'RAG機能は現在利用できません',
                'message': 'Railway環境ではRAG機能が無効化されています。本番環境でRAGを有効にするにはENABLE_RAG_IN_RAILWAY環境変数を設定してください。'
            }, status=503)
        
        answer = rag_ask(question)
        print(f"✅ RAG回答完了: {len(answer)} 文字")
        
        return JsonResponse({
            'success': True,
            'question': question,
            'answer': answer
        })
        
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            print(f"❌ イベントループエラー: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Event loop error',
                'message': 'RAGシステムの初期化中です。しばらく待ってから再試行してください。'
            }, status=503)
        else:
            print(f"❌ RuntimeError: {e}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': 'Runtime error',
                'message': str(e)
            }, status=500)
            
    except ImportError as e:
        print(f"❌ インポートエラー (依存関係): {e}")
        return JsonResponse({
            'success': False,
            'error': 'Import error',
            'message': 'RAGシステムの依存関係が不足しています。faiss-cpuがインストールされているか確認してください。'
        }, status=500)
        
    except FileNotFoundError as e:
        print(f"❌ ファイル未発見エラー: {e}")
        return JsonResponse({
            'success': False,
            'error': 'File not found',
            'message': 'RAGベクターストアが見つかりません。VECTOR_STORE_PATHを確認してください。'
        }, status=500)
        
    except Exception as e:
        print(f"❌ RAG回答エラー: {e}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': 'RAG error',
            'message': str(e)
        }, status=500)
def book_preview(request, book_id):
    """本文プレビューページ"""
    # 初期データから作品を探す
    book_data = None
    for book in POPULAR_BOOKS:
        if book['book_id'] == book_id:
            book_data = book
            break
    
    if not book_data:
        context = {
            'error_message': f'作品ID {book_id} が見つかりません',
            'title': 'エラー'
        }
        return render(request, 'main/book_preview.html', context)
    
    # 本文を取得
    text_content = None
    error_message = None
    
    try:
        print(f"作品 '{book_data['title']}' のテキストを取得中...")
        raw_text = get_book_text(book_data)
        
        if raw_text:
            # 青空文庫テキストをクリーニング
            text_content = clean_aozora_text(raw_text)
            # プレビュー用に最初の2000文字に制限
            if len(text_content) > 2000:
                text_content = text_content[:2000] + "\n\n... （続きを読むには全文を取得してください）"
        else:
            error_message = "テキストの取得に失敗しました"
            
    except Exception as e:
        error_message = f"テキスト取得エラー: {str(e)}"
        print(f"エラー: {e}")
    
    context = {
        'book': book_data,
        'text_content': text_content,
        'error_message': error_message,
        'title': f'{book_data["title"]} - 本文プレビュー'
    }
    
    return render(request, 'main/book_preview.html', context)

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def recommend_books_api(request):
    """
    天気と時間に基づく青空文庫作品推薦API
    
    Parameters:
    - lat: 緯度 (オプション、デフォルト: 東京駅)
    - lon: 経度 (オプション、デフォルト: 東京駅)
    - use_ai: 現在はLangChain版のみで、他の方法なども実装の余地あり
    - model_type: AI版使用時のGeminiモデル (ベータ版ではgemini 2.5-flash-liteで固定)
    """
    print(f"📚 作品推薦API リクエスト受信 - IP: {request.META.get('REMOTE_ADDR')}")
    
    # GETとPOSTの両方に対応
    if request.method == 'POST':
        params = request.data if hasattr(request, 'data') else {}
    else:
        params = request.GET
    
    # パラメータを取得
    lat = params.get('lat', 35.681236)  # デフォルト: 東京駅
    lon = params.get('lon', 139.767125)
    use_ai = params.get('use_ai', 'false').lower() == 'true'
    model_type = params.get('model_type', 'flash')  # デフォルト: flash
    
    print(f"📍 座標: lat={lat}, lon={lon}")
    print(f"🤖 AI使用: {use_ai}")
    print(f"🎯 モデル: {model_type}")
    
    try:
        lat = float(lat)
        lon = float(lon)
        
        # APIキーを設定から取得
        openweather_api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
        google_api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        
        # LangChain版推薦を使用
        print("LangChain版推薦システムを使用")
        
        if not google_api_key or not google_api_key.strip():
            return JsonResponse({
                'success': False,
                'error': 'Google API key not configured',
                'message': 'AI推薦を使用するにはGoogle APIキーの設定が必要です。シンプル版をご利用ください。',
                'fallback_available': True
            }, status=400)
        
        result = recommend_books_by_weather_and_time(
            lat=lat,
            lon=lon,
            google_api_key=google_api_key,
            openweather_api_key=openweather_api_key,
            model_type=model_type
        )
        
        if result['success']:
            print("✅ AI推薦完了")
            return JsonResponse({
                'success': True,
                'type': 'ai_recommendation',
                'recommendation': result['recommendation'],
                'weather_info': result['weather_info'],
                'location': result['location'],
                'model_used': result.get('model_used', model_type),
                'timestamp': result['timestamp']
            })
        else:
            print(f"❌ AI推薦エラー: {result['error']}")
            return JsonResponse({
                'success': False,
                'error': result['error'],
                'message': 'AI推薦でエラーが発生しました。シンプル版をお試しください。',
                'fallback_available': True
            }, status=500)
    
    except ValueError as e:
        print(f"❌ パラメータエラー: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid parameters',
            'message': f'パラメータが無効です: {str(e)}'
        }, status=400)
    
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback
        print(f"❌ エラー詳細: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': 'Unexpected error',
            'message': f'予期しないエラーが発生しました: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def integrated_recommendation_api(request):
    """統合推薦API：天気情報とRAGを組み合わせた推薦"""
    try:
        # リクエストパラメータを取得
        lat = float(request.GET.get('lat', 35.681236))
        lon = float(request.GET.get('lon', 139.767125))
        exclude_text = request.GET.get('exclude', None)
        
        print(f"🌟 統合推薦API呼び出し: lat={lat}, lon={lon}, exclude={exclude_text}")
        
        # OpenWeatherMap APIキーを取得
        openweather_api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        
        # 統合推薦を実行
        result = get_integrated_recommendation(
            lat=lat, 
            lon=lon, 
            openweather_api_key=openweather_api_key,
            exclude_text=exclude_text
        )
        
        if result['success']:
            return Response(result)
        else:
            return Response(result, status=500)
            
    except ValueError as e:
        return Response({
            'success': False,
            'error': 'Invalid coordinates',
            'message': '座標の形式が正しくありません。'
        }, status=400)
    except Exception as e:
        print(f"❌ 統合推薦API error: {e}")
        import traceback
        print(f"❌ Error details: {traceback.format_exc()}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': '統合推薦システムでエラーが発生しました。'
        }, status=500)
