from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import AozoraBook
from .utils import (
    update_book_rankings, get_book_text, clean_aozora_text, POPULAR_BOOKS,
    get_weather_data, get_weather_icon_emoji, get_weather_recommendation, get_mock_weather_data,
    recommend_books_by_weather_and_time, get_simple_weather_recommendation
)
from django.views.decorators.http import require_http_methods

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return JsonResponse({'status': 'ok', 'message': 'API is working'})

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
    - use_ai: trueの場合LangChain版、falseの場合シンプル版 (デフォルト: false)
    - model_type: AI版使用時のGeminiモデル ("flash"または"pro"、デフォルト: "flash")
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
        
        if use_ai:
            # LangChain版推薦を使用
            print("🧠 LangChain版推薦システムを使用")
            
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
        
        else:
            # シンプル版推薦を使用
            print("📝 シンプル版推薦システムを使用")
            
            result = get_simple_weather_recommendation(
                lat=lat,
                lon=lon,
                openweather_api_key=openweather_api_key
            )
            
            if result['success']:
                print("✅ シンプル推薦完了")
                return JsonResponse({
                    'success': True,
                    'type': 'simple_recommendation',
                    'recommended_mood': result['recommended_mood'],
                    'suggested_authors': result['suggested_authors'],
                    'weather_message': result['weather_message'],
                    'weather_info': result['weather_info'],
                    'model_used': 'simple_algorithm',
                    'timestamp': result['timestamp']
                })
            else:
                print(f"❌ シンプル推薦エラー: {result['error']}")
                return JsonResponse({
                    'success': False,
                    'error': result['error'],
                    'message': '推薦システムでエラーが発生しました'
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
