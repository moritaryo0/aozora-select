from django.core.management.base import BaseCommand
from django.conf import settings
import os
import tempfile
import zipfile
from main.rag_service import _download_vectorstore_from_url, _default_vector_store_path


class Command(BaseCommand):
    help = 'Google Driveからベクターストアをダウンロードします'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Google Driveの共有URL'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存のベクターストアを上書きします'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 ベクターストアダウンロードを開始...')
        
        # URLの取得
        url = options['url'] or os.getenv('VECTORSTORE_URL')
        if not url:
            self.stdout.write('❌ URLが指定されていません。--urlオプションまたはVECTORSTORE_URL環境変数を設定してください。')
            return
        
        # ベクターストアのパス
        vector_store_path = _default_vector_store_path()
        
        # 既存のベクターストアが存在するかチェック
        if os.path.exists(vector_store_path) and not options['force']:
            self.stdout.write(f'✅ ベクターストアは既に存在します: {vector_store_path}')
            self.stdout.write('上書きする場合は --force オプションを使用してください。')
            return
        
        try:
            # 一時ファイルにダウンロード
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                self.stdout.write(f'📥 ダウンロード中: {url}')
                
                if _download_vectorstore_from_url(url, tmp_file.name):
                    # ZIPファイルを展開
                    self.stdout.write('📦 ファイルを展開中...')
                    with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                        zip_ref.extractall(os.path.dirname(vector_store_path))
                    
                    # 一時ファイルを削除
                    os.unlink(tmp_file.name)
                    
                    self.stdout.write(f'✅ ベクターストアのダウンロードと展開が完了しました: {vector_store_path}')
                    
                    # ファイル一覧を表示
                    if os.path.exists(vector_store_path):
                        files = os.listdir(vector_store_path)
                        self.stdout.write(f'📁 展開されたファイル: {files}')
                else:
                    self.stdout.write('❌ ダウンロードに失敗しました')
                    
        except Exception as e:
            self.stdout.write(f'❌ エラーが発生しました: {str(e)}')
            import traceback
            self.stdout.write(traceback.format_exc())


# 使用例:
# python manage.py download_vectorstore --url "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing"
# python manage.py download_vectorstore --url "https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing" --force
