"""
統合推薦システム：天気情報とRAGを組み合わせた推薦機能
"""
import os
from datetime import datetime
from .utils import get_weather_data, get_mock_weather_data
from .rag_service import ask as rag_ask


def create_weather_rag_prompt(weather_info, location_name="現在地", exclude_text=None):
    """
    天気情報を使ってRAG検索用のプロンプトを生成
    """
    now = datetime.now()
    
    # 天気と気温に基づく読書の雰囲気を決定
    temp = weather_info.get('temperature', 20)
    weather_main = weather_info.get('weather_main', '').lower()
    weather_description = weather_info.get('weather_description', '晴れ')
    
    # 時間帯による読書雰囲気の調整
    if 6 <= now.hour < 12:
        time_mood = "朝の清々しい気分"
    elif 12 <= now.hour < 17:
        time_mood = "午後のゆったりとした時間"
    elif 17 <= now.hour < 20:
        time_mood = "夕方の落ち着いた雰囲気"
    else:
        time_mood = "夜の静寂な時間"
    
    # 天気による読書雰囲気の調整
    if 'rain' in weather_main or 'drizzle' in weather_main:
        weather_mood = "雨音に包まれて、内省的で情緒豊かな"
    elif 'clear' in weather_main:
        if temp > 25:
            weather_mood = "晴天の爽やかな気分で、明るく軽快な"
        else:
            weather_mood = "穏やかな晴天の下で、心地よい"
    elif 'cloud' in weather_main:
        weather_mood = "曇り空の落ち着いた雰囲気で、思索的な"
    elif 'snow' in weather_main:
        weather_mood = "雪景色を眺めながら、静謐で美しい"
    elif 'thunderstorm' in weather_main:
        weather_mood = "雷雨の迫力ある音に合わせて、ドラマチックな"
    else:
        weather_mood = "今の気候に心地よく寄り添う"
    
    # 気温による読書体験の調整
    if temp < 5:
        temp_mood = "寒さを忘れて心温まる"
    elif temp > 30:
        temp_mood = "暑さを忘れさせてくれる涼やかな"
    elif 20 <= temp <= 25:
        temp_mood = "快適な気温の中でじっくりと味わえる"
    else:
        temp_mood = "今の気候にぴったりの"
    
    # 月と季節感の追加
    month = now.month
    if month in [12, 1, 2]:
        season_mood = "冬の趣を感じる"
    elif month in [3, 4, 5]:
        season_mood = "春の息づかいを感じる"
    elif month in [6, 7, 8]:
        season_mood = "夏の生命力あふれる"
    else:
        season_mood = "秋の情緒深い"
    
    prompt = f"""
現在は{now.year}年{month}月{now.day}日の{now.hour}時頃で、{time_mood}の中です。
天気は{weather_description}、気温は{temp}度という環境です。

この{weather_mood}雰囲気と{temp_mood}読書体験、そして{season_mood}季節感を考慮して、
青空文庫の中から今この瞬間に読むのにぴったりな短編作品（1時間以内で読める）を1つ推薦してください。

{f"【重要】以下の作品は除外してください(空の場合は無視)：{exclude_text}" if exclude_text else ""}

条件：
- 現在の天気や季節感、時間帯にマッチする作品
- 短時間で読み切れる短編や中編
- 読後感が今の気分や環境に合う作品

以下の形式で回答してください：

-作品名-：[作品名]
-作者名-：[作者名]
-文字数-：[作品の文字数]
-作品の魅力-：[作品の特徴やあらすじを簡潔に]

-読書体験-：[簡単な選書理由とこの天気・時間帯でおすすめのシチュエーション(BGMなど)の提案]

参考にした作品名（タイトル・作者）も最後に記載してください。
"""
    
    return prompt.strip()


def get_integrated_recommendation(lat=35.681236, lon=139.767125, openweather_api_key=None, exclude_text=None):
    """
    天気情報とRAGを統合した推薦システム
    
    Args:
        lat (float): 緯度（デフォルト: 東京駅）
        lon (float): 経度（デフォルト: 東京駅）
        openweather_api_key (str): OpenWeatherMap APIキー
        exclude_text (str): 除外したい作品の情報
        
    Returns:
        dict: 統合推薦結果
    """
    
    try:
        print("🌟 統合推薦システム開始")
        
        # Google APIキーの確認
        from django.conf import settings
        google_api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        if not google_api_key or not google_api_key.strip():
            return {
                'success': False,
                'error': 'Google API key not configured',
                'recommendation': '申し訳ございません。RAGシステムが初期化されていません。しばらく時間をおいてから再度お試しください。',
                'timestamp': datetime.now().isoformat(),
                'type': 'integrated_weather_rag'
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
        
        print(f"✅ 天気情報取得完了: {weather_info['weather_description']}, {weather_info['temperature']}度")
        
        # 天気情報を基にRAG検索用プロンプトを生成
        location_name = weather_info.get('city_name', '現在地')
        rag_prompt = create_weather_rag_prompt(weather_info, location_name, exclude_text)
        
        print(f"📝 生成されたRAGプロンプト: {rag_prompt[:200]}...")
        
        # RAGシステムで推薦を取得
        print("🤖 RAG推薦実行中...")
        rag_result = rag_ask(rag_prompt)
        
        if not rag_result:
            raise Exception("RAGシステムからの応答が空です")
        
        print("✅ 統合推薦完了")
        
        return {
            'success': True,
            'recommendation': rag_result,
            'weather_info': weather_info,
            'prompt_used': rag_prompt,
            'model_used': 'gemini-2.5-flash-lite-integrated',
            'timestamp': datetime.now().isoformat(),
            'location': {
                'lat': lat,
                'lon': lon,
                'city_name': location_name
            },
            'type': 'integrated_weather_rag'
        }
        
    except Exception as e:
        print(f"❌ 統合推薦エラー: {e}")
        import traceback
        print(f"❌ エラー詳細: {traceback.format_exc()}")
        
        return {
            'success': False,
            'error': str(e),
            'recommendation': None,
            'timestamp': datetime.now().isoformat(),
            'type': 'integrated_weather_rag'
        }
