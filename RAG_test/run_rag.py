

import os
import sys
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import MultiQueryRetriever

# 環境変数を読み込み
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

# --- RAGの準備 ---
VECTOR_STORE_PATH = os.getenv('VECTOR_STORE_PATH', 'aozora_faiss_index')

print("Embeddingモデルを読み込んでいます...", file=sys.stderr)
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

print(f"Vector Storeを '{VECTOR_STORE_PATH}' から読み込んでいます...", file=sys.stderr)
try:
    vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
except Exception as e:
    print(f"エラー: Vector Storeの読み込みに失敗しました。パスを確認してください: {e}", file=sys.stderr)
    sys.exit(1)

print("Retrieverを作成しています...", file=sys.stderr)
base_retriever = vector_store.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 16, "score_threshold": 0.1}
)  # リコール拡張＋しきい値緩和

print("LLMを初期化しています...", file=sys.stderr)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key, temperature=0)

# プロンプトテンプレートの定義
prompt_template = """
あなたは親切なアシスタントです。以下の「参考情報」を主に用いて、ユーザーの「質問」に日本語で回答してください。参考情報が不十分な場合は、検索から得られる情報でも構いませんが青空文庫の中から具体的な作品情報を回答してください。回答は簡潔に、可能なら箇条書きで示してください。最後に参考にした作品名（タイトル・作者）を列挙してください。

【参考情報】
{context}

【質問】
{question}

【回答】
"""
prompt = ChatPromptTemplate.from_template(prompt_template)

# MultiQueryRetriever（質問を多様化）
mq_prompt = ChatPromptTemplate.from_template(
    """
    あなたは検索クエリ拡張のアシスタントです。次のユーザー質問に対して、意味が異なるが有用な日本語クエリを10つ生成してください。
    条件:
    - 季節語・情景語・時間語（例: 夕焼け, 夕暮れ, 潮風, 蝉, 花火, 海, 渚 など）や、質問中のそれらの語をなるべく維持・活用する
    - 各行に1クエリ、番号や記号は不要

    質問: {question}
    """
)

mq_retriever = MultiQueryRetriever.from_llm(
    retriever=base_retriever,
    llm=llm,
    prompt=mq_prompt
)

# Retrieverが返すDocument配列を本文中心のテキストに整形
def format_docs(docs):
    lines = []
    for i, d in enumerate(docs, 1):
        title = d.metadata.get("title", "不明")
        author = d.metadata.get("author", "不明")
        source = d.metadata.get("source", "")
        lines.append(
            f"[{i}] タイトル: {title}（{author}）\n出典: {source}\n本文抜粋:\n{d.page_content}"
        )
    return "\n\n---\n\n".join(lines)

# RAG Chainの構築
def filter_docs(docs):
    filtered = []
    for d in docs:
        text = (d.page_content or "").strip()
        if len(text) < 60:
            continue
        if sum(ch.isdigit() for ch in text) > max(1, int(len(text) * 0.4)):
            continue
        filtered.append(d)
    return filtered or docs

# 質問から季節・情景語を抽出してスコアリング
QUERY_KEYWORDS = [
    # 春
    "春", "春風", "春雨", "春宵", "朧月夜", "若葉", "新緑", "花見", "桜", "梅", "菜の花", "つつじ", "藤", "うぐいす",
    # 夏
    "夏", "真夏", "盛夏", "夏至", "夕暮れ", "夕方", "黄昏", "夕焼け", "夕立", "納涼", "打ち水", "暑気払い",
    "蝉", "せみ", "蛍", "ほたる", "金魚", "入道雲", "朝顔", "向日葵", "ひまわり", "ラムネ", "氷水",
    "海", "渚", "砂浜", "潮風", "浜辺", "縁日", "祭", "浴衣", "団扇", "うちわ", "扇子", "花火", "盆", "盆踊り",
    # 秋
    "秋", "秋雨", "秋風", "野分", "夜長", "彼岸", "彼岸花", "曼珠沙華", "月", "名月", "中秋", "月見",
    "紅葉", "黄葉", "稲穂", "新米", "すすき", "虫の音", "鈴虫", "松虫", "きりぎりす", "銀杏",
    # 冬
    "冬", "真冬", "木枯し", "北風", "霜", "霜夜", "雪", "粉雪", "初雪", "吹雪", "氷", "凍てつく",
    "炬燵", "こたつ", "火鉢", "炭火", "囲炉裏", "みかん", "雪明り", "師走", "年の瀬",
    # 天気・時間
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
    # まず季節・情景語のヒットがあるものを優先的に残す
    filtered_by_terms = []
    for d in docs:
        text = (d.page_content or "")
        md = d.metadata or {}
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
        text = (d.page_content or "")
        s = 0
        for t in terms:
            s += text.count(t) * 2  # 本文一致を重めに
        md = d.metadata or {}
        kw = md.get("keywords") or {}
        if isinstance(kw, dict):
            for arr in kw.values():
                for t in terms:
                    if t in arr:
                        s += 3
        return s
    ranked = sorted(docs, key=score, reverse=True)
    return ranked[:top_n]

rag_chain = (
    RunnableParallel({"context": mq_retriever, "question": RunnablePassthrough()})
    | (lambda x: {"context": format_docs(rerank_docs(x["context"], x["question"])), "question": x["question"]})
    | prompt
    | llm
    | StrOutputParser()
)

print("\n--- RAGシステムの準備が完了しました ---", file=sys.stderr)

# --- コマンドラインからの実行 ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用法: python run_rag.py <質問内容>", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"質問: {question}", file=sys.stderr)
    print("回答: ", end="", file=sys.stderr)

    # ストリーミングで回答を生成し、標準出力に表示
    for chunk in rag_chain.stream(question):
        print(chunk, end="")
    print("", file=sys.stderr) # 最後の改行

