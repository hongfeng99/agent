import json
from datetime import datetime
from pathlib import Path

import pytest

from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    SearchResult,
    TaskStatus,
    TaskSummary,
)
from chapter14.backend.services.note_service import (
    NoteService,
    make_topic_slug,
)


def create_task_summary(
    task_id: int = 1,
    source_url: str = (
        "https://example.com/mcp"
    ),
) -> TaskSummary:
    """
    创建测试使用的任务总结。
    """

    task = ResearchTask(
        id=task_id,
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

    source = SearchResult(
        title="MCP Architecture",
        url=source_url,
        snippet=(
            "MCP 包含 Host、Client "
            "和 Server。"
        ),
    )

    return TaskSummary(
        task=task,
        summary=(
            "MCP 采用 Host、Client 和 "
            "Server 协作架构。[1]"
        ),
        sources=[source],
    )


def test_make_topic_slug() -> None:
    """
    验证研究主题能够转换为文件夹名称。
    """

    slug = make_topic_slug(
        "  MCP 协议：架构 / 应用？  "
    )

    assert slug == "mcp-协议-架构-应用"


def test_make_topic_slug_uses_fallback() -> None:
    """
    无法生成有效名称时使用 research。
    """

    slug = make_topic_slug(
        '  <>:"/\\|?*  '
    )

    assert slug == "research"


def test_note_service_creates_directories(
    tmp_path: Path,
) -> None:
    """
    验证初始化时会创建笔记和报告目录。
    """

    service = NoteService(
        topic="MCP 协议研究",
        workspace_root=tmp_path,
        now=datetime(
            2026,
            7,
            25,
            15,
            30,
            0,
        ),
    )

    assert service.note_dir.exists()

    assert service.run_id == (
        "20260725_153000_mcp-协议研究"
    )

    assert (
        tmp_path / "notes"
    ).exists()

    assert (
        tmp_path / "reports"
    ).exists()


def test_note_service_creates_unique_directory(
    tmp_path: Path,
) -> None:
    """
    同一时间和主题不会覆盖旧目录。
    """

    fixed_time = datetime(
        2026,
        7,
        25,
        15,
        30,
        0,
    )

    first_service = NoteService(
        topic="MCP 研究",
        workspace_root=tmp_path,
        now=fixed_time,
    )

    second_service = NoteService(
        topic="MCP 研究",
        workspace_root=tmp_path,
        now=fixed_time,
    )

    assert (
        first_service.run_id
        == "20260725_153000_mcp-研究"
    )

    assert (
        second_service.run_id
        == "20260725_153000_mcp-研究_02"
    )


def test_save_state(
    tmp_path: Path,
) -> None:
    """
    验证 ResearchState 能够保存为 JSON。
    """

    summary = create_task_summary()

    state = ResearchState(
        topic="MCP 协议研究",
        tasks=[summary.task],
        summaries=[summary],
        status=ResearchStatus.RESEARCHING,
    )

    service = NoteService(
        topic=state.topic,
        workspace_root=tmp_path,
    )

    state_path = service.save_state(
        state
    )

    assert state_path.exists()

    state_data = json.loads(
        state_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        state_data["topic"]
        == "MCP 协议研究"
    )

    assert (
        state_data["status"]
        == "researching"
    )

    assert len(
        state_data["summaries"]
    ) == 1


def test_save_task_summary(
    tmp_path: Path,
) -> None:
    """
    验证任务总结能够保存为 Markdown。
    """

    summary = create_task_summary()

    service = NoteService(
        topic="MCP 协议研究",
        workspace_root=tmp_path,
    )

    task_path = (
        service.save_task_summary(
            summary
        )
    )

    assert task_path.exists()

    assert task_path.name == (
        "task_01.md"
    )

    content = task_path.read_text(
        encoding="utf-8",
    )

    assert "# MCP 的核心架构" in content
    assert "## 研究总结" in content
    assert "## 搜索来源" in content

    assert (
        "https://example.com/mcp"
        in content
    )


def test_save_sources_removes_duplicate_urls(
    tmp_path: Path,
) -> None:
    """
    验证相同 URL 只保存一次。
    """

    first_summary = create_task_summary(
        task_id=1,
        source_url=(
            "https://example.com/mcp"
        ),
    )

    second_summary = create_task_summary(
        task_id=2,
        source_url=(
            "https://example.com/mcp/"
        ),
    )

    service = NoteService(
        topic="MCP 协议研究",
        workspace_root=tmp_path,
    )

    sources_path = service.save_sources(
        [
            first_summary,
            second_summary,
        ]
    )

    source_data = json.loads(
        sources_path.read_text(
            encoding="utf-8",
        )
    )

    assert len(source_data) == 1

    assert source_data[0]["task_ids"] == [
        1,
        2,
    ]


def test_save_report(
    tmp_path: Path,
) -> None:
    """
    验证最终报告会保存两个副本。
    """

    service = NoteService(
        topic="MCP 协议研究",
        workspace_root=tmp_path,
    )

    report = """
# MCP 协议研究报告

## 结论

MCP 可以统一模型与外部工具之间的连接方式。
"""

    public_report_path = (
        service.save_report(report)
    )

    local_report_path = (
        service.note_dir
        / "final_report.md"
    )

    assert public_report_path.exists()
    assert local_report_path.exists()

    assert (
        public_report_path.parent
        == tmp_path / "reports"
    )

    assert (
        public_report_path.read_text(
            encoding="utf-8",
        )
        ==
        local_report_path.read_text(
            encoding="utf-8",
        )
    )


def test_save_report_rejects_empty_text(
    tmp_path: Path,
) -> None:
    """
    空报告不能被保存。
    """

    service = NoteService(
        topic="MCP 协议研究",
        workspace_root=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="研究报告不能为空",
    ):
        service.save_report("   ")