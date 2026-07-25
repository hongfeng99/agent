import json
from pathlib import Path
from typing import Any

import pytest

from chapter14.backend.agent import (
    DeepResearchAgent,
)
from chapter14.backend.models import (
    ResearchStatus,
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)


class FakePlanningService:
    """
    模拟研究规划服务。
    """

    def __init__(
        self,
        tasks: list[ResearchTask],
    ) -> None:
        self.tasks = tasks
        self.received_topic = ""

    def plan(
        self,
        topic: str,
    ) -> list[ResearchTask]:
        self.received_topic = topic
        return self.tasks


class FakeSearchService:
    """
    模拟搜索服务。
    """

    def __init__(
        self,
        results_by_query: dict[
            str,
            list[SearchResult],
        ],
        error_query: str | None = None,
    ) -> None:
        self.results_by_query = (
            results_by_query
        )

        self.error_query = error_query
        self.received_queries: list[str] = []

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        self.received_queries.append(query)

        if query == self.error_query:
            raise ConnectionError(
                "模拟搜索服务连接失败"
            )

        return self.results_by_query.get(
            query,
            [],
        )


class FakeSummarizationService:
    """
    模拟任务总结服务。
    """

    def __init__(self) -> None:
        self.received_task_ids: list[int] = []

    def summarize(
        self,
        task: ResearchTask,
        search_results: list[SearchResult],
    ) -> TaskSummary:
        self.received_task_ids.append(
            task.id
        )

        completed_task = task.model_copy(
            update={
                "status": TaskStatus.COMPLETED,
            }
        )

        return TaskSummary(
            task=completed_task,
            summary=(
                f"任务 {task.id} 的研究总结。[1]"
            ),
            sources=search_results,
        )


class FakeReportingService:
    """
    模拟最终报告服务。
    """

    def __init__(self) -> None:
        self.received_topic = ""
        self.received_summary_count = 0

    def generate(
        self,
        topic: str,
        summaries: list[TaskSummary],
    ) -> str:
        self.received_topic = topic

        self.received_summary_count = len(
            summaries
        )

        return (
            f"# {topic}\n\n"
            "## 摘要\n\n"
            "这是最终研究报告。\n\n"
            "## 结论\n\n"
            "研究任务已经完成。"
        )


def create_tasks() -> list[ResearchTask]:
    """
    创建测试任务。
    """

    return [
        ResearchTask(
            id=1,
            title="基本概念",
            intent="研究基本概念",
            query="basic concept query",
        ),
        ResearchTask(
            id=2,
            title="实际应用",
            intent="研究实际应用",
            query="application query",
        ),
    ]


def create_search_results() -> dict[
    str,
    list[SearchResult],
]:
    """
    创建测试搜索结果。
    """

    return {
        "basic concept query": [
            SearchResult(
                title="基本概念来源",
                url=(
                    "https://example.com/"
                    "concept"
                ),
                snippet="基本概念资料。",
            )
        ],
        "application query": [
            SearchResult(
                title="应用来源",
                url=(
                    "https://example.com/"
                    "application"
                ),
                snippet="实际应用资料。",
            )
        ],
    }


def test_agent_completes_full_workflow(
    tmp_path: Path,
) -> None:
    """
    验证完整研究工作流能够成功完成。
    """

    planner = FakePlanningService(
        tasks=create_tasks()
    )

    searcher = FakeSearchService(
        results_by_query=(
            create_search_results()
        )
    )

    summarizer = (
        FakeSummarizationService()
    )

    reporter = FakeReportingService()

    agent = DeepResearchAgent(
        planner=planner,  # type: ignore[arg-type]
        searcher=searcher,  # type: ignore[arg-type]
        summarizer=summarizer,  # type: ignore[arg-type]
        reporter=reporter,  # type: ignore[arg-type]
        workspace_root=tmp_path,
    )

    state = agent.research(
        "测试研究主题"
    )

    assert (
        state.status
        == ResearchStatus.COMPLETED
    )

    assert state.error_message is None
    assert len(state.tasks) == 2
    assert len(state.summaries) == 2

    assert all(
        task.status == TaskStatus.COMPLETED
        for task in state.tasks
    )

    assert (
        state.final_report.startswith(
            "# 测试研究主题"
        )
    )

    assert planner.received_topic == (
        "测试研究主题"
    )

    assert searcher.received_queries == [
        "basic concept query",
        "application query",
    ]

    assert (
        summarizer.received_task_ids
        == [1, 2]
    )

    assert (
        reporter.received_summary_count
        == 2
    )

    assert agent.last_note_dir is not None
    assert agent.last_report_path is not None

    assert (
        agent.last_note_dir
        / "research_state.json"
    ).exists()

    assert (
        agent.last_note_dir
        / "task_01.md"
    ).exists()

    assert (
        agent.last_note_dir
        / "task_02.md"
    ).exists()

    assert (
        agent.last_note_dir
        / "sources.json"
    ).exists()

    assert (
        agent.last_note_dir
        / "final_report.md"
    ).exists()

    assert agent.last_report_path.exists()


def test_agent_saves_completed_state(
    tmp_path: Path,
) -> None:
    """
    验证磁盘中的研究状态为 completed。
    """

    agent = DeepResearchAgent(
        planner=FakePlanningService(
            create_tasks()
        ),  # type: ignore[arg-type]
        searcher=FakeSearchService(
            create_search_results()
        ),  # type: ignore[arg-type]
        summarizer=(
            FakeSummarizationService()
        ),  # type: ignore[arg-type]
        reporter=(
            FakeReportingService()
        ),  # type: ignore[arg-type]
        workspace_root=tmp_path,
    )

    agent.research("测试主题")

    assert agent.last_note_dir is not None

    state_path = (
        agent.last_note_dir
        / "research_state.json"
    )

    state_data = json.loads(
        state_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        state_data["status"]
        == "completed"
    )

    assert (
        len(state_data["summaries"])
        == 2
    )

    assert state_data["error_message"] is None


def test_agent_records_failure(
    tmp_path: Path,
) -> None:
    """
    验证搜索失败时会保存失败状态。
    """

    tasks = create_tasks()

    searcher = FakeSearchService(
        results_by_query=(
            create_search_results()
        ),
        error_query="application query",
    )

    agent = DeepResearchAgent(
        planner=FakePlanningService(
            tasks
        ),  # type: ignore[arg-type]
        searcher=searcher,  # type: ignore[arg-type]
        summarizer=(
            FakeSummarizationService()
        ),  # type: ignore[arg-type]
        reporter=(
            FakeReportingService()
        ),  # type: ignore[arg-type]
        workspace_root=tmp_path,
    )

    with pytest.raises(
        RuntimeError,
        match="深度研究任务执行失败",
    ):
        agent.research("失败测试主题")

    assert agent.last_note_dir is not None

    state_path = (
        agent.last_note_dir
        / "research_state.json"
    )

    state_data = json.loads(
        state_path.read_text(
            encoding="utf-8"
        )
    )

    assert state_data["status"] == "failed"

    assert (
        "模拟搜索服务连接失败"
        in state_data["error_message"]
    )

    second_task = state_data["tasks"][1]

    assert (
        second_task["status"]
        == "failed"
    )


def test_agent_emits_events(
    tmp_path: Path,
) -> None:
    """
    验证 Agent 会发送运行事件。
    """

    received_events: list[
        tuple[
            str,
            str,
            dict[str, Any],
        ]
    ] = []

    def event_handler(
        event_type: str,
        message: str,
        data: dict[str, Any],
    ) -> None:
        received_events.append(
            (
                event_type,
                message,
                data,
            )
        )

    agent = DeepResearchAgent(
        planner=FakePlanningService(
            create_tasks()
        ),  # type: ignore[arg-type]
        searcher=FakeSearchService(
            create_search_results()
        ),  # type: ignore[arg-type]
        summarizer=(
            FakeSummarizationService()
        ),  # type: ignore[arg-type]
        reporter=(
            FakeReportingService()
        ),  # type: ignore[arg-type]
        workspace_root=tmp_path,
        event_handler=event_handler,
    )

    agent.research("事件测试主题")

    event_types = [
        event[0]
        for event in received_events
    ]

    assert (
        "planning_started"
        in event_types
    )

    assert (
        "planning_completed"
        in event_types
    )

    assert "search_started" in event_types

    assert (
        "summarization_started"
        in event_types
    )

    assert "task_completed" in event_types

    assert (
        "reporting_started"
        in event_types
    )

    assert (
        "research_completed"
        in event_types
    )