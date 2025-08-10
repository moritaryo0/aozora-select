import os
import asyncio
import threading
import requests
import tempfile
import re
from typing import Optional

from django.conf import settings

# イベントループの問題を回避するための設定
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_CALLBACKS_MANAGER"] = "disabled"

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import MultiQueryRetriever


_rag_lock = threading.Lock()
_rag_ready = False
_rag_chain = None


def _extract_google_drive_file_id(url: str) -> Optional[str]:
    """Google DriveのURLからファイルIDを抽出"""
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _download_from_google_drive(file_id: str, local_path: str) -> bool:
    """Google Driveからファイルをダウンロード"""
    try:
        print(f"📥 Google Driveからファイルをダウンロード中: {file_id}")
        
        # Google Driveの直接ダウンロードURL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # セッションを作成してCookieを管理
        session = requests.Session()
        
        # 最初のリクエストでCookieを取得
        response = session.get(download_url, stream=True)
        response.raise_for_status()
        
        # 大きなファイルの場合の確認ページを処理
        if 'confirm=' in response.url:
            confirm_token = re.search(r'confirm=([^&]+)', response.url).group(1)
            download_url = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
            response = session.get(download_url, stream=True)
            response.raise_for_status()
        
        # ディレクトリを作成
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # ファイルをダウンロード
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
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
        
        # Google DriveのURLかチェック
        if 'drive.google.com' in url:
            file_id = _extract_google_drive_file_id(url)
            if file_id:
                return _download_from_google_drive(file_id, local_path)
            else:
                print("❌ Google DriveのURLからファイルIDを抽出できませんでした")
                return False
        
        # 通常のHTTPダウンロード
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ ベクターストアのダウンロード完了: {local_path}")
        return True
    except Exception as e:
        print(f"❌ ベクターストアのダウンロードに失敗: {e}")
        return False


def _default_vector_store_path() -> str:
    # RAG_test/aozora_faiss_index をデフォルトに
    base_dir = getattr(settings, "BASE_DIR", os.getcwd())
    return os.getenv(
        "VECTOR_STORE_PATH",
        os.path.join(base_dir, "RAG_test", "aozora_faiss_index"),
    )


def _ensure_vectorstore_exists():
    """ベクターストアが存在しない場合、外部からダウンロード"""
    vector_store_path = _default_vector_store_path()
    
    if not os.path.exists(vector_store_path):
        # 外部URLからダウンロードを試行
        vectorstore_url = os.getenv("VECTORSTORE_URL")
        if vectorstore_url:
            # 一時ファイルにダウンロードしてから展開
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                if _download_vectorstore_from_url(vectorstore_url, tmp_file.name):
                    import zipfile
                    with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                        zip_ref.extractall(os.path.dirname(vector_store_path))
                    os.unlink(tmp_file.name)
                    print(f"✅ ベクターストアを展開しました: {vector_store_path}")
                else:
                    print(f"❌ ベクターストアのダウンロードに失敗しました")
        else:
            print(f"⚠️ VECTORSTORE_URLが設定されていません")


def _build_rag_chain():
    google_api_key = getattr(settings, "GOOGLE_API_KEY", None)
    if not google_api_key:
        raise RuntimeError("GOOGLE_API_KEY が設定されていません")

    # ベクターストアの存在確認とダウンロード
    _ensure_vectorstore_exists()
    
    vector_store_path = _default_vector_store_path()
    
    print(f"🔍 ベクターストアパス確認: {vector_store_path}")
    if not os.path.exists(vector_store_path):
        raise FileNotFoundError(f"ベクターストアが見つかりません: {vector_store_path}")

    # 新しいイベントループを設定（初期化時のみ）
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Embeddings と VectorStore を初期化
    print("📥 Embeddingsモデル初期化中...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=google_api_key
    )
    
    print("📂 ベクターストア読み込み中...")
    vector_store = FAISS.load_local(
        vector_store_path, embeddings, allow_dangerous_deserialization=True
    )

    base_retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 16, "score_threshold": 0.1},
    )

    print("🤖 LLMモデル初期化中...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite", 
        google_api_key=google_api_key, 
        temperature=0,
        # より安全な設定
        max_retries=1,
        timeout=60
    )

    prompt_template = (
        """
あなたは親切なアシスタントです。以下の「参考情報」を主に用いて、ユーザーの「質問」に日本語で回答してください。また、挙げる作品はできる限り小説で狂言や能は避けるようにし、1つでフォーマットは以下に準拠してください。
ただし、具体的な作者を指定されない場合、作品が誰もが読んだことのあるような作品になってしまうことを避けてください。
参考情報が不十分な場合は、検索から得られる情報でも構いませんが青空文庫の中から具体的な作品情報を回答してください。回答は簡潔に、可能なら箇条書きで示してください。最後に参考にした作品名（タイトル・作者）を列挙してください。


【参考情報】
{context}

【質問】
{question}

【回答】
"""
    )
    prompt = ChatPromptTemplate.from_template(prompt_template)

    # シンプルなRetrieverを使用（MultiQueryRetrieverは一旦無効化）
    print("🔍 Retriever設定完了")

    def format_docs(docs):
        lines = []
        for i, d in enumerate(docs, 1):
            md = getattr(d, "metadata", {}) or {}
            title = md.get("title", "不明")
            author = md.get("author", "不明")
            source = md.get("source", "")
            lines.append(
                f"[{i}] タイトル: {title}（{author}）\n出典: {source}\n本文抜粋:\n{getattr(d, 'page_content', '')}"
            )
        return "\n\n---\n\n".join(lines)

    def filter_docs(docs):
        filtered = []
        for d in docs:
            text = (getattr(d, "page_content", "") or "").strip()
            if len(text) < 60:
                continue
            if sum(ch.isdigit() for ch in text) > max(1, int(len(text) * 0.4)):
                continue
            filtered.append(d)
        return filtered or docs

    QUERY_KEYWORDS = [
        "春", "春風", "春雨", "春宵", "朧月夜", "若葉", "新緑", "花見", "桜", "梅", "菜の花", "つつじ", "藤", "うぐいす",
        "夏", "真夏", "盛夏", "夏至", "夕暮れ", "夕方", "黄昏", "夕焼け", "夕立", "納涼", "打ち水", "暑気払い",
        "蝉", "せみ", "蛍", "ほたる", "金魚", "入道雲", "朝顔", "向日葵", "ひまわり", "ラムネ", "氷水",
        "海", "渚", "砂浜", "潮風", "浜辺", "縁日", "祭", "浴衣", "団扇", "うちわ", "扇子", "花火", "盆", "盆踊り",
        "秋", "秋雨", "秋風", "野分", "夜長", "彼岸", "彼岸花", "曼珠沙華", "月", "名月", "中秋", "月見",
        "紅葉", "黄葉", "稲穂", "新米", "すすき", "虫の音", "鈴虫", "松虫", "きりぎりす", "銀杏",
        "冬", "真冬", "木枯し", "北風", "霜", "霜夜", "雪", "粉雪", "初雪", "吹雪", "氷", "凍てつく",
        "炬燵", "こたつ", "火鉢", "炭火", "囲炉裏", "みかん", "雪明り", "師走", "年の瀬",
        "雨", "小雨", "驟雨", "にわか雨", "霧", "霞", "雲", "曇", "快晴", "晴天", "雷", "稲妻", "虹",
        "風", "涼風", "寒風", "南風", "北風",
        "朝", "朝焼け", "昼", "正午", "夕", "逢魔が時", "宵", "宵闇", "夜", "真夜中", "夜明け", "暁", "明け方",
    ]

    def extract_query_terms(question: str) -> set:
        terms = set()
        if not question:
            return terms
        for w in QUERY_KEYWORDS:
            if w in question:
                terms.add(w)
        return terms

    def rerank_docs(docs, question: str, top_n: int = 10):
        docs = filter_docs(docs)
        terms = extract_query_terms(question)
        if not terms:
            return docs[:top_n]

        filtered_by_terms = []
        for d in docs:
            text = getattr(d, "page_content", "")
            md = getattr(d, "metadata", {}) or {}
            kw = md.get("keywords") or {}
            hit = any(t in text for t in terms)
            if not hit and isinstance(kw, dict):
                for arr in kw.values():
                    if any(t in arr for t in terms):
                        hit = True
                        break
            if hit:
                filtered_by_terms.append(d)
        if filtered_by_terms:
            docs = filtered_by_terms

        def score(d):
            text = getattr(d, "page_content", "")
            s = 0
            for t in terms:
                s += text.count(t) * 2
            md = getattr(d, "metadata", {}) or {}
            kw = md.get("keywords") or {}
            if isinstance(kw, dict):
                for arr in kw.values():
                    for t in terms:
                        if t in arr:
                            s += 3
            return s

        ranked = sorted(docs, key=score, reverse=True)
        return ranked[:top_n]

    print("⚙️ RAGチェーン構築中...")
    
    # シンプルなRAGチェーンを構築
    def rag_pipeline(question):
        # 基本的な検索（新しいAPIを使用）
        docs = base_retriever.invoke(question)
        # 再ランク付け
        filtered_docs = rerank_docs(docs, question)
        # フォーマット
        context = format_docs(filtered_docs)
        # プロンプト生成
        messages = prompt.format_messages(context=context, question=question)
        # LLMで回答生成（新しいAPIを使用）
        response = llm.invoke(messages)
        return response.content

    print("✅ RAGチェーン構築完了")
    return rag_pipeline


def ensure_rag_ready():
    global _rag_ready, _rag_chain
    if _rag_ready and _rag_chain is not None:
        return
    with _rag_lock:
        if not _rag_ready:
            print("🚀 RAGシステム初期化開始...")
            try:
                _rag_chain = _build_rag_chain()
                _rag_ready = True
                print("✅ RAGシステム初期化完了")
            except Exception as e:
                print(f"❌ RAGシステム初期化失敗: {e}")
                raise


def _run_with_event_loop(func, *args, **kwargs):
    """イベントループを作成してRAGチェーンを実行する"""
    try:
        # 既存のイベントループがあるかチェック
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 既存のループが実行中の場合、新しいスレッドで実行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run_in_new_thread, func, *args, **kwargs)
                return future.result()
        else:
            # ループが停止している場合、そのまま実行
            return func(*args, **kwargs)
    except RuntimeError:
        # イベントループが存在しない場合、新しく作成
        return _run_in_new_thread(func, *args, **kwargs)

def _run_in_new_thread(func, *args, **kwargs):
    """新しいスレッドでイベントループを作成して実行"""
    def run_with_new_loop():
        # 新しいイベントループを作成
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return func(*args, **kwargs)
        finally:
            new_loop.close()
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_with_new_loop)
        return future.result()

def ask(question: str) -> str:
    """RAGで質問に回答する。準備が未完なら初期化してから実行。"""
    ensure_rag_ready()
    
    try:
        # シンプルなパイプライン実行
        print(f"🔍 RAG質問処理開始: {question}")
        result = _rag_chain(question)
        print(f"✅ RAG回答生成完了: {len(result)} 文字")
        return result
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            # イベントループエラーの場合、専用処理で実行
            print(f"⚠️ イベントループエラーを検出、代替実行中: {e}")
            return _run_with_event_loop(_rag_chain, question)
        else:
            # その他のRuntimeErrorは再発生
            raise


