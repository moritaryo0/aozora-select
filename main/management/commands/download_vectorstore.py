import os
import re
import requests
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


def _download_from_google_drive(file_id: str, local_path: str) -> bool:
    """Google Driveからファイルをダウンロード（大容量確認トークンに対応）"""
    try:
        print(f"📥 Google Driveからファイルをダウンロード中: {file_id}")
        session = requests.Session()

        def _perform_download(token: Optional[str] = None):
            params = {"export": "download", "id": file_id}
            if token:
                params["confirm"] = token
            return session.get("https://drive.google.com/uc", params=params, stream=True)

        response = _perform_download()
        response.raise_for_status()

        token = None
        for k, v in response.cookies.items():
            if k.startswith("download_warning"):
                token = v
                break
        if token:
            response = _perform_download(token)
            response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type.lower():
            print("❌ 取得したコンテンツはHTMLです。共有設定やリンク形式を確認してください。")
            return False

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"✅ Google Driveからのダウンロード完了: {local_path}")
        return True
    except Exception as e:
        print(f"❌ Google Driveからのダウンロードに失敗: {e}")
        return False


def _download_vectorstore_from_url(url: str, local_path: str) -> bool:
    """外部URLからベクターストアをダウンロード"""
    try:
        print(f"📥 ベクターストアをダウンロード中: {url}")
        if "drive.google.com" in url:
            file_id = _extract_google_drive_file_id(url)
            if not file_id:
                print("❌ Google DriveのURLからファイルIDを抽出できませんでした")
                return False
            return _download_from_google_drive(file_id, local_path)

        response = requests.get(url, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        print(f"✅ ベクターストアのダウンロード完了: {local_path}")
        return True
    except Exception as e:
        print(f"❌ ベクターストアのダウンロードに失敗: {e}")
        return False

class Command(BaseCommand):
    help = 'Google Driveからベクターストア(zip)をダウンロードして展開します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存のベクターストアを上書きします'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 ベクターストアダウンロードを開始...')
        
        vector_store_path = getattr(settings, "VECTOR_STORE_PATH", None)
        if not vector_store_path:
            self.stderr.write(self.style.ERROR('VECTOR_STORE_PATHがsettings.pyで設定されていません。'))
            return

        drive_file_id = getattr(settings, "GOOGLE_DRIVE_FILE_ID", None)
        if not drive_file_id:
            self.stderr.write(self.style.ERROR('GOOGLE_DRIVE_FILE_IDがsettings.pyで設定されていません。'))
            return

        if os.path.exists(vector_store_path) and not options['force']:
            self.stdout.write(self.style.SUCCESS(f'✅ ベクターストアは既に存在します: {vector_store_path}'))
            return
        
        # 親ディレクトリを作成
        parent_dir = os.path.dirname(vector_store_path)
        os.makedirs(parent_dir, exist_ok=True)

        drive_url = f'https://drive.google.com/file/d/{drive_file_id}/view?usp=sharing'

        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                self.stdout.write(f'📥 ダウンロード中: {drive_url}')
                download_ok = _download_vectorstore_from_url(drive_url, tmp_file.name)

            if not download_ok:
                self.stderr.write(self.style.ERROR('❌ ダウンロードに失敗しました'))
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
                return

            if not zipfile.is_zipfile(tmp_file.name):
                self.stderr.write(self.style.ERROR('ダウンロードしたファイルはZIP形式ではありません。'))
                os.unlink(tmp_file.name)
                return

            self.stdout.write('📦 ファイルを展開中...')
            with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                zip_ref.extractall(parent_dir)
            
            self.stdout.write(self.style.SUCCESS(f'✅ ベクターストアのダウンロードと展開が完了しました: {parent_dir}'))
            
            files = os.listdir(parent_dir)
            self.stdout.write(f'📁 展開後のファイル一覧: {files}')

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ エラーが発生しました: {str(e)}'))
            import traceback
            self.stderr.write(traceback.format_exc())
        finally:
            if 'tmp_file' in locals() and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)