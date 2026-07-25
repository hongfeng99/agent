import json
from typing import Any

from pydantic import ValidationError

from chapter14.backend.models import ResearchTask


def extract_json_array(response_text: str) -> list[Any]:
    """
    从大模型返回的文本中提取第一个合法的 JSON 数组。

    支持以下格式：

    1. 纯 JSON 数组；
    2. Markdown JSON 代码块；
    3. JSON 数组前后带有普通说明文字。

    参数：
        response_text:
            大模型返回的原始文本。

    返回：
        解析后的 Python 列表。

    异常：
        ValueError:
            文本为空，或者没有找到合法 JSON 数组。
    """

    if not isinstance(response_text, str):
        raise TypeError(
            "response_text 必须是字符串，"
            f"实际类型为：{type(response_text).__name__}"
        )

    response_text = response_text.strip()

    if not response_text:
        raise ValueError("模型返回内容为空。")

    # 第一种情况：
    # 整段文本本身就是合法 JSON。
    try:
        result = json.loads(response_text)

        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 第二种情况：
    # JSON 数组前后存在 Markdown 或普通说明文字。
    #
    # JSONDecoder.raw_decode 可以从指定位置开始解析 JSON，
    # 因此我们依次寻找文本中的 "["。
    decoder = json.JSONDecoder()

    for index, character in enumerate(response_text):
        if character != "[":
            continue

        try:
            result, _ = decoder.raw_decode(
                response_text[index:]
            )
        except json.JSONDecodeError:
            continue

        if isinstance(result, list):
            return result

    raise ValueError(
        "没有从模型返回内容中找到合法的 JSON 数组。"
    )


def parse_research_tasks(
    response_text: str,
) -> list[ResearchTask]:
    """
    将大模型返回的 JSON 研究计划转换为 ResearchTask 列表。

    模型只需要返回：

    [
        {
            "title": "...",
            "intent": "...",
            "query": "..."
        }
    ]

    id 和默认状态由程序自动补充。
    """

    raw_tasks = extract_json_array(response_text)

    if not raw_tasks:
        raise ValueError("研究计划中没有任何子任务。")

    tasks: list[ResearchTask] = []

    for index, raw_task in enumerate(
        raw_tasks,
        start=1,
    ):
        if not isinstance(raw_task, dict):
            raise ValueError(
                f"第 {index} 个研究子任务必须是 JSON 对象，"
                f"实际类型为：{type(raw_task).__name__}"
            )

        try:
            task = ResearchTask(
                id=index,
                title=raw_task.get("title", ""),
                intent=raw_task.get("intent", ""),
                query=raw_task.get("query", ""),
            )
        except ValidationError as exc:
            raise ValueError(
                f"第 {index} 个研究子任务格式不正确："
                f"{raw_task}"
            ) from exc

        tasks.append(task)

    return tasks