import pytest
from fastapi.testclient import TestClient

from chapter14.backend.api_models import (
    JobStatus,
)
from chapter14.backend.dependencies import (
    get_research_job_store,
)
from chapter14.backend.main import app
from chapter14.backend.task_manager import (
    ResearchJobStore,
)


client = TestClient(app)


@pytest.fixture
def event_store() -> ResearchJobStore:
    """
    创建独立的测试任务仓库。
    """

    store = ResearchJobStore()

    app.dependency_overrides[
        get_research_job_store
    ] = lambda: store

    yield store

    app.dependency_overrides.clear()


def create_completed_job(
    store: ResearchJobStore,
) -> str:
    """
    创建一个已经完成并包含事件的任务。
    """

    job = store.create(
        "SSE 测试主题"
    )

    store.append_event(
        job_id=job.job_id,
        event_type="planning_started",
        message="正在制定研究计划。",
    )

    store.append_event(
        job_id=job.job_id,
        event_type="planning_completed",
        message="研究规划完成。",
        data={
            "task_count": 3,
        },
    )

    store.append_event(
        job_id=job.job_id,
        event_type="job_completed",
        message="后台研究任务执行完成。",
    )

    store.update(
        job.job_id,
        status=JobStatus.COMPLETED,
        stage="completed",
        progress=100,
    )

    return job.job_id


def test_sse_returns_event_history(
    event_store: ResearchJobStore,
) -> None:
    """
    验证 SSE 接口会返回已经产生的事件。
    """

    job_id = create_completed_job(
        event_store
    )

    response = client.get(
        f"/research/tasks/{job_id}/events"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith(
        "text/event-stream"
    )

    content = response.text

    assert "event: job_queued" in content

    assert (
        "event: planning_started"
        in content
    )

    assert (
        "event: planning_completed"
        in content
    )

    assert (
        "event: job_completed"
        in content
    )

    assert "SSE 测试主题" in content


def test_sse_supports_after_sequence(
    event_store: ResearchJobStore,
) -> None:
    """
    验证可以跳过已经接收过的事件。
    """

    job_id = create_completed_job(
        event_store
    )

    response = client.get(
        f"/research/tasks/{job_id}/events",
        params={
            "after": 2,
        },
    )

    assert response.status_code == 200

    content = response.text

    assert "event: job_queued" not in content

    assert (
        "event: planning_started"
        not in content
    )

    assert (
        "event: planning_completed"
        in content
    )

    assert (
        "event: job_completed"
        in content
    )


def test_sse_supports_last_event_id(
    event_store: ResearchJobStore,
) -> None:
    """
    验证 Last-Event-ID 请求头。
    """

    job_id = create_completed_job(
        event_store
    )

    response = client.get(
        f"/research/tasks/{job_id}/events",
        headers={
            "Last-Event-ID": "3",
        },
    )

    assert response.status_code == 200

    content = response.text

    assert (
        "event: planning_completed"
        not in content
    )

    assert (
        "event: job_completed"
        in content
    )


def test_sse_rejects_invalid_last_event_id(
    event_store: ResearchJobStore,
) -> None:
    """
    非整数 Last-Event-ID 应返回 400。
    """

    job_id = create_completed_job(
        event_store
    )

    response = client.get(
        f"/research/tasks/{job_id}/events",
        headers={
            "Last-Event-ID": "abc",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Last-Event-ID 必须是整数。"
    )


def test_sse_returns_404_for_unknown_job(
    event_store: ResearchJobStore,
) -> None:
    """
    不存在的任务应返回 404。
    """

    response = client.get(
        "/research/tasks/not-found/events"
    )

    assert response.status_code == 404