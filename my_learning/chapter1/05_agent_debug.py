import os
import re
from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient


# =========================================================
# 1. 加载配置
# =========================================================

# 当前文件位于：
# hello-agents/my_learning/chapter1/04_first_agent.py
#
# parents[0] = chapter1
# parents[1] = my_learning
# parents[2] = hello-agents 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL")
MODEL_ID = os.getenv("LLM_MODEL_ID")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def check_config() -> None:
    """检查运行智能体所需的配置。"""
    missing_items = []

    if not API_KEY:
        missing_items.append("DASHSCOPE_API_KEY")

    if not BASE_URL:
        missing_items.append("LLM_BASE_URL")

    if not MODEL_ID:
        missing_items.append("LLM_MODEL_ID")

    if not TAVILY_API_KEY:
        missing_items.append("TAVILY_API_KEY")

    if missing_items:
        missing_text = ", ".join(missing_items)
        raise ValueError(
            f"缺少环境变量：{missing_text}。"
            "请检查项目根目录中的 .env 文件。"
        )


# =========================================================
# 2. 系统提示词
# =========================================================

AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。

你的任务是分析用户的请求，并使用可用工具一步步解决问题。

# 可用工具

1. get_weather(city: str)
作用：查询指定城市的当前天气。

调用示例：
get_weather(city="北京")

2. get_attraction(city: str, weather: str)
作用：根据城市和已经查询到的天气搜索合适的旅游景点。

调用示例：
get_attraction(city="北京", weather="晴，气温25摄氏度")

# 输出格式

每次回复必须只包含一对 Thought 和 Action：

Thought: 简要说明当前掌握的信息和下一步计划
Action: 要执行的行动

Action只能使用以下两种格式：

1. 调用工具：
Action: function_name(arg_name="arg_value")

2. 完成任务：
Action: Finish[最终答案]

# 规则

- 每次只能执行一个行动。
- Action必须单独占一行。
- 不得编造天气信息。
- 查询到天气后，必须调用get_attraction搜索景点。
- 获得景点搜索结果后，才能使用Finish。
- 不得重复调用已经成功执行过的相同工具。
- 最终答案必须基于Observation中的真实结果。
"""


# =========================================================
# 3. 天气工具
# =========================================================

def get_weather(city: str) -> str:
    """
    查询指定城市的当前天气。

    参数：
        city：城市名称。

    返回：
        整理后的天气文本。
    """
    city = city.strip()

    if not city:
        return "错误：城市名称不能为空。"

    url = f"https://wttr.in/{city}"

    try:
        response = requests.get(
            url,
            params={"format": "j1"},
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()
        current_condition = data["current_condition"][0]

        weather_description = current_condition["weatherDesc"][0]["value"]
        temperature = current_condition["temp_C"]
        feels_like = current_condition["FeelsLikeC"]
        humidity = current_condition["humidity"]

        return (
            f"{city}当前天气为{weather_description}，"
            f"气温{temperature}摄氏度，"
            f"体感温度{feels_like}摄氏度，"
            f"湿度{humidity}%。"
        )

    except requests.exceptions.Timeout:
        return "错误：天气服务请求超时。"

    except requests.exceptions.RequestException as error:
        return f"错误：天气服务请求失败：{error}"

    except (KeyError, IndexError, ValueError) as error:
        return f"错误：天气数据解析失败：{error}"


# =========================================================
# 4. 景点搜索工具
# =========================================================

def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，搜索合适的旅游景点。

    参数：
        city：城市名称。
        weather：天气工具返回的天气情况。

    返回：
        Tavily搜索得到的景点推荐。
    """
    city = city.strip()
    weather = weather.strip()

    if not city:
        return "错误：城市名称不能为空。"

    if not weather:
        return "错误：天气信息不能为空。"

    if not TAVILY_API_KEY:
        return "错误：没有配置TAVILY_API_KEY。"

    query = (
        f"{city}在{weather}的情况下，"
        "适合游览的旅游景点推荐及理由"
    )

    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

        response = tavily_client.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            max_results=5,
        )

        answer = response.get("answer")

        if answer:
            return answer

        results = response.get("results", [])

        if not results:
            return "没有搜索到相关景点。"

        formatted_results = []

        for index, item in enumerate(results[:3], start=1):
            title = item.get("title", "未命名景点")
            content = item.get("content", "没有相关摘要")

            formatted_results.append(
                f"{index}. {title}：{content}"
            )

        return "\n".join(formatted_results)

    except Exception as error:
        return (
            "错误：Tavily搜索失败："
            f"{type(error).__name__}: {error}"
        )


# =========================================================
# 5. 工具注册表
# =========================================================

available_tools: dict[str, Callable[..., str]] = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


# =========================================================
# 6. 大模型客户端
# =========================================================

class OpenAICompatibleClient:
    """调用兼容OpenAI接口的大模型服务。"""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
    ) -> None:
        self.model = model

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """调用大语言模型并返回模型生成的文本。"""
        print("正在调用大语言模型……")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                stream=False,
            )

            content = response.choices[0].message.content

            if not content:
                return "错误：模型没有返回文本。"

            return content.strip()

        except Exception as error:
            return (
                "错误：调用大语言模型失败："
                f"{type(error).__name__}: {error}"
            )


# =========================================================
# 7. 解析模型输出
# =========================================================

def extract_first_thought_action(llm_output: str) -> str:
    """
    从模型输出中截取第一组Thought-Action。

    某些模型可能一次输出多组Thought-Action，
    这里只保留第一组。
    """
    match = re.search(
        r"(Thought:.*?Action:.*?)(?=\n\s*"
        r"(?:Thought:|Observation:)|\Z)",
        llm_output,
        re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return llm_output.strip()


def extract_action(llm_output: str) -> str | None:
    """从模型输出中提取Action内容。"""
    action_match = re.search(
        r"^Action:\s*(.+)$",
        llm_output,
        re.MULTILINE,
    )

    if not action_match:
        return None

    return action_match.group(1).strip()


def parse_tool_call(
    action_string: str,
) -> tuple[str, dict[str, str]] | None:
    """
    解析工具调用。

    示例：
        get_weather(city="北京")

    解析结果：
        ("get_weather", {"city": "北京"})
    """
    tool_match = re.fullmatch(
        r"(\w+)\((.*)\)",
        action_string,
        re.DOTALL,
    )

    if not tool_match:
        return None

    tool_name = tool_match.group(1)
    arguments_string = tool_match.group(2)

    arguments = dict(
        re.findall(
            r'(\w+)\s*=\s*"([^"]*)"',
            arguments_string,
        )
    )

    return tool_name, arguments


def extract_final_answer(
    llm_output: str,
    action_string: str,
) -> str | None:
    """
    提取Finish中的最终答案。

    同时兼容单行和多行最终答案。
    """
    if not action_string.startswith("Finish"):
        return None

    finish_match = re.search(
        r"Action:\s*Finish\[(.*)\]\s*$",
        llm_output,
        re.DOTALL,
    )

    if not finish_match:
        return None

    return finish_match.group(1).strip()


def print_prompt_history(prompt_history: list[str]) -> None:
    """打印当前保存的完整智能体执行历史。"""
    print("\n" + "#" * 70)
    print("当前 prompt_history")
    print("#" * 70)

    for index, message in enumerate(prompt_history, start=1):
        print(f"\n[{index}]")
        print(message)

    print("\n" + "#" * 70)

# =========================================================
# 8. Agent主循环
# =========================================================

def run_agent(user_prompt: str, max_steps: int = 5) -> str:
    """
    运行Thought-Action-Observation智能体循环。
    """
    llm = OpenAICompatibleClient(
        model=MODEL_ID,
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    # 保存用户任务、模型输出和工具观察结果。
    prompt_history = [
        f"用户请求：{user_prompt}"
    ]

    print(f"\n用户输入：{user_prompt}")
    print("=" * 70)

    for step in range(1, max_steps + 1):
        print(f"\n--- 循环 {step} ---")

        # 打印当前执行历史
        print_prompt_history(prompt_history)

        # 将此前所有信息组合成当前提示。
        full_prompt = "\n".join(prompt_history)

        print("\n本轮真正发送给模型的完整提示：")
        print("-" * 70)
        print(full_prompt)
        print("+" * 70)

        # 模型进行当前轮决策。
        raw_llm_output = llm.generate(
            prompt=full_prompt,
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        print(raw_llm_output)

        # 只保留第一组Thought-Action。
        llm_output = extract_first_thought_action(
            raw_llm_output
        )

        print("\n模型输出：")
        print(llm_output)

        # 把模型输出加入历史记录。
        prompt_history.append(llm_output)

        # 提取Action。
        action_string = extract_action(llm_output)

        print("\nAction解析结果：")
        print(action_string)

        if not action_string:
            observation = (
                "错误：没有解析到Action。"
                "请严格使用Thought和Action格式。"
            )

            observation_string = (
                f"Observation: {observation}"
            )

            print(f"\n{observation_string}")
            print("=" * 70)

            prompt_history.append(observation_string)
            continue

        # 判断模型是否准备结束任务。
        if action_string.startswith("Finish"):
            final_answer = extract_final_answer(
                llm_output=llm_output,
                action_string=action_string,
            )

            if final_answer:
                print("\n任务完成。")
                print("=" * 70)
                print(final_answer)
                return final_answer

            observation = (
                "错误：Finish格式不正确。"
                "正确格式为Finish[最终答案]。"
            )

            observation_string = (
                f"Observation: {observation}"
            )

            print(f"\n{observation_string}")
            prompt_history.append(observation_string)
            continue

        # 解析普通工具调用。
        parsed_tool_call = parse_tool_call(action_string)

        if not parsed_tool_call:
            observation = (
                f"错误：无法解析工具调用："
                f"{action_string}"
            )

        else:
            tool_name, arguments = parsed_tool_call

            print("\n工具调用解析结果：")
            print(f"tool_name = {tool_name}")
            print(f"arguments = {arguments}")

            if tool_name not in available_tools:
                observation = (
                    f"错误：不存在名为"
                    f"'{tool_name}'的工具。"
                )

            else:
                tool_function = available_tools[tool_name]

                print(f"Python准备执行的函数：{tool_function.__name__}")

                try:
                    observation = tool_function(**arguments)

                except TypeError as error:
                    observation = (
                        f"错误：工具参数不正确：{error}"
                    )

                except Exception as error:
                    observation = (
                        "错误：工具执行失败："
                        f"{type(error).__name__}: {error}"
                    )

        # 把工具执行结果作为Observation返回模型。
        observation_string = (
            f"Observation: {observation}"
        )

        print(f"\n{observation_string}")
        print("=" * 70)

        prompt_history.append(observation_string)

    final_message = (
        f"任务未能在{max_steps}轮以内完成。"
    )

    print(f"\n{final_message}")
    return final_message


# =========================================================
# 9. 程序入口
# =========================================================

if __name__ == "__main__":
    check_config()

    user_input = input(
        "请输入旅行任务\n"
        "直接按回车将使用默认任务："
    ).strip()

    if not user_input:
        user_input = (
            "请查询今天北京的天气，"
            "然后根据天气推荐一个合适的旅游景点。"
        )

    run_agent(
        user_prompt=user_input,
        max_steps=5,
    )