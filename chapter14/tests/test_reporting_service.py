from typing import Any

import pytest

from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)
from chapter14.backend.prompts import (
    build_reporting_prompt,
)
from chapter14.backend.services.reporting_service import (
    ReportingService,
)


class FakeLLM:
    """
    用于测试 ReportingService 的假大模型。
    """

    def __init__(
        self,
        response_text: Any = "",
        error: Exception | None = None,
    ) -> None:
        self.response_text = response_text
        self.error = error

        self.received_messages: list[
            dict[str, str]
        ] = []

    def invoke(
        self,
        messages: list[dict[str, str]],
    ) -> Any:
        """
        模拟大模型调用。
        """

        self.received_messages = messages

        if self.error is not None:
            raise self.error

        return self.response_text


def create_test_summaries() -> list[TaskSummary]:
    """
    创建两条测试用子任务总结。

    两个子任务中故意包含一个重复 URL，
    用于测试全局来源去重。
    """

    first_task = ResearchTask(
        id=1,
        title="MCP 的核心架构",
        intent=(
            "了解 MCP Host、Client "
            "和 Server 的职责"
        ),
        query=(
            "Model Context Protocol "
            "architecture"
        ),
        status=TaskStatus.COMPLETED,
    )

    second_task = ResearchTask(
        id=2,
        title="MCP 的应用价值",
        intent=(
            "分析 MCP 对智能体工具接入"
            "和系统扩展的价值"
        ),
        query=(
            "Model Context Protocol "
            "agent use cases"
        ),
        status=TaskStatus.COMPLETED,
    )

    architecture_source = SearchResult(
        title="MCP Architecture",
        url="https://example.com/mcp",
        snippet=(
            "MCP 包含 Host、Client "
            "和 Server。"
        ),
    )

    duplicate_architecture_source = (
        SearchResult(
            title="MCP Architecture Duplicate",
            url="https://example.com/mcp/",
            snippet=(
                "MCP 包含 Host、Client "
                "和 Server。"
            ),
        )
    )

    application_source = SearchResult(
        title="MCP Agent Applications",
        url=(
            "https://example.org/"
            "mcp-applications"
        ),
        snippet=(
            "MCP 可以统一智能体应用"
            "与外部工具之间的连接方式。"
        ),
    )

    first_summary = TaskSummary(
        task=first_task,
        summary=(
            "MCP 采用 Host、Client 和 Server "
            "组成的架构。[1]"
        ),
        sources=[
            architecture_source,
        ],
    )

    second_summary = TaskSummary(
        task=second_task,
        summary=(
            "MCP 可以减少外部工具的重复"
            "适配工作。[1][2]"
        ),
        sources=[
            duplicate_architecture_source,
            application_source,
        ],
    )

    return [
        first_summary,
        second_summary,
    ]


def test_build_reporting_prompt() -> None:
    """
    验证最终报告提示词包含研究主题和子任务总结。
    """

    summaries = create_test_summaries()

    prompt = build_reporting_prompt(
        topic="MCP 对智能体开发的价值",
        summaries=summaries,
    )

    assert (
        "MCP 对智能体开发的价值"
        in prompt
    )

    assert (
        "MCP 的核心架构"
        in prompt
    )

    assert (
        "MCP 的应用价值"
        in prompt
    )

    assert (
        "MCP 采用 Host、Client 和 Server"
        in prompt
    )

    assert (
        "MCP 可以减少外部工具"
        in prompt
    )


def test_build_reporting_prompt_deduplicates_sources() -> None:
    """
    验证相同 URL 只获得一个全局编号。
    """

    summaries = create_test_summaries()

    prompt = build_reporting_prompt(
        topic="MCP 研究",
        summaries=summaries,
    )

    # 相同 URL 的两个写法都应该对应全局来源 [1]。
    assert (
        "任务内来源 [1] 对应全局来源 [1]"
        in prompt
    )

    # 第二个任务的第二条来源应当成为全局来源 [2]。
    assert (
        "任务内来源 [2] 对应全局来源 [2]"
        in prompt
    )

    # 去重后 URL 只应在全局来源列表中出现一次。
    assert (
        prompt.count(
            "URL：https://example.com/mcp"
        )
        == 1
    )


def test_build_reporting_prompt_rejects_empty_topic() -> None:
    """
    空研究主题应该被拒绝。
    """

    with pytest.raises(
        ValueError,
        match="研究主题不能为空",
    ):
        build_reporting_prompt(
            topic="   ",
            summaries=create_test_summaries(),
        )


def test_build_reporting_prompt_rejects_empty_summaries() -> None:
    """
    没有子任务总结时不能生成报告提示词。
    """

    with pytest.raises(
        ValueError,
        match="子任务总结不能为空",
    ):
        build_reporting_prompt(
            topic="MCP 研究",
            summaries=[],
        )


def test_reporting_service_returns_report() -> None:
    """
    验证报告服务能够返回最终报告。
    """

    model_response = """
# MCP 对智能体开发的价值

## 摘要

MCP 为智能体连接外部工具提供了标准化方式。[1][2]

## 研究背景

传统智能体项目通常需要分别适配不同工具接口。

## 主要发现

MCP 使用 Host、Client 和 Server 架构组织连接。[1]

## 综合分析

标准化协议能够降低重复集成成本。[2]

## 局限性

当前资料没有提供大规模性能测试数据。

## 结论

MCP 有助于提高智能体系统的扩展能力。

## 参考资料

[1] [MCP Architecture](https://example.com/mcp)

[2] [MCP Agent Applications](https://example.org/mcp-applications)
"""

    fake_llm = FakeLLM(
        response_text=model_response,
    )

    service = ReportingService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    report = service.generate(
        topic="MCP 对智能体开发的价值",
        summaries=create_test_summaries(),
    )

    assert report.startswith(
        "# MCP 对智能体开发的价值"
    )

    assert "## 摘要" in report
    assert "## 结论" in report
    assert "## 参考资料" in report

    assert len(
        fake_llm.received_messages
    ) == 2

    assert (
        fake_llm.received_messages[0]["role"]
        == "system"
    )

    assert (
        fake_llm.received_messages[1]["role"]
        == "user"
    )


def test_reporting_service_wraps_llm_error() -> None:
    """
    验证模型调用错误会转换为 RuntimeError。
    """

    fake_llm = FakeLLM(
        error=ConnectionError(
            "模拟模型连接失败"
        ),
    )

    service = ReportingService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="调用最终报告模型失败",
    ):
        service.generate(
            topic="MCP 研究",
            summaries=create_test_summaries(),
        )


def test_reporting_service_rejects_non_string_response() -> None:
    """
    验证模型返回非字符串时会抛出 TypeError。
    """

    fake_llm = FakeLLM(
        response_text={
            "report": "错误的数据类型",
        }
    )

    service = ReportingService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        TypeError,
        match="最终报告模型应当返回字符串",
    ):
        service.generate(
            topic="MCP 研究",
            summaries=create_test_summaries(),
        )


def test_reporting_service_rejects_empty_response() -> None:
    """
    验证模型返回空内容时会抛出 ValueError。
    """

    fake_llm = FakeLLM(
        response_text="   ",
    )

    service = ReportingService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="最终报告模型返回了空内容",
    ):
        service.generate(
            topic="MCP 研究",
            summaries=create_test_summaries(),
        )