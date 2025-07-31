from django.core.management.base import BaseCommand
from main.utils import test_github_fetch, get_book_text, clean_aozora_text, POPULAR_BOOKS

class Command(BaseCommand):
    help = 'GitHub からの青空文庫テキスト取得をテスト'

    def add_arguments(self, parser):
        parser.add_argument(
            '--book-id',
            type=str,
            help='特定の作品IDでテスト（例: 16）',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='全ての人気作品でテスト',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('青空文庫テキスト取得テストを開始します...\n')
        )

        if options['book_id']:
            # 特定の作品をテスト
            book_data = None
            for book in POPULAR_BOOKS:
                if book['book_id'] == options['book_id']:
                    book_data = book
                    break
            
            if book_data:
                self.test_single_book(book_data)
            else:
                self.stdout.write(
                    self.style.ERROR(f'作品ID {options["book_id"]} が見つかりません')
                )
                
        elif options['all']:
            # 全ての人気作品をテスト
            for book in POPULAR_BOOKS:
                self.test_single_book(book)
                self.stdout.write('-' * 50)
                
        else:
            # デフォルト：羅生門をテスト
            self.stdout.write('デフォルトテスト: 羅生門')
            test_github_fetch()

    def test_single_book(self, book_data):
        """単一の作品をテスト"""
        self.stdout.write(f"\n📖 '{book_data['title']}' ({book_data['author']}) をテスト中...")
        
        try:
            # テキストを取得
            raw_text = get_book_text(book_data)
            
            if raw_text:
                # テキストをクリーニング
                cleaned_text = clean_aozora_text(raw_text)
                
                # 結果を表示
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 取得成功: {len(raw_text)} 文字 (クリーニング後: {len(cleaned_text)} 文字)')
                )
                
                # 最初の300文字をプレビュー
                preview = cleaned_text[:300] + "..." if len(cleaned_text) > 300 else cleaned_text
                self.stdout.write(f'\n📄 プレビュー:\n{preview}\n')
                
            else:
                self.stdout.write(
                    self.style.ERROR('❌ テキストの取得に失敗')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ エラー: {str(e)}')
            ) 