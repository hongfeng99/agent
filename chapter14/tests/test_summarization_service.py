from typing import Any

import pytest

from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
    TaskStatus,
)
from chapter14.backend.prompts import (
    build_summarization_prompt,
)
from chapter14.backend.services.summarization_service import (
    SummarizationService,
)


class FakeLLM:
    """
    用于测试 SummarizationService 的假大模型。
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


def create_test_task() -> ResearchTask:
    """
    创建测试用研究任务。
    """

    return ResearchTask(
        id=1,
        title="MCP 的核心架构",
        intent=(
            "了解 MCP Host、Client 和 Server "
            "之间的关系"
        ),
        query=(
            "Model Context Protocol "
            "host client server architecture"
        ),
    )


def create_test_results() -> list[SearchResult]:
    """
    创建测试用搜索结果。
    """

    return [
        SearchResult(
            title="MCP Architecture",
            url="https://example.com/mcp-architecture",
            snippet=(
                "MCP 架构包含 Host、Client 和 Server。"
                "Host 负责承载大模型应用，Client 负责建立"
                "协议连接，Server 提供资源和工具。"
            ),
        ),
        SearchResult(
            title="Understanding MCP",
            url="https://example.org/understanding-mcp",
            snippet=(
                "一个 Host 可以创建多个 MCP Client，"
                "每个 Client 通常连接一个 MCP Server。"
            ),
        ),
    ]


def test_build_summarization_prompt() -> None:
    """
    验证总结提示词包含任务和来源信息。
    """

    task = create_test_task()
    results = create_test_results()

    prompt = build_summarization_prompt(
        task=task,
        search_results=results,
    )

    assert "MCP 的核心架构" in prompt

    assert (
        "了解 MCP Host、Client 和 Server"
        in prompt
    )

    assert (
        "Model Context Protocol "
        "host client server architecture"
        in prompt
    )

    assert "[1]" in prompt
    assert "[2]" in prompt

    assert "MCP Architecture" in prompt
    assert "Understanding MCP" in prompt

    assert (
        "https://example.com/mcp-architecture"
        in prompt
    )


def test_build_summarization_prompt_rejects_empty_results() -> None:
    """
    搜索结果为空时不能构建总结提示词。
    """

    task = create_test_task()

    with pytest.raises(
        ValueError,
        match="搜索结果不能为空",
    ):
        build_summarization_prompt(
            task=task,
            search_results=[],
        )


def test_summarization_service_returns_summary() -> None:
    """
    验证总结服务能够返回 TaskSummary。
    """

    model_response = """
## 核心结论

MCP 采用 Host、Client 和 Server 三层协作架构。[1]

## 详细分析

Host 承载大模型应用，Client 负责协议连接，
Server 则向应用提供工具和资源。[1]
一个 Host 可以同时管理多个 Client。[2]

## 局限性

当前资料主要介绍架构组成，
没有详细讨论不同实现之间的性能差异。
"""

    fake_llm = FakeLLM(
        response_text=model_response,
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    task = create_test_task()
    results = create_test_results()

    task_summary = service.summarize(
        task=task,
        search_results=results,
    )

    assert (
        "MCP 采用 Host、Client 和 Server"
        in task_summary.summary
    )

    assert len(task_summary.sources) == 2

    assert (
        task_summary.task.status
        == TaskStatus.COMPLETED
    )

    assert task_summary.task.id == 1

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


def test_summarization_does_not_modify_original_task() -> None:
    """
    验证总结服务不会修改原始任务状态。
    """

    fake_llm = FakeLLM(
        response_text="有效的研究总结。[1]",
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    task = create_test_task()
    results = create_test_results()

    task_summary = service.summarize(
        task=task,
        search_results=results,
    )

    assert task.status == TaskStatus.PENDING

    assert (
        task_summary.task.status
        == TaskStatus.COMPLETED
    )


def test_summarization_service_rejects_empty_results() -> None:
    """
    验证没有搜索结果时无法生成总结。
    """

    fake_llm = FakeLLM(
        response_text="不会使用该内容",
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="搜索结果不能为空",
    ):
        service.summarize(
            task=create_test_task(),
            search_results=[],
        )


def test_summarization_service_wraps_llm_error() -> None:
    """
    验证模型调用错误会转换成 RuntimeError。
    """

    fake_llm = FakeLLM(
        error=ConnectionError(
            "模拟模型连接失败"
        ),
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="调用任务总结模型失败",
    ):
        service.summarize(
            task=create_test_task(),
            search_results=create_test_results(),
        )


def test_summarization_service_rejects_non_string_response() -> None:
    """
    验证模型返回非字符串时会抛出 TypeError。
    """

    fake_llm = FakeLLM(
        response_text={
            "summary": "错误的返回类型",
        }
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        TypeError,
        match="任务总结模型应当返回字符串",
    ):
        service.summarize(
            task=create_test_task(),
            search_results=create_test_results(),
        )


def test_summarization_service_rejects_empty_response() -> None:
    """
    验证模型返回空字符串时会抛出异常。
    """

    fake_llm = FakeLLM(
        response_text="   ",
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="任务总结模型返回了空内容",
    ):
        service.summarize(
            task=create_test_task(),
            search_results=create_test_results(),
        )


def test_summary_preserves_source_order() -> None:
    """
    验证 TaskSummary 中的来源顺序保持不变。
    """

    fake_llm = FakeLLM(
        response_text="研究总结。[1][2]",
    )

    service = SummarizationService(
        llm=fake_llm,  # type: ignore[arg-type]
    )

    results = create_test_results()

    task_summary = service.summarize(
        task=create_test_task(),
        search_results=results,
    )

    assert (
        task_summary.sources[0].title
        == "MCP Architecture"
    )

    assert (
        task_summary.sources[1].title
        == "Understanding MCP"
    )