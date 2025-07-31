from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_community.tools import DuckDuckGoSearchRun
from utils import get_weather_data
import datetime

# APIキーを環境変数から取得
google_api_key = GOOGLE_API_KEY
# OpenWeatherMapのAPIキーも取得
openweather_api_key = OPENWEATHERMAP_API_KEY

# --- 天気情報を取得 ---
# 東京駅の緯度経度
tokyo_station_lat = 35.681236
tokyo_station_lon = 139.767125        
now = datetime.datetime.now()


if not openweather_api_key:
    print("❌エラー: 環境変数に OPENWEATHERMAP_API_KEY が設定されていません。")
else:
    # 天気データを取得
    weather_info = get_weather_data(tokyo_station_lat, tokyo_station_lon, openweather_api_key)

    if weather_info:
        # --- 天気情報を使ってプロンプトを作成 ---

        prompt_template = """
現在は{year}年の{month}月{day}日の{hour}時です。東京駅周辺の天気は、{weather_description}、気温は{temperature}度です。
この気象情報と現在の一般的なニュースや話題を考慮して、今日という日にぴったりのオススメの作品を青空文庫の中から一時間以内でサクッと読めるくらいの短編を検索して選書してください。
みんなが一度は読んだことがあるほどのメジャーな作品は除いでみてください。
"""
        prompt = prompt_template.format(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            weather_description=weather_info['weather_description'],
            temperature=weather_info['temperature']
        )

        # --- LangChainエージェントの準備 ---
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=google_api_key)
        search = DuckDuckGoSearchRun()
        tools = [search]
        react_prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm, tools, react_prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # --- エージェントの実行 ---
        print("\n--- エージェント実行 ---")
        print(f"プロンプト: {prompt}")
        result = agent_executor.invoke({"input": prompt})

        # --- 結果の表示 ---
        print("\n--- 最終結果 ---")
        print(result['output'])