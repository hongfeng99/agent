import json
import re
import unicodedata

from datetime import datetime
from pathlib import Path
from typing import Iterable


from chapter14.backend.models import (
    ResearchState,
    TaskSummary,
)
from chapter14.backend.utils.source_utils import (
    normalize_url,
)


def make_topic_slug(
    topic: str,
    max_length: int = 40,
) -> str:
    """
    将研究主题转换为适合文件夹名称的字符串。

    处理内容：

    1. 去除首尾空格；
    2. 删除 Windows 文件名不允许使用的字符；
    3. 将连续空白转换为连字符；
    4. 限制文件名长度；
    5. 主题无法生成有效名称时使用 research。
    """

    if not isinstance(topic, str):
        raise TypeError(
            "topic 必须是字符串，"
            f"实际类型为：{type(topic).__name__}"
        )

    if max_length < 1:
        raise ValueError(
            "max_length 必须大于等于 1。"
        )

    cleaned_topic = unicodedata.normalize(
        "NFKC",
        topic,
    ).strip().lower()

    # 删除 Windows 文件名中的非法字符。
    cleaned_topic = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        " ",
        cleaned_topic,
    )

    # 将连续空格转换为连字符。
    cleaned_topic = re.sub(
        r"\s+",
        "-",
        cleaned_topic,
    )

    # 合并连续连字符。
    cleaned_topic = re.sub(
        r"-+",
        "-",
        cleaned_topic,
    )

    cleaned_topic = cleaned_topic.strip(
        "-._ "
    )

    if not cleaned_topic:
        return "research"

    slug = cleaned_topic[:max_length]

    return slug.rstrip("-._ ") or "research"


class NoteService:
    """
    研究笔记持久化服务。

    负责：

    1. 为一次研究创建独立目录；
    2. 保存完整研究状态；
    3. 保存每个子任务的 Markdown 笔记；
    4. 汇总并保存所有资料来源；
    5. 保存最终研究报告。
    """

    def __init__(
        self,
        topic: str,
        workspace_root: str | Path = (
            "chapter14/workspace"
        ),
        now: datetime | None = None,
    ) -> None:
        """
        初始化笔记服务。

        参数：
            topic:
                当前研究主题。

            workspace_root:
                工作目录根路径。

            now:
                用于生成运行编号的时间。
                测试时可以传入固定时间。
        """

        if not isinstance(topic, str):
            raise TypeError(
                "topic 必须是字符串，"
                f"实际类型为：{type(topic).__name__}"
            )

        topic = topic.strip()

        if not topic:
            raise ValueError(
                "研究主题不能为空。"
            )

        self.topic = topic
        self.workspace_root = Path(
            workspace_root
        )

        self.notes_root = (
            self.workspace_root / "notes"
        )

        self.reports_root = (
            self.workspace_root / "reports"
        )

        self.notes_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.reports_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        effective_time = now or datetime.now()

        timestamp = effective_time.strftime(
            "%Y%m%d_%H%M%S"
        )

        topic_slug = make_topic_slug(topic)

        base_run_id = (
            f"{timestamp}_{topic_slug}"
        )

        self.note_dir = (
            self._create_unique_note_directory(
                base_run_id
            )
        )

        self.run_id = self.note_dir.name

    def _create_unique_note_directory(
        self,
        base_run_id: str,
    ) -> Path:
        """
        创建不覆盖旧研究记录的目录。

        同一秒内重复创建时，会依次追加：

        _02
        _03
        _04
        """

        candidate = (
            self.notes_root / base_run_id
        )

        suffix = 2

        while candidate.exists():
            candidate = self.notes_root / (
                f"{base_run_id}_{suffix:02d}"
            )
            suffix += 1

        candidate.mkdir(
            parents=True,
            exist_ok=False,
        )

        return candidate

    @staticmethod
    def _write_text(
        path: Path,
        content: str,
    ) -> None:
        """
        以 UTF-8 编码写入文本。

        先写入临时文件，再替换正式文件，
        降低写入中断导致文件损坏的风险。
        """

        temporary_path = path.with_name(
            path.name + ".tmp"
        )

        temporary_path.write_text(
            content,
            encoding="utf-8",
        )

        temporary_path.replace(path)

    def save_state(
        self,
        state: ResearchState,
    ) -> Path:
        """
        保存完整研究状态。

        返回保存后的文件路径。
        """

        if not isinstance(
            state,
            ResearchState,
        ):
            raise TypeError(
                "state 必须是 ResearchState，"
                f"实际类型为："
                f"{type(state).__name__}"
            )

        state_path = (
            self.note_dir
            / "research_state.json"
        )

        state_json = state.model_dump_json(
            indent=2,
        )

        self._write_text(
            state_path,
            state_json,
        )

        return state_path

    def save_task_summary(
        self,
        task_summary: TaskSummary,
    ) -> Path:
        """
        将单个子任务总结保存为 Markdown。
        """

        if not isinstance(
            task_summary,
            TaskSummary,
        ):
            raise TypeError(
                "task_summary 必须是 TaskSummary，"
                f"实际类型为："
                f"{type(task_summary).__name__}"
            )

        task = task_summary.task

        source_sections: list[str] = []

        for index, source in enumerate(
            task_summary.sources,
            start=1,
        ):
            snippet = (
                source.snippet
                or "该来源没有提供摘要。"
            )

            source_sections.append(
                "\n".join(
                    [
                        (
                            f"{index}. "
                            f"[{source.title}]"
                            f"({source.url})"
                        ),
                        f"   - 摘要：{snippet}",
                    ]
                )
            )

        if source_sections:
            sources_text = "\n\n".join(
                source_sections
            )
        else:
            sources_text = (
                "本任务没有保存搜索来源。"
            )

        markdown_content = "\n".join(
            [
                f"# {task.title}",
                "",
                "## 任务信息",
                "",
                f"- 任务编号：{task.id}",
                f"- 当前状态：{task.status.value}",
                f"- 研究目的：{task.intent}",
                f"- 搜索语句：{task.query}",
                "",
                "## 研究总结",
                "",
                task_summary.summary,
                "",
                "## 搜索来源",
                "",
                sources_text,
                "",
            ]
        )

        task_path = self.note_dir / (
            f"task_{task.id:02d}.md"
        )

        self._write_text(
            task_path,
            markdown_content,
        )

        return task_path

    def save_sources(
        self,
        summaries: Iterable[TaskSummary],
    ) -> Path:
        """
        汇总所有子任务的资料来源并保存为 JSON。

        相同 URL 只保存一次，同时记录该来源
        被哪些研究子任务使用。
        """

        source_map: dict[
            str,
            dict[str, object],
        ] = {}

        for summary in summaries:
            if not isinstance(
                summary,
                TaskSummary,
            ):
                raise TypeError(
                    "summaries 中的元素必须是 "
                    "TaskSummary。"
                )

            task_id = summary.task.id

            for source in summary.sources:
                normalized_url = (
                    normalize_url(source.url)
                )

                source_key = (
                    normalized_url
                    or source.url.strip()
                )

                if not source_key:
                    continue

                if source_key not in source_map:
                    source_map[source_key] = {
                        "title": source.title,
                        "url": source.url,
                        "snippet": source.snippet,
                        "task_ids": [],
                    }

                task_ids = source_map[
                    source_key
                ]["task_ids"]

                if not isinstance(
                    task_ids,
                    list,
                ):
                    raise RuntimeError(
                        "内部来源数据格式错误。"
                    )

                if task_id not in task_ids:
                    task_ids.append(task_id)

        sources_path = (
            self.note_dir / "sources.json"
        )

        source_data = list(
            source_map.values()
        )

        source_json = json.dumps(
            source_data,
            ensure_ascii=False,
            indent=2,
        )

        self._write_text(
            sources_path,
            source_json,
        )

        return sources_path

    def save_report(
        self,
        report: str,
    ) -> Path:
        """
        保存最终 Markdown 研究报告。

        报告会同时保存到：

        1. 当前研究笔记目录；
        2. workspace/reports 目录。
        """

        if not isinstance(report, str):
            raise TypeError(
                "report 必须是字符串，"
                f"实际类型为："
                f"{type(report).__name__}"
            )

        report = report.strip()

        if not report:
            raise ValueError(
                "研究报告不能为空。"
            )

        local_report_path = (
            self.note_dir / "final_report.md"
        )

        public_report_path = (
            self.reports_root
            / f"{self.run_id}.md"
        )

        report_content = report + "\n"

        self._write_text(
            local_report_path,
            report_content,
        )

        self._write_text(
            public_report_path,
            report_content,
        )

        return public_report_path