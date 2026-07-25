from typing import Any

import pytest

from chapter14.backend.models import TaskStatus
from chapter14.backend.prompts import build_planning_prompt
from chapter14.backend.services.planning_service import (
    PlanningService,
)


class FakeLLM:
    """
    用于测试 PlanningService 的假大模型。

    FakeLLM 不会访问网络，也不会调用真实模型。
    它只会返回预先设置好的字符串，或者主动抛出异常。
    """

    def __init__(
        self,
        response_text: str = "",
        error: Exception | None = None,
    ) -> None:
        self.response_text = response_text
        self.error = error

        # 记录 PlanningService 传给模型的 messages。
        self.received_messages: list[
            dict[str, str]
        ] = []

        # 记录 invoke() 接收到的其他参数。
        self.received_kwargs: dict[str, Any] = {}

    def invoke(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        模拟 HelloAgentsLLM.invoke()。
        """

        self.received_messages = messages
        self.received_kwargs = kwargs

        if self.error is not None:
            raise self.error

        return self.response_text


def test_build_planning_prompt() -> None:
    """
    验证规划提示词中包含研究主题、任务数量和字段要求。
    """

    prompt = build_planning_prompt(
        topic="MCP 协议的价值",
        min_tasks=3,
        max_tasks=5,
    )

    assert "MCP 协议的价值" in prompt
    assert "3～5 个子任务" in prompt
    assert '"title"' in prompt
    assert '"intent"' in prompt
    assert '"query"' in prompt


def test_build_planning_prompt_rejects_empty_topic() -> None:
    """
    验证空研究主题会被拒绝。
    """

    with pytest.raises(
        ValueError,
        match="研究主题不能为空",
    ):
        build_planning_prompt("   ")


def test_build_planning_prompt_rejects_invalid_min_tasks() -> None:
    """
    验证 min_tasks 不能小于 1。
    """

    with pytest.raises(
        ValueError,
        match="min_tasks 必须大于等于 1",
    ):
        build_planning_prompt(
            topic="测试主题",
            min_tasks=0,
            max_tasks=5,
        )


def test_build_planning_prompt_rejects_invalid_max_tasks() -> None:
    """
    验证 max_tasks 不能小于 min_tasks。
    """

    with pytest.raises(
        ValueError,
        match="max_tasks 不能小于 min_tasks",
    ):
        build_planning_prompt(
            topic="测试主题",
            min_tasks=5,
            max_tasks=3,
        )


def test_planning_service_returns_tasks() -> None:
    """
    验证规划服务能够返回 ResearchTask 列表。
    """

    response_text = """
[
    {
        "title": "MCP 的基本概念",
        "intent": "了解 MCP 的设计目标和核心组成",
        "query": "Model Context Protocol architecture"
    },
    {
        "title": "MCP 的工作机制",
        "intent": "分析 MCP 客户端和服务端如何交互",
        "query": "Model Context Protocol client server workflow"
    },
    {
        "title": "MCP 的应用价值",
        "intent": "研究 MCP 在智能体项目中的实际作用",
        "query": "Model Context Protocol agent use cases"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    tasks = service.plan(
        "MCP 协议对智能体开发有什么价值？"
    )

    assert len(tasks) == 3

    assert tasks[0].id == 1
    assert tasks[0].title == "MCP 的基本概念"
    assert tasks[0].status == TaskStatus.PENDING

    assert tasks[1].id == 2
    assert tasks[1].title == "MCP 的工作机制"

    assert tasks[2].id == 3
    assert tasks[2].title == "MCP 的应用价值"

    assert len(fake_llm.received_messages) == 2

    assert (
        fake_llm.received_messages[0]["role"]
        == "system"
    )

    assert (
        fake_llm.received_messages[1]["role"]
        == "user"
    )

    assert (
        "MCP 协议对智能体开发有什么价值"
        in fake_llm.received_messages[1]["content"]
    )


def test_planning_service_supports_markdown_response() -> None:
    """
    验证模型返回 Markdown JSON 代码块时也能正常解析。
    """

    response_text = """
下面是研究计划：

```json
[
    {
        "title": "基本概念",
        "intent": "研究基本概念",
        "query": "basic concept"
    },
    {
        "title": "核心机制",
        "intent": "研究核心机制",
        "query": "core mechanism"
    },
    {
        "title": "实际应用",
        "intent": "研究实际应用",
        "query": "practical applications"
    }
]
```

以上是完整的研究计划。
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    tasks = service.plan(
        "测试研究主题"
    )

    assert len(tasks) == 3
    assert tasks[0].title == "基本概念"
    assert tasks[1].title == "核心机制"
    assert tasks[2].title == "实际应用"


def test_planning_service_rejects_too_few_tasks() -> None:
    """
    验证少于最小数量的任务会被拒绝。
    """

    response_text = """
[
    {
        "title": "任务一",
        "intent": "研究问题一",
        "query": "research query one"
    },
    {
        "title": "任务二",
        "intent": "研究问题二",
        "query": "research query two"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
        min_tasks=3,
        max_tasks=5,
    )

    with pytest.raises(
        ValueError,
        match="研究子任务数量不符合要求",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_too_many_tasks() -> None:
    """
    验证超过最大数量的任务会被拒绝。
    """

    response_text = """
[
    {
        "title": "任务一",
        "intent": "研究问题一",
        "query": "research query one"
    },
    {
        "title": "任务二",
        "intent": "研究问题二",
        "query": "research query two"
    },
    {
        "title": "任务三",
        "intent": "研究问题三",
        "query": "research query three"
    },
    {
        "title": "任务四",
        "intent": "研究问题四",
        "query": "research query four"
    },
    {
        "title": "任务五",
        "intent": "研究问题五",
        "query": "research query five"
    },
    {
        "title": "任务六",
        "intent": "研究问题六",
        "query": "research query six"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
        min_tasks=3,
        max_tasks=5,
    )

    with pytest.raises(
        ValueError,
        match="研究子任务数量不符合要求",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_duplicate_title() -> None:
    """
    验证重复的任务标题会被拒绝。
    """

    response_text = """
[
    {
        "title": "基本概念",
        "intent": "研究定义",
        "query": "concept definition"
    },
    {
        "title": "基本概念",
        "intent": "研究组成",
        "query": "concept components"
    },
    {
        "title": "实际应用",
        "intent": "研究应用",
        "query": "practical applications"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="存在重复标题",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_case_insensitive_duplicate_title() -> None:
    """
    验证标题重复检查不区分英文大小写。
    """

    response_text = """
[
    {
        "title": "MCP Architecture",
        "intent": "研究架构",
        "query": "mcp architecture"
    },
    {
        "title": "mcp architecture",
        "intent": "研究组成",
        "query": "mcp components"
    },
    {
        "title": "MCP Applications",
        "intent": "研究应用",
        "query": "mcp applications"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="存在重复标题",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_duplicate_query() -> None:
    """
    验证重复的搜索语句会被拒绝。
    """

    response_text = """
[
    {
        "title": "基本概念",
        "intent": "研究定义",
        "query": "same query"
    },
    {
        "title": "核心机制",
        "intent": "研究机制",
        "query": "same query"
    },
    {
        "title": "实际应用",
        "intent": "研究应用",
        "query": "practical applications"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="存在重复搜索语句",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_case_insensitive_duplicate_query() -> None:
    """
    验证搜索语句重复检查不区分英文大小写。
    """

    response_text = """
[
    {
        "title": "基本概念",
        "intent": "研究定义",
        "query": "MCP Architecture"
    },
    {
        "title": "核心机制",
        "intent": "研究机制",
        "query": "mcp architecture"
    },
    {
        "title": "实际应用",
        "intent": "研究应用",
        "query": "MCP applications"
    }
]
"""

    fake_llm = FakeLLM(
        response_text=response_text,
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="存在重复搜索语句",
    ):
        service.plan("测试主题")


def test_planning_service_wraps_llm_error() -> None:
    """
    验证大模型调用异常会被转换成 RuntimeError。
    """

    fake_llm = FakeLLM(
        error=ConnectionError(
            "模拟网络连接失败"
        ),
    )

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="调用研究规划模型失败",
    ):
        service.plan("测试主题")


def test_planning_service_rejects_non_string_response() -> None:
    """
    验证规划模型返回非字符串内容时会抛出 TypeError。
    """

    fake_llm = FakeLLM(
        response_text="",
    )

    # 为了模拟错误的模型返回类型，
    # 将 response_text 替换成列表。
    fake_llm.response_text = [  # type: ignore[assignment]
        {
            "title": "错误返回值",
        }
    ]

    service = PlanningService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        TypeError,
        match="规划模型应当返回字符串",
    ):
        service.plan("测试主题")