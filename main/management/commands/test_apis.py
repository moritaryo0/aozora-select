from django.core.management.base import BaseCommand
from django.conf import settings
from main.utils import get_weather_data, get_mock_weather_data
import os


class Command(BaseCommand):
    help = 'API接続をテストします'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lat',
            type=float,
            default=35.681236,
            help='緯度（デフォルト: 東京駅）'
        )
        parser.add_argument(
            '--lon', 
            type=float,
            default=139.767125,
            help='経度（デフォルト: 東京駅）'
        )

    def handle(self, *args, **options):
        lat = options['lat']
        lon = options['lon']
        
        self.stdout.write(self.style.SUCCESS('🧪 API接続テスト'))
        self.stdout.write('=' * 50)
        
        # OpenWeatherMap APIのテスト
        self.stdout.write(self.style.WARNING('🌤️ OpenWeatherMap APIテスト'))
        
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY') or getattr(settings, 'OPENWEATHERMAP_API_KEY', None)
        
        if api_key and api_key.strip():
            self.stdout.write(f"📍 位置: 緯度 {lat}, 経度 {lon}")
            self.stdout.write(f"🔑 APIキー: {api_key[:8]}...{api_key[-8:]}")
            
            try:
                weather_data = get_weather_data(lat, lon, api_key)
                if weather_data:
                    self.stdout.write(self.style.SUCCESS('✅ OpenWeatherMap API接続成功'))
                    self.stdout.write(f"📍 場所: {weather_data.get('city_name', 'N/A')}")
                    self.stdout.write(f"🌡️ 気温: {weather_data.get('temperature', 'N/A')}°C")
                    self.stdout.write(f"☁️ 天気: {weather_data.get('weather_description', 'N/A')}")
                else:
                    self.stdout.write(self.style.ERROR('❌ OpenWeatherMap API接続失敗'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ OpenWeatherMap APIエラー: {e}'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ OpenWeatherMap APIキーが設定されていません'))
            self.stdout.write('モックデータでテスト:')
            mock_data = get_mock_weather_data()
            self.stdout.write(f"📍 場所: {mock_data.get('city_name', 'N/A')}")
            self.stdout.write(f"🌡️ 気温: {mock_data.get('temperature', 'N/A')}°C")
        
        self.stdout.write('')
        
        # Google Gemini APIのテスト
        self.stdout.write(self.style.WARNING('🧠 Google Gemini APIテスト'))
        
        google_api_key = os.environ.get('GOOGLE_API_KEY') or getattr(settings, 'GOOGLE_API_KEY', None)
        
        if google_api_key and google_api_key.strip():
            self.stdout.write(f"🔑 APIキー: {google_api_key[:8]}...{google_api_key[-8:]}")
            
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash", 
                    google_api_key=google_api_key
                )
                
                # 簡単なテスト
                response = llm.invoke("こんにちは！")
                self.stdout.write(self.style.SUCCESS('✅ Google Gemini API接続成功'))
                self.stdout.write(f"🤖 レスポンス: {response.content[:100]}...")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Google Gemini APIエラー: {e}'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Google Gemini APIキーが設定されていません'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('テスト完了！')) 