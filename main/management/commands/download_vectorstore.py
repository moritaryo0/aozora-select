import os
import re
import gdown
import tempfile
import zipfile
from typing import Optional

from django.core.management.base import BaseCommand
from django.conf import settings

def _extract_google_drive_file_id(url: str) -> Optional[str]:
    """Google DriveのURLからファイルIDを抽出"""
    patterns = [
        r"/file/d/([a-zA-Z0-9-_]+)",
        r"/d/([a-zA-Z0-9-_]+)",
        r"id=([a-zA-Z0-9-_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

class Command(BaseCommand):
    help = 'Google Driveからベクターストア(zip)をダウンロードして展開します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存のベクターストアを上書きします'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 gdownを使用してベクターストアダウンロードを開始...')
        
        vector_store_path = getattr(settings, "VECTOR_STORE_PATH", None)
        if not vector_store_path:
            self.stderr.write(self.style.ERROR('VECTOR_STORE_PATHがsettings.pyで設定されていません。'))
            return

        id_or_url = getattr(settings, "GOOGLE_DRIVE_FILE_ID", None)
        if not id_or_url:
            self.stderr.write(self.style.ERROR('GOOGLE_DRIVE_FILE_IDがsettings.pyで設定されていません。'))
            return

        if os.path.exists(vector_store_path) and not options['force']:
            self.stdout.write(self.style.SUCCESS(f'✅ ベクターストアは既に存在します: {vector_store_path}'))
            return
        
        # ファイルIDを抽出
        file_id = _extract_google_drive_file_id(id_or_url) if "drive.google.com" in id_or_url else id_or_url
        if not file_id:
            self.stderr.write(self.style.ERROR(f'URLからGoogle DriveのファイルIDを抽出できませんでした: {id_or_url}'))
            return

        parent_dir = os.path.dirname(vector_store_path)
        os.makedirs(parent_dir, exist_ok=True)

        tmp_zip_path = None
        try:
            # gdownでzipファイルをダウンロード
            self.stdout.write(f'📥 gdownでダウンロード中: {file_id}')
            tmp_zip_path = gdown.download(id=file_id, quiet=False, fuzzy=True)
            
            if tmp_zip_path is None:
                self.stderr.write(self.style.ERROR('❌ gdownでのダウンロードに失敗しました。'))
                return

            if not zipfile.is_zipfile(tmp_zip_path):
                self.stderr.write(self.style.ERROR('ダウンロードしたファイルはZIP形式ではありません。'))
                return

            # zipファイルを展開
            self.stdout.write(f'📦 {tmp_zip_path} を展開中...')
            with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(parent_dir)
            
            self.stdout.write(self.style.SUCCESS(f'✅ ベクターストアのダウンロードと展開が完了しました: {parent_dir}'))
            
            files = os.listdir(parent_dir)
            self.stdout.write(f'📁 展開後のファイル一覧: {files}')

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ エラーが発生しました: {str(e)}'))
            import traceback
            self.stderr.write(traceback.format_exc())
        finally:
            # 一時ファイルを削除
            if tmp_zip_path and os.path.exists(tmp_zip_path):
                os.unlink(tmp_zip_path)
                self.stdout.write(f'🗑️ 一時ファイル {tmp_zip_path} を削除しました。')