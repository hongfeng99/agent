import requests

def get_weather(city:str)->str:
    """
    查询指定城市的天气

    参数：
        city:城市名称

    返回：
        格式化后的天气信息
    """
    city=city.strip()
    if not city:
        return "错误，城市名称不能为空"
    
    url=f"https://wttr.in/{city}"

    try:
        response=requests.get(
            url,
            params={"format":"j1"},
            timeout=33,
        )

        # 如果服务器返回 404、500 等错误，主动抛出异常
        response.raise_for_status()

        # 把服务器返回的 JSON 数据转换为 Python 字典
        data=response.json()

        # current_condition 是一个列表，取第一个元素表示当前天气
        current_condition=data["current_condition"][0]

        weather_desc=current_condition["weatherDesc"][0]["value"]
        temperature=current_condition["temp_C"]
        feels_like=current_condition["FeelsLikeC"]
        humidity=current_condition["humidity"]

        return(
            f"{city}当前天气：{weather_desc},"
            f"气温{temperature}`C,"
            f"体感温度{feels_like},"
            f"湿度{humidity}%"
        )
    
    except requests.exceptions.Timeout:
        return "错误：天气服务请求超时"
    
    except requests.exceptions.RequestException as error:
        return f"错误：天气服务请求失败：{error}"
    
    except (KeyError,IndexError,ValueError) as error:
        return f"错误：天气数据解析失败：{error}"
    

if __name__ == "__main__":
    city_name=input("请输入要查询的城市：")
    result=get_weather(city_name)
    print(result)



