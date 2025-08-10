from django.core.management.base import BaseCommand
from main.rag_service import ask, ensure_rag_ready


class Command(BaseCommand):
    help = 'RAGシステムをテストする管理コマンド'

    def add_arguments(self, parser):
        parser.add_argument(
            'question',
            type=str,
            help='RAGに送信する質問'
        )

    def handle(self, *args, **options):
        question = options['question']
        
        self.stdout.write(
            self.style.SUCCESS(f'🔍 RAGテスト開始: {question}')
        )
        
        try:
            # RAGシステムの初期化をテスト
            self.stdout.write('📚 RAGシステム初期化中...')
            ensure_rag_ready()
            self.stdout.write(
                self.style.SUCCESS('✅ RAGシステム初期化完了')
            )
            
            # 質問を実行
            self.stdout.write(f'🤖 RAGに質問中: {question}')
            answer = ask(question)
            
            self.stdout.write(
                self.style.SUCCESS('✅ RAG回答取得完了')
            )
            self.stdout.write(f'\n📖 回答:\n{answer}\n')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ RAGテストエラー: {e}')
            )
            import traceback
            self.stdout.write(
                self.style.ERROR(traceback.format_exc())
            )
