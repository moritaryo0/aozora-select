from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = '環境変数の設定状況をチェックします'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 環境変数設定チェック'))
        self.stdout.write('=' * 50)
        
        # 基本的なDjango設定
        self.check_setting('SECRET_KEY', '秘密鍵')
        self.check_setting('DEBUG', 'デバッグモード')
        self.check_setting('ALLOWED_HOSTS', '許可ホスト')
        
        self.stdout.write('')
        
        # API設定
        self.stdout.write(self.style.WARNING('📡 API設定'))
        self.check_api_key('OPENWEATHERMAP_API_KEY', 'OpenWeatherMap')
        self.check_api_key('GOOGLE_API_KEY', 'Google Gemini')
        
        self.stdout.write('')
        
        # データベース設定
        self.stdout.write(self.style.WARNING('💾 データベース設定'))
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            self.stdout.write(f"✅ DATABASE_URL: 設定済み (PostgreSQL)")
        else:
            self.stdout.write(f"📝 DATABASE_URL: 未設定 (SQLite使用)")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('チェック完了！'))
        
        # .envファイルの作成案内
        if not os.path.exists('.env'):
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('💡 .envファイルが見つかりません'))
            self.stdout.write('以下のコマンドで作成できます:')
            self.stdout.write('cp .env.example .env')
            self.stdout.write('または')
            self.stdout.write('cp .env.local .env')

    def check_setting(self, key, description):
        value = os.environ.get(key) or getattr(settings, key, None)
        if value:
            display_value = str(value)
            if key == 'SECRET_KEY':
                display_value = f"{display_value[:8]}...{display_value[-8:]}"
            self.stdout.write(f"✅ {key} ({description}): {display_value}")
        else:
            self.stdout.write(f"❌ {key} ({description}): 未設定")

    def check_api_key(self, key, service_name):
        value = os.environ.get(key) or getattr(settings, key, None)
        if value and value.strip():
            masked_value = f"{value[:8]}...{value[-8:]}" if len(value) > 16 else "設定済み"
            self.stdout.write(f"✅ {key} ({service_name}): {masked_value}")
        else:
            self.stdout.write(f"❌ {key} ({service_name}): 未設定") 