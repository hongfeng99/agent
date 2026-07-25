from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from chapter14.backend.agent import (
    EventHandler,
)
from chapter14.backend.dependencies import (
    get_agent_factory,
    get_research_job_store,
)
from chapter14.backend.main import app
from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)
from chapter14.backend.task_manager import (
    ResearchJobStore,
)


class FakeBackgroundAgent:
    """
    用于测试后台 API 的假 Agent。
    """

    def __init__(
        self,
        event_handler: EventHandler | None,
        should_fail: bool = False,
    ) -> None:
        self._event_handler = event_handler
        self._should_fail = should_fail

        self.last_run_id: str | None = None
        self.last_report_path: Path | None = None

    def _emit(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if self._event_handler is None:
            return

        self._event_handler(
            event_type,
            message,
            data or {},
        )

    def research(
        self,
        topic: str,
    ) -> ResearchState:
        """
        模拟一个完整后台研究过程。
        """

        self._emit(
            "planning_started",
            "正在制定研究计划。",
        )

        self._emit(
            "planning_completed",
            "研究规划完成。",
            {
                "task_count": 2,
            },
        )

        first_task = ResearchTask(
            id=1,
            title="基本概念",
            intent="研究基本概念",
            query="basic concept",
            status=TaskStatus.COMPLETED,
        )

        second_task = ResearchTask(
            id=2,
            title="实际应用",
            intent="研究实际应用",
            query="applications",
            status=TaskStatus.COMPLETED,
        )

        self._emit(
            "task_started",
            "开始执行子任务 1。",
            {
                "task_id": 1,
            },
        )

        self._emit(
            "search_started",
            "正在搜索子任务 1。",
            {
                "task_id": 1,
            },
        )

        self._emit(
            "task_completed",
            "子任务 1 执行完成。",
            {
                "task_id": 1,
            },
        )

        if self._should_fail:
            raise RuntimeError(
                "模拟后台研究失败"
            )

        self._emit(
            "task_started",
            "开始执行子任务 2。",
            {
                "task_id": 2,
            },
        )

        self._emit(
            "task_completed",
            "子任务 2 执行完成。",
            {
                "task_id": 2,
            },
        )

        self._emit(
            "reporting_started",
            "正在生成最终报告。",
        )

        self.last_run_id = "internal-run-001"

        self.last_report_path = Path(
            "chapter14/workspace/reports/"
            "internal-run-001.md"
        )

        report = (
            f"# {topic}\n\n"
            "## 摘要\n\n"
            "这是后台任务生成的测试报告。"
        )

        self._emit(
            "research_completed",
            "深度研究任务执行完成。",
        )

        return ResearchState(
            topic=topic,
            tasks=[
                first_task,
                second_task,
            ],
            summaries=[],
            final_report=report,
            status=ResearchStatus.COMPLETED,
        )


def successful_agent_factory(
    event_handler: EventHandler | None,
) -> FakeBackgroundAgent:
    """
    创建成功执行的假 Agent。
    """

    return FakeBackgroundAgent(
        event_handler=event_handler,
        should_fail=False,
    )


def failing_agent_factory(
    event_handler: EventHandler | None,
) -> FakeBackgroundAgent:
    """
    创建执行失败的假 Agent。
    """

    return FakeBackgroundAgent(
        event_handler=event_handler,
        should_fail=True,
    )


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_dependencies() -> None:
    """
    每个测试前后清理任务仓库和依赖覆盖。
    """

    store = get_research_job_store()
    store.clear()

    app.dependency_overrides.clear()

    yield

    store.clear()
    app.dependency_overrides.clear()


def test_create_background_research() -> None:
    """
    验证可以创建后台研究任务。
    """

    app.dependency_overrides[
        get_agent_factory
    ] = lambda: successful_agent_factory

    response = client.post(
        "/research/tasks",
        json={
            "topic": "MCP 协议研究",
        },
    )

    assert response.status_code == 202

    response_data = response.json()

    assert response_data["job_id"]
    assert response_data["status"] == "queued"

    assert response_data["status_url"] == (
        f"/research/tasks/"
        f"{response_data['job_id']}"
    )


def test_get_completed_background_research() -> None:
    """
    验证可以查询已完成的后台任务。
    """

    app.dependency_overrides[
        get_agent_factory
    ] = lambda: successful_agent_factory

    create_response = client.post(
        "/research/tasks",
        json={
            "topic": "MCP 协议研究",
        },
    )

    job_id = create_response.json()[
        "job_id"
    ]

    status_response = client.get(
        f"/research/tasks/{job_id}"
    )

    assert status_response.status_code == 200

    job_data = status_response.json()

    assert job_data["job_id"] == job_id
    assert job_data["status"] == "completed"
    assert job_data["stage"] == "completed"
    assert job_data["progress"] == 100
    assert job_data["task_count"] == 2

    assert (
        job_data["completed_task_count"]
        == 2
    )

    assert (
        job_data["run_id"]
        == "internal-run-001"
    )

    assert (
        "后台任务生成的测试报告"
        in job_data["report"]
    )


def test_background_research_failure() -> None:
    """
    验证后台研究失败时会保存失败状态。
    """

    app.dependency_overrides[
        get_agent_factory
    ] = lambda: failing_agent_factory

    create_response = client.post(
        "/research/tasks",
        json={
            "topic": "失败测试主题",
        },
    )

    job_id = create_response.json()[
        "job_id"
    ]

    status_response = client.get(
        f"/research/tasks/{job_id}"
    )

    assert status_response.status_code == 200

    job_data = status_response.json()

    assert job_data["status"] == "failed"
    assert job_data["stage"] == "failed"

    assert (
        "模拟后台研究失败"
        in job_data["error_message"]
    )


def test_get_unknown_background_research() -> None:
    """
    查询不存在的任务应该返回 404。
    """

    response = client.get(
        "/research/tasks/not-found-job"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "没有找到指定的研究任务。"
    )


def test_background_research_rejects_empty_topic() -> None:
    """
    空研究主题应该返回 422。
    """

    response = client.post(
        "/research/tasks",
        json={
            "topic": "   ",
        },
    )

    assert response.status_code == 422