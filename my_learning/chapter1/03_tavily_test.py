import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

PROJECT_ROOT=Path(__file__).resolve().parents[2]
ENV_PATH=PROJECT_ROOT/".env"

load_dotenv(ENV_PATH)

def get_attraction(city:str,weather:str)->str:
    """
    根据城市和天气，使用 Tavily 搜索合适的旅游景点。

    参数：
        city: 城市名称，例如“北京”
        weather: 天气状况，例如“晴天，气温25℃”

    返回：
        搜索得到的景点推荐文本
    """
    city=city.strip()
    weather=weather.strip()

    if not city:
        return "错误：城市名称不能为空。"

    if not weather:
        return "错误：天气信息不能为空。"
    
    api_key=os.getenv("TAVILY_API_KEY")

    if not api_key:
        return "错误：没有读取到 TAVILY_API_KEY，请检查项目根目录的 .env 文件。"
    
    tavily_client=TavilyClient(api_key=api_key)

    query=(
        f"{city}在{weather}天气下适合旅游的景点"
        "请推荐三个景点，并说明推荐理由"
    )

    try:
        response=tavily_client.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            max_results=5,
        )

        answer=response.get("answer")

        if answer:
            return answer
        
        results =response.get("results",[])

        if not results:
            return "没有搜索到合适的景点信息"
        
        formatted_results=[]
        for index,item in enumerate(results[:3],start=1):
            title = item.get("title", "未命名结果")
            content = item.get("content", "没有摘要")
            url = item.get("url", "没有链接")

            formatted_results.append(
                f"{index}. {title}\n"
                f"摘要：{content}\n"
                f"来源：{url}"
            )

        return "\n\n".join(formatted_results)

    
    except Exception as error:
        return (
            "Tavily 搜索失败："
            f"{type(error).__name__}: {error}"
        )
    
if __name__=="__main__":
    city_name=input("请输入城市：").strip()
    weather_info=input("请输入天气情况：").strip()

    print("\n正在搜索合适的旅游景点.....")

    result  =get_attraction(
        city=city_name,
        weather=weather_info,
    )


    print("\n搜索结果：")
    print("-" * 60)
    print(result)
    print("-" * 60)