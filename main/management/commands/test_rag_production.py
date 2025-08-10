from django.core.management.base import BaseCommand
from django.conf import settings
import os
from main.rag_service import ask, ensure_rag_ready


class Command(BaseCommand):
    help = '本番環境でRAG機能をテストします'

    def add_arguments(self, parser):
        parser.add_argument(
            '--question',
            type=str,
            default='夏の夕暮れについて教えてください',
            help='テスト用の質問'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 RAG機能の本番環境テストを開始...')
        
        # 環境変数の確認
        self.stdout.write(f'📍 BASE_DIR: {settings.BASE_DIR}')
        self.stdout.write(f'📍 VECTOR_STORE_PATH: {os.getenv("VECTOR_STORE_PATH", "未設定")}')
        self.stdout.write(f'📍 GOOGLE_API_KEY: {"設定済み" if os.getenv("GOOGLE_API_KEY") else "未設定"}')
        
        # ベクターストアの存在確認
        vector_store_path = os.getenv('VECTOR_STORE_PATH', os.path.join(settings.BASE_DIR, 'RAG_test', 'aozora_faiss_index'))
        if os.path.exists(vector_store_path):
            self.stdout.write(f'✅ ベクターストアが見つかりました: {vector_store_path}')
            files = os.listdir(vector_store_path)
            self.stdout.write(f'📁 ファイル一覧: {files}')
        else:
            self.stdout.write(f'❌ ベクターストアが見つかりません: {vector_store_path}')
            return
        
        try:
            # RAG機能の初期化
            self.stdout.write('🤖 RAG機能を初期化中...')
            ensure_rag_ready()
            self.stdout.write('✅ RAG機能の初期化が完了しました')
            
            # テスト質問
            question = options['question']
            self.stdout.write(f'❓ テスト質問: {question}')
            
            # RAGで回答を取得
            self.stdout.write('🔍 回答を生成中...')
            answer = ask(question)
            
            self.stdout.write('✅ 回答が生成されました:')
            self.stdout.write('=' * 50)
            self.stdout.write(answer)
            self.stdout.write('=' * 50)
            
        except Exception as e:
            self.stdout.write(f'❌ エラーが発生しました: {str(e)}')
            import traceback
            self.stdout.write(traceback.format_exc())
