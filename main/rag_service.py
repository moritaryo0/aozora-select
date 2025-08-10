import os
import asyncio
import threading
from typing import Optional

from django.conf import settings

# イベントループの問題を回避するための設定
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_CALLBACKS_MANAGER"] = "disabled"

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


_rag_lock = threading.Lock()
_rag_ready = False
_rag_chain = None


def _default_vector_store_path() -> str:
    # settings.pyからベクターストアのパスを取得
    vector_store_path = getattr(settings, "VECTOR_STORE_PATH", None)
    if not vector_store_path:
        raise ValueError("VECTOR_STORE_PATHがsettings.pyで設定されていません。")
    return str(vector_store_path)


def _build_rag_chain():
    google_api_key = getattr(settings, "GOOGLE_API_KEY", None)
    if not google_api_key:
        raise RuntimeError("GOOGLE_API_KEY が設定されていません")

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
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)

    print("📂 ベクターストア読み込み中...")
    vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)

    base_retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold", search_kwargs={"k": 16, "score_threshold": 0.1}
    )

    print("🤖 LLMモデル初期化中...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=google_api_key,
        temperature=0,
        max_retries=1,
        timeout=60,
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

    print("🔍 Retriever設定完了")

    def format_docs(docs):
        lines = []
        for i, d in enumerate(docs, 1):
            md = getattr(d, "metadata", {}) or {}
            title = md.get("title", "不明")
            author = md.get("author", "不明")
            source = md.get("source", "")
            lines.append(f"[{i}] タイトル: {title}（{author}）\n出典: {source}\n本文抜粋:\n{getattr(d, 'page_content', '')}")
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
            kw = md.get("keywords", {}) or {}
            if isinstance(kw, dict):
                for arr in kw.values():
                    for t in terms:
                        if t in arr:
                            s += 3
            return s

        ranked = sorted(docs, key=score, reverse=True)
        return ranked[:top_n]

    print("⚙️ RAGチェーン構築中...")

    def rag_pipeline(question):
        docs = base_retriever.invoke(question)
        filtered_docs = rerank_docs(docs, question)
        context = format_docs(filtered_docs)
        messages = prompt.format_messages(context=context, question=question)
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
                # Google APIキーの確認
                google_api_key = getattr(settings, "GOOGLE_API_KEY", None)
                if not google_api_key or not google_api_key.strip():
                    print("⚠️ GOOGLE_API_KEYが設定されていません。RAGシステムをスキップします。")
                    _rag_chain = None
                    _rag_ready = True
                    return
                
                # Railway環境では初期化をスキップ（本番環境での重い処理を避ける）
                if os.environ.get('RAILWAY_ENVIRONMENT') and not os.environ.get('ENABLE_RAG_IN_RAILWAY'):
                    print("⚠️ Railway環境ではRAGシステム初期化をスキップします")
                    print("⚠️ 本番環境でRAGを有効にするにはENABLE_RAG_IN_RAILWAY環境変数を設定してください")
                    _rag_chain = None
                    _rag_ready = True
                    return
                
                _rag_chain = _build_rag_chain()
                _rag_ready = True
                print("✅ RAGシステム初期化完了")
            except Exception as e:
                print(f"❌ RAGシステム初期化失敗: {e}")
                # 初期化失敗時はNoneを設定して後で再試行できるようにする
                _rag_chain = None
                _rag_ready = False
                print("⚠️ RAGシステム初期化をスキップしました。後で再試行されます。")


def _run_with_event_loop(func, *args, **kwargs):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run_in_new_thread, func, *args, **kwargs)
                return future.result()
        else:
            return func(*args, **kwargs)
    except RuntimeError:
        return _run_in_new_thread(func, *args, **kwargs)


def _run_in_new_thread(func, *args, **kwargs):
    def run_with_new_loop():
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
    try:
        ensure_rag_ready()
        if _rag_chain is None:
            return "申し訳ございません。RAGシステムが初期化されていません。しばらく時間をおいてから再度お試しください。"
        
        print(f"🔍 RAG質問処理開始: {question}")
        result = _rag_chain(question)
        print(f"✅ RAG回答生成完了: {len(result)} 文字")
        return result
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            print(f"⚠️ イベントループエラーを検出、代替実行中: {e}")
            return _run_with_event_loop(_rag_chain, question)
        else:
            return f"エラーが発生しました: {str(e)}"
    except Exception as e:
        print(f"❌ RAG処理中にエラーが発生: {e}")
        return f"申し訳ございません。処理中にエラーが発生しました: {str(e)}"