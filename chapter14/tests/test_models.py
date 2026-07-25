import pytest
from pydantic import ValidationError

from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)


def test_create_research_task() -> None:
    """
    验证能够正常创建研究子任务。
    """

    task = ResearchTask(
        id=1,
        title="MCP 的基本概念",
        intent="了解 MCP 的设计目标和核心组成",
        query="Model Context Protocol architecture",
    )

    assert task.id == 1
    assert task.title == "MCP 的基本概念"
    assert task.status == TaskStatus.PENDING


def test_task_strips_whitespace() -> None:
    """
    验证字符串字段会自动去除首尾空格。
    """

    task = ResearchTask(
        id=1,
        title="  MCP 的基本概念  ",
        intent="  了解 MCP 的设计目标  ",
        query="  Model Context Protocol  ",
    )

    assert task.title == "MCP 的基本概念"
    assert task.intent == "了解 MCP 的设计目标"
    assert task.query == "Model Context Protocol"


def test_task_rejects_empty_query() -> None:
    """
    query 不能为空。
    """

    with pytest.raises(ValidationError):
        ResearchTask(
            id=1,
            title="MCP 的基本概念",
            intent="了解 MCP",
            query="",
        )


def test_task_id_must_start_from_one() -> None:
    """
    子任务编号必须大于等于 1。
    """

    with pytest.raises(ValidationError):
        ResearchTask(
            id=0,
            title="MCP 的基本概念",
            intent="了解 MCP",
            query="Model Context Protocol",
        )


def test_create_search_result() -> None:
    """
    验证搜索结果模型。
    """

    result = SearchResult(
        title="Model Context Protocol",
        url="https://example.com/mcp",
        snippet="MCP 是一种连接模型和外部工具的协议。",
    )

    assert result.title == "Model Context Protocol"
    assert result.url == "https://example.com/mcp"


def test_create_task_summary() -> None:
    """
    验证任务、搜索结果和总结可以组合。
    """

    task = ResearchTask(
        id=1,
        title="MCP 的基本概念",
        intent="了解 MCP",
        query="Model Context Protocol",
        status=TaskStatus.COMPLETED,
    )

    source = SearchResult(
        title="MCP Introduction",
        url="https://example.com/mcp",
        snippet="MCP introduction",
    )

    summary = TaskSummary(
        task=task,
        summary="MCP 用于连接大模型应用和外部数据或工具。",
        sources=[source],
    )

    assert summary.task.status == TaskStatus.COMPLETED
    assert len(summary.sources) == 1


def test_create_research_state() -> None:
    """
    验证研究状态的默认值。
    """

    state = ResearchState(
        topic="MCP 协议对智能体开发有什么价值？",
    )

    assert state.status == ResearchStatus.CREATED
    assert state.tasks == []
    assert state.summaries == []
    assert state.final_report == ""
    assert state.error_message is None


def test_research_state_lists_are_independent() -> None:
    """
    验证不同 ResearchState 不会共享同一个列表对象。

    default_factory=list 可以避免可变默认值共享问题。
    """

    state_one = ResearchState(topic="主题一")
    state_two = ResearchState(topic="主题二")

    state_one.tasks.append(
        ResearchTask(
            id=1,
            title="测试任务",
            intent="测试列表是否独立",
            query="test query",
        )
    )

    assert len(state_one.tasks) == 1
    assert state_two.tasks == []


def test_research_state_can_be_serialized() -> None:
    """
    验证研究状态可以转换为字典。
    """

    state = ResearchState(
        topic="MCP 协议研究",
    )

    state_data = state.model_dump(mode="json")

    assert state_data["topic"] == "MCP 协议研究"
    assert state_data["status"] == "created"
    assert state_data["tasks"] == []