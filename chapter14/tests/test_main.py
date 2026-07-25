from pathlib import Path

from fastapi.testclient import TestClient

from chapter14.backend.api_models import (
    ResearchResponse,
)
from chapter14.backend.dependencies import (
    build_deep_research_agent,
)
from chapter14.backend.main import app
from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
    TaskSummary,
)


class FakeDeepResearchAgent:
    """
    用于测试 FastAPI 接口的假 Agent。
    """

    def __init__(self) -> None:
        self.last_run_id = "test-run-001"

        self.last_report_path = Path(
            "chapter14/workspace/reports/"
            "test-run-001.md"
        )

    def research(
        self,
        topic: str,
    ) -> ResearchState:
        """
        返回固定研究结果，不调用真实模型或搜索服务。
        """

        task = ResearchTask(
            id=1,
            title="测试子任务",
            intent="验证 API 是否能够返回研究结果",
            query="test research query",
            status=TaskStatus.COMPLETED,
        )

        summary = TaskSummary(
            task=task,
            summary="这是测试任务总结。[1]",
            sources=[],
        )

        return ResearchState(
            topic=topic,
            tasks=[task],
            summaries=[summary],
            final_report=(
                f"# {topic}\n\n"
                "## 摘要\n\n"
                "这是一份测试研究报告。\n\n"
                "## 结论\n\n"
                "API 接口运行正常。"
            ),
            status=ResearchStatus.COMPLETED,
        )


class FailingDeepResearchAgent:
    """
    用于模拟研究流程执行失败。
    """

    last_run_id = None
    last_report_path = None

    def research(
        self,
        topic: str,
    ) -> ResearchState:
        raise RuntimeError(
            "模拟研究流程失败"
        )


def override_successful_agent() -> FakeDeepResearchAgent:
    """
    返回测试使用的成功 Agent。
    """

    return FakeDeepResearchAgent()


def override_failing_agent() -> FailingDeepResearchAgent:
    """
    返回测试使用的失败 Agent。
    """

    return FailingDeepResearchAgent()


client = TestClient(app)


def test_health_check() -> None:
    """
    验证健康检查接口。
    """

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "deep-research-agent",
    }


def test_create_research() -> None:
    """
    验证研究接口能够返回完整结果。
    """

    app.dependency_overrides[
        build_deep_research_agent
    ] = override_successful_agent

    try:
        response = client.post(
            "/research",
            json={
                "topic": "MCP 协议研究",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    response_data = response.json()

    validated_response = (
        ResearchResponse.model_validate(
            response_data
        )
    )

    assert (
        validated_response.run_id
        == "test-run-001"
    )

    assert (
        validated_response.topic
        == "MCP 协议研究"
    )

    assert (
        validated_response.status
        == "completed"
    )

    assert (
        validated_response.task_count
        == 1
    )

    assert (
        validated_response.summary_count
        == 1
    )

    assert (
        "API 接口运行正常"
        in validated_response.report
    )


def test_create_research_strips_topic_whitespace() -> None:
    """
    验证请求主题会自动去除首尾空格。
    """

    app.dependency_overrides[
        build_deep_research_agent
    ] = override_successful_agent

    try:
        response = client.post(
            "/research",
            json={
                "topic": "  MCP 协议研究  ",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    assert (
        response.json()["topic"]
        == "MCP 协议研究"
    )


def test_create_research_rejects_empty_topic() -> None:
    """
    验证空研究主题会被 FastAPI 拒绝。
    """

    response = client.post(
        "/research",
        json={
            "topic": "   ",
        },
    )

    assert response.status_code == 422


def test_create_research_rejects_missing_topic() -> None:
    """
    验证缺少 topic 字段会返回 422。
    """

    response = client.post(
        "/research",
        json={},
    )

    assert response.status_code == 422


def test_create_research_handles_agent_failure() -> None:
    """
    验证 Agent 执行失败时返回 500。
    """

    app.dependency_overrides[
        build_deep_research_agent
    ] = override_failing_agent

    try:
        response = client.post(
            "/research",
            json={
                "topic": "失败测试主题",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500

    assert (
        "模拟研究流程失败"
        in response.json()["detail"]
    )