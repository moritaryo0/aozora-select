import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

# LangChain関連のインポートを追加
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_community.tools import DuckDuckGoSearchRun

# 青空文庫の人気作品（定番作品）のデータ
POPULAR_BOOKS = [
    {
        'book_id': '773',
        'title': '吾輩は猫である',
        'author': '夏目漱石',
        'author_id': '000148',
        'card_url': 'https://www.aozora.gr.jp/cards/000148/card773.html',
        'description': '中学校の英語教師である珍野苦沙弥の家に飼われている猫である「吾輩」の視点から、珍野一家や、そこに集まる彼の友人や門下の書生たちの人間模様を風刺的・戯作的に描いた長編小説。',
        'access_count': 150000
    },
    {
        'book_id': '789',
        'title': 'こころ',
        'author': '夏目漱石',
        'author_id': '000148',
        'card_url': 'https://www.aozora.gr.jp/cards/000148/card789.html',
        'description': '明治時代の知識人である「先生」と、その教えを受ける「私」との交流を通じて、人間の心の奥底にひそむエゴイズムと、明治という時代に生きる人間の孤独を描いた長編小説。',
        'access_count': 140000
    },
    {
        'book_id': '16',
        'title': '羅生門',
        'author': '芥川龍之介',
        'author_id': '000879',
        'card_url': 'https://www.aozora.gr.jp/cards/000879/card16.html',
        'description': '平安時代の京都を舞台に、生活に困窮した下人が羅生門で老婆と出会い、生きるための悪へと手を染める決意をする短編小説。',
        'access_count': 130000
    },
    {
        'book_id': '127',
        'title': '蜘蛛の糸',
        'author': '芥川龍之介',
        'author_id': '000879',
        'card_url': 'https://www.aozora.gr.jp/cards/000879/card127.html',
        'description': '地獄に落ちた男が、生前に蜘蛛を助けた功徳により、極楽から垂らされた蜘蛛の糸にすがるが、他の亡者を蹴落とそうとした瞬間に糸が切れてしまう仏教説話をもとにした短編。',
        'access_count': 120000
    },
    {
        'book_id': '148',
        'title': '走れメロス',
        'author': '太宰治',
        'author_id': '000035',
        'card_url': 'https://www.aozora.gr.jp/cards/000035/card148.html',
        'description': '人間不信になった王に死刑を宣告されたメロスが、妹の結婚式に出席するため、親友のセリヌンティウスを人質に3日間の猶予を得て、約束を守るために必死に走る友情物語。',
        'access_count': 125000
    },
    {
        'book_id': '275',
        'title': '人間失格',
        'author': '太宰治',
        'author_id': '000035',
        'card_url': 'https://www.aozora.gr.jp/cards/000035/card275.html',
        'description': '「恥の多い生涯を送って来ました」という書き出しで始まる、主人公・大庭葉蔵の手記を通じて、人間社会に適応できない男の破滅的な生涯を描いた自伝的長編小説。',
        'access_count': 135000
    },
    {
        'book_id': '463',
        'title': '銀河鉄道の夜',
        'author': '宮沢賢治',
        'author_id': '000081',
        'card_url': 'https://www.aozora.gr.jp/cards/000081/card463.html',
        'description': '少年ジョバンニが、親友カムパネルラと共に銀河鉄道に乗って宇宙を旅する幻想的な物語。「ほんとうの幸い」とは何かを問いかける、宮沢賢治の代表作。',
        'access_count': 115000
    },
    {
        'book_id': '461',
        'title': '注文の多い料理店',
        'author': '宮沢賢治',
        'author_id': '000081',
        'card_url': 'https://www.aozora.gr.jp/cards/000081/card461.html',
        'description': '二人の紳士が山奥で見つけた西洋料理店「山猫軒」に入ると、次々と奇妙な注文が書かれた扉が現れる。実は…という風刺の効いた童話。',
        'access_count': 110000
    },
    {
        'book_id': '42',
        'title': '坊っちゃん',
        'author': '夏目漱石',
        'author_id': '000148',
        'card_url': 'https://www.aozora.gr.jp/cards/000148/card42.html',
        'description': '江戸っ子気質の青年教師「坊っちゃん」が、四国の中学校に赴任し、同僚教師たちの俗物根性と対決する痛快な中編小説。',
        'access_count': 125000
    },
    {
        'book_id': '1', 
        'title': '山月記',
        'author': '中島敦',
        'author_id': '000119',
        'card_url': 'https://www.aozora.gr.jp/cards/000119/card1.html',
        'description': '詩人を志した李徴が、自尊心の高さゆえに狂気に陥り、虎になってしまう中国の古典を題材にした短編小説。人間の内なる獣性と芸術家の業を描く。',
        'access_count': 118000
    }
]

def fetch_aozora_text_from_github(book_id, author_id):
    """GitHubの青空文庫テキストアーカイブからテキストデータを取得"""
    try:
        # author_idを6桁の0埋め形式に変換
        author_id_padded = f"{int(author_id):06d}"
        
        # GitHub APIを使ってファイル一覧を取得
        api_url = f"https://api.github.com/repos/aozorahack/aozorabunko_text/contents/cards/{author_id_padded}/files"
        
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            print(f"API エラー: {response.status_code}")
            return None
            
        files = response.json()
        
        # book_idに対応するディレクトリを探す
        target_dir = None
        for file_info in files:
            if file_info['type'] == 'dir' and book_id in file_info['name']:
                target_dir = file_info['name']
                break
        
        if not target_dir:
            print(f"book_id {book_id} に対応するディレクトリが見つかりません")
            return None
        
        # テキストファイルのURLを構築
        txt_url = f"https://aozorahack.org/aozorabunko_text/cards/{author_id_padded}/files/{target_dir}/{target_dir}.txt"
        
        # テキストファイルを取得
        txt_response = requests.get(txt_url, timeout=10)
        if txt_response.status_code == 200:
            # 青空文庫のテキストはShift_JISエンコーディング
            txt_response.encoding = 'shift_jis'
            return txt_response.text
        else:
            print(f"テキストファイル取得エラー: {txt_response.status_code}")
            return None
            
    except Exception as e:
        print(f"GitHub からのテキスト取得エラー: {e}")
        return None

def fetch_aozora_text_simple(book_id, author_id):
    """簡単なURL推測によるテキスト取得（フォールバック用）"""
    try:
        author_id_padded = f"{int(author_id):06d}"
        
        # よくあるパターンでURLを推測
        patterns = [
            f"{book_id}_ruby_{book_id}",
            f"{book_id}_txt_{book_id}",
            f"{book_id}_ruby",
            f"{book_id}_txt"
        ]
        
        for pattern in patterns:
            txt_url = f"https://aozorahack.org/aozorabunko_text/cards/{author_id_padded}/files/{pattern}/{pattern}.txt"
            
            response = requests.get(txt_url, timeout=5)
            if response.status_code == 200:
                response.encoding = 'shift_jis'
                return response.text
                
        print(f"全てのパターンで取得に失敗: book_id={book_id}, author_id={author_id}")
        return None
        
    except Exception as e:
        print(f"簡単な取得方法でエラー: {e}")
        return None

def get_book_text(book_data):
    """作品のテキストデータを取得（メイン関数）"""
    book_id = book_data['book_id']
    author_id = book_data['author_id']
    title = book_data['title']
    
    print(f"'{title}' のテキストを取得中...")
    
    # まずGitHub APIを使った方法を試す
    text = fetch_aozora_text_from_github(book_id, author_id)
    
    # 失敗した場合は簡単な推測方法を試す
    if not text:
        print("GitHub API方式が失敗。URL推測方式を試行中...")
        text = fetch_aozora_text_simple(book_id, author_id)
    
    if text:
        print(f"'{title}' のテキスト取得成功 ({len(text)} 文字)")
        return text
    else:
        print(f"'{title}' のテキスト取得に失敗")
        return None

def clean_aozora_text(text):
    """青空文庫テキストから不要な部分を除去"""
    if not text:
        return ""
    
    lines = text.split('\n')
    content_lines = []
    start_reading = False
    
    for line in lines:
        # 本文開始の目印
        if '-------' in line and '底本' not in line:
            start_reading = True
            continue
        
        # 底本情報が始まったら終了
        if start_reading and ('底本：' in line or '底本:' in line):
            break
            
        if start_reading:
            content_lines.append(line)
    
    return '\n'.join(content_lines).strip()

# 既存の関数を修正
def fetch_book_data(card_url):
    """
    非推奨: 直接青空文庫のHTMLをパースする方法は動作しません
    代わりに get_book_text() を使用してください
    """
    print("警告: fetch_book_data は非推奨です。get_book_text() を使用してください。")
    return None

# 残りの既存の関数...
def get_popular_books():
    """人気作品データを取得"""
    return POPULAR_BOOKS

def update_book_rankings():
    """作品のランキングを更新"""
    from .models import AozoraBook
    
    books = get_popular_books()
    
    for i, book_data in enumerate(books, 1):
        book, created = AozoraBook.objects.update_or_create(
            book_id=book_data['book_id'],
            defaults={
                'title': book_data['title'],
                'author': book_data['author'],
                'author_id': book_data['author_id'],
                'card_url': book_data['card_url'],
                'description': book_data.get('description', ''),
                'access_count': book_data.get('access_count', 0),
                'ranking': i
            }
        )
        
        if created:
            print(f'新規作成: {book.title}')
        else:
            print(f'更新: {book.title}')

# 使用例とテスト用関数
def test_github_fetch():
    """GitHub からのテキスト取得をテスト"""
    # 羅生門で試してみる
    test_book = {
        'book_id': '16',
        'title': '羅生門',
        'author': '芥川龍之介',
        'author_id': '000879'
    }
    
    text = get_book_text(test_book)
    if text:
        cleaned_text = clean_aozora_text(text)
        print(f"\n=== {test_book['title']} ===")
        print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
    
    return text 

# 天気情報取得関連の関数
def get_weather_data(lat, lon, api_key):
    """OpenWeatherMap APIから天気情報を取得"""
    try:
        print(f"🌐 OpenWeatherMap API呼び出し開始")
        print(f"📍 座標: lat={lat}, lon={lon}")
        print(f"🔑 APIキー: {api_key[:8]}...{api_key[-8:] if len(api_key) > 16 else '短いキー'}")
        
        # 現在の天気情報を取得
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ja"
        print(f"🌐 リクエストURL: {url}")
        
        response = requests.get(url, timeout=10)
        
        print(f"📡 APIレスポンス: {response.status_code}")
        print(f"📊 レスポンスヘッダー: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ APIレスポンスデータ: {data}")
            
            weather_info = {
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'weather_main': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'wind_speed': data.get('wind', {}).get('speed', 0),
                'clouds': data.get('clouds', {}).get('all', 0),
                'city_name': data.get('name', '現在地'),
                'country': data.get('sys', {}).get('country', ''),
                'sunrise': data.get('sys', {}).get('sunrise'),
                'sunset': data.get('sys', {}).get('sunset'),
                'timezone': data.get('timezone', 0)
            }
            
            print(f"✅ 処理済み天気情報: {weather_info}")
            return weather_info
        else:
            print(f"❌ 天気API エラー: {response.status_code}")
            print(f"❌ エラー内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 天気情報取得エラー: {e}")
        import traceback
        print(f"❌ エラー詳細: {traceback.format_exc()}")
        return None

def get_weather_icon_emoji(icon_code):
    """OpenWeatherMapのアイコンコードから対応する絵文字を取得"""
    icon_map = {
        '01d': '☀️',    # clear sky day
        '01n': '🌙',    # clear sky night
        '02d': '⛅',    # few clouds day
        '02n': '☁️',    # few clouds night
        '03d': '☁️',    # scattered clouds
        '03n': '☁️',    # scattered clouds
        '04d': '☁️',    # broken clouds
        '04n': '☁️',    # broken clouds
        '09d': '🌧️',   # shower rain
        '09n': '🌧️',   # shower rain
        '10d': '🌦️',   # rain day
        '10n': '🌧️',   # rain night
        '11d': '⛈️',   # thunderstorm
        '11n': '⛈️',   # thunderstorm
        '13d': '❄️',    # snow
        '13n': '❄️',    # snow
        '50d': '🌫️',   # mist
        '50n': '🌫️',   # mist
    }
    return icon_map.get(icon_code, '🌤️')

def get_weather_recommendation(weather_data):
    """天気情報に基づいた読書推薦メッセージを生成"""
    if not weather_data:
        return "今日もあなたにぴったりの作品をお届けします"
    
    temp = weather_data.get('temperature', 20)
    weather_main = weather_data.get('weather_main', '').lower()
    description = weather_data.get('weather_description', '')
    
    recommendations = []
    
    # 温度に基づく推薦
    if temp < 5:
        recommendations.append("寒い日には心温まる物語で暖を取りませんか？")
    elif temp > 30:
        recommendations.append("暑い日にはすっきりとした短編がおすすめです")
    elif 20 <= temp <= 25:
        recommendations.append("過ごしやすい気候での読書は格別ですね")
    
    # 天気に基づく推薦
    if 'rain' in weather_main or 'drizzle' in weather_main:
        recommendations.append("雨音と共に、情緒豊かな作品はいかがでしょう")
    elif 'clear' in weather_main:
        recommendations.append("晴れやかな気分で、明るい物語を楽しみましょう")
    elif 'cloud' in weather_main:
        recommendations.append("曇り空には、思索的な作品がよく似合います")
    elif 'snow' in weather_main:
        recommendations.append("雪景色を眺めながら、冬の情景を描いた作品を")
    elif 'thunderstorm' in weather_main:
        recommendations.append("嵐の夜には、ドラマチックな物語で心を躍らせて")
    
    if recommendations:
        return recommendations[0]
    else:
        return f"{weather_data.get('city_name', '現在地')}の{description}。素敵な読書時間をお過ごしください"

def get_mock_weather_data():
    """APIキーが設定されていない場合のモック天気データ"""
    return {
        'temperature': 22,
        'feels_like': 24,
        'humidity': 65,
        'pressure': 1013,
        'weather_main': 'Clear',
        'weather_description': '快晴',
        'weather_icon': '01d',
        'wind_speed': 2.5,
        'clouds': 10,
        'city_name': '東京',
        'country': 'JP',
        'sunrise': None,
        'sunset': None,
        'timezone': 32400  # JST
    }

def recommend_books_by_weather_and_time(lat=35.681236, lon=139.767125, google_api_key=None, openweather_api_key=None, model_type="flash"):
    """
    天気情報と現在時刻に基づいて青空文庫から短編作品を推薦
    
    Args:
        lat (float): 緯度（デフォルト: 東京駅）
        lon (float): 経度（デフォルト: 東京駅）
        google_api_key (str): Google Generative AI APIキー
        openweather_api_key (str): OpenWeatherMap APIキー
        model_type (str): 使用するGeminiモデル（"flash"または"pro"、デフォルト: "flash"）
        
    Returns:
        dict: 推薦結果と詳細情報
    """
    
    try:
        print("📚 青空文庫作品推薦システム開始")
        
        # APIキーの確認
        if not google_api_key:
            return {
                'success': False,
                'error': 'Google APIキーが設定されていません',
                'recommendation': None
            }
        
        # 天気情報を取得
        weather_info = None
        if openweather_api_key:
            print("🌤️ 天気情報を取得中...")
            weather_info = get_weather_data(lat, lon, openweather_api_key)
        
        # APIキーがない場合はモックデータを使用
        if not weather_info:
            print("⚠️ 天気情報の取得に失敗。モックデータを使用します。")
            weather_info = get_mock_weather_data()
        
        # 現在の日時を取得
        now = datetime.now()
        
        # プロンプトを生成
        prompt_template = """
現在は{year}年の{month}月{day}日の{hour}時です。{city_name}の天気は、{weather_description}、気温は{temperature}度です。
この気象情報と現在の一般的なニュースや話題を考慮して、今日という日にぴったりのオススメの作品を青空文庫の中から一時間以内でサクッと読めるくらいの短編を検索して選書してください。
みんなが一度は読んだことがあるほどのメジャーな作品は除いてみてください。回答は日本語でお願いします。ユーザのプライバシーに配慮して回答には現在地に関する言及は控えてください。

推薦理由も含めて、以下の形式で回答してください：
- 作品名：
- 作者名：
--作品リンク:
https://www.google.com/search?q=青空文庫+[作品名]
- 推薦理由：
- あらすじ：
"""
        
        prompt = prompt_template.format(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            city_name=weather_info.get('city_name', '現在地'),
            weather_description=weather_info['weather_description'],
            temperature=weather_info['temperature']
        )
        
        print(f"🤖 LangChainエージェント準備中...")
        
        # Geminiモデルを選択
        if model_type.lower() == "pro":
            model_name = "gemini-2.5-pro"
        elif model_type.lower() == "flash-lite":
            model_name = "gemini-2.5-flash-lite"
        else:
            model_name = "gemini-2.5-flash"
            
        print(f"🎯 使用モデル: {model_name}")
        
        # LangChainエージェントの準備
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_api_key)
        search = DuckDuckGoSearchRun()
        tools = [search]
        react_prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm, tools, react_prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
        
        print(f"🔍 作品推薦実行中...")
        print(f"📝 生成されたプロンプト: {prompt[:200]}...")
        
        # エージェントの実行
        try:
            result = agent_executor.invoke({"input": prompt})
        except google.api_core.exceptions.ResourceExhausted as e:
            print(f"❌ Gemini API レート制限エラー: {e}")
            return {
                'success': False,
                'error': 'Gemini API rate limit exceeded',
                'recommendation': None,
                'message': '現在、Gemini APIの利用が集中しているため、一時的に推薦ができません。しばらく時間をおいてから再度お試しください。',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ LangChainエージェント実行エラー: {e}")
            import traceback
            print(f"❌ エラー詳細: {traceback.format_exc()}")
            raise e
        
        print(f"✅ 推薦完了")
        
        return {
            'success': True,
            'recommendation': result['output'],
            'weather_info': weather_info,
            'prompt_used': prompt,
            'model_used': model_name,
            'timestamp': now.isoformat(),
            'location': {
                'lat': lat,
                'lon': lon,
                'city_name': weather_info.get('city_name', '現在地')
            }
        }
        
    except Exception as e:
        print(f"❌ 作品推薦エラー: {e}")
        import traceback
        print(f"❌ エラー詳細: {traceback.format_exc()}")
        
        return {
            'success': False,
            'error': str(e),
            'recommendation': None,
            'timestamp': datetime.now().isoformat()
        }

def get_simple_weather_recommendation(lat=35.681236, lon=139.767125, openweather_api_key=None):
    """
    シンプルな天気ベースの作品推薦（LangChain不使用版）
    
    Args:
        lat (float): 緯度
        lon (float): 経度  
        openweather_api_key (str): OpenWeatherMap APIキー
        
    Returns:
        dict: 簡単な推薦情報
    """
    
    try:
        # 天気情報を取得
        weather_info = None
        if openweather_api_key:
            weather_info = get_weather_data(lat, lon, openweather_api_key)
        
        if not weather_info:
            weather_info = get_mock_weather_data()
        
        # 天気に基づいた簡単な推薦
        weather_main = weather_info.get('weather_main', '').lower()
        temp = weather_info.get('temperature', 20)
        
        # 天気・気温に基づいた作品カテゴリの選定
        if 'rain' in weather_main:
            recommended_mood = "雨の日にぴったりな情緒的な作品"
            suggested_works = ["樋口一葉", "泉鏡花", "森鴎外"]
        elif 'clear' in weather_main and temp > 25:
            recommended_mood = "晴天の暑い日におすすめの爽やかな作品"
            suggested_works = ["宮沢賢治", "新美南吉", "小川未明"]
        elif 'cloud' in weather_main:
            recommended_mood = "曇り空に合う思索的な作品"
            suggested_works = ["内田百閒", "久保田万太郎", "岡本綺堂"]
        elif temp < 10:
            recommended_mood = "寒い日に心温まる作品"
            suggested_works = ["小泉八雲", "徳田秋声", "田山花袋"]
        else:
            recommended_mood = "今日の気候にぴったりの作品"
            suggested_works = ["坂口安吾", "織田作之助", "檀一雄"]
        
        return {
            'success': True,
            'weather_info': weather_info,
            'recommended_mood': recommended_mood,
            'suggested_authors': suggested_works,
            'weather_message': get_weather_recommendation(weather_info),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        } 