import pytest

from chapter14.backend.models import TaskStatus
from chapter14.backend.utils.json_parser import (
    extract_json_array,
    parse_research_tasks,
)


def test_extract_plain_json_array() -> None:
    """
    验证能够解析纯 JSON 数组。
    """

    response_text = """
    [
        {
            "title": "MCP 的基本概念",
            "intent": "了解 MCP",
            "query": "Model Context Protocol"
        }
    ]
    """

    result = extract_json_array(response_text)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "MCP 的基本概念"


def test_extract_json_from_markdown_code_block() -> None:
    """
    验证能够从 Markdown 代码块中提取 JSON。
    """

    response_text = """
下面是研究计划：

```json
[
    {
        "title": "MCP 的基本概念",
        "intent": "了解 MCP 的设计目标",
        "query": "Model Context Protocol architecture"
    }
]
```

以上是完整计划。
"""

    result = extract_json_array(response_text)

    assert len(result) == 1
    assert result[0]["query"] == (
        "Model Context Protocol architecture"
    )


def test_extract_json_with_surrounding_text() -> None:
    """
    验证 JSON 前后存在普通文本时仍然可以解析。
    """

    response_text = """
研究计划如下：

[
    {
        "title": "任务一",
        "intent": "研究第一个问题",
        "query": "first research query"
    },
    {
        "title": "任务二",
        "intent": "研究第二个问题",
        "query": "second research query"
    }
]

请按照以上计划执行。
"""

    result = extract_json_array(response_text)

    assert len(result) == 2
    assert result[1]["title"] == "任务二"


def test_extract_rejects_empty_text() -> None:
    """
    空字符串应该抛出异常。
    """

    with pytest.raises(
        ValueError,
        match="模型返回内容为空",
    ):
        extract_json_array("")


def test_extract_rejects_invalid_json() -> None:
    """
    不包含合法 JSON 数组时应该抛出异常。
    """

    response_text = "模型没有按照要求返回 JSON。"

    with pytest.raises(
        ValueError,
        match="没有从模型返回内容中找到",
    ):
        extract_json_array(response_text)


def test_extract_rejects_non_string() -> None:
    """
    输入不是字符串时应该抛出 TypeError。
    """

    with pytest.raises(
        TypeError,
        match="response_text 必须是字符串",
    ):
        extract_json_array(123)  # type: ignore[arg-type]


def test_parse_research_tasks() -> None:
    """
    验证能够转换成 ResearchTask 列表。
    """

    response_text = """
[
    {
        "title": "MCP 的基本概念",
        "intent": "了解 MCP 的设计目标和核心组成",
        "query": "Model Context Protocol architecture"
    },
    {
        "title": "MCP 的应用场景",
        "intent": "了解 MCP 在 Agent 中的实际应用",
        "query": "Model Context Protocol use cases"
    }
]
"""

    tasks = parse_research_tasks(response_text)

    assert len(tasks) == 2

    assert tasks[0].id == 1
    assert tasks[0].title == "MCP 的基本概念"
    assert tasks[0].status == TaskStatus.PENDING

    assert tasks[1].id == 2
    assert tasks[1].title == "MCP 的应用场景"


def test_parse_tasks_rejects_empty_array() -> None:
    """
    空任务数组应该抛出异常。
    """

    with pytest.raises(
        ValueError,
        match="研究计划中没有任何子任务",
    ):
        parse_research_tasks("[]")


def test_parse_tasks_rejects_non_object_item() -> None:
    """
    数组中的每个元素都必须是 JSON 对象。
    """

    response_text = """
[
    "这不是一个研究任务"
]
"""

    with pytest.raises(
        ValueError,
        match="必须是 JSON 对象",
    ):
        parse_research_tasks(response_text)


def test_parse_tasks_rejects_missing_query() -> None:
    """
    缺少 query 字段时应该抛出异常。
    """

    response_text = """
[
    {
        "title": "MCP 的基本概念",
        "intent": "了解 MCP"
    }
]
"""

    with pytest.raises(
        ValueError,
        match="第 1 个研究子任务格式不正确",
    ):
        parse_research_tasks(response_text)