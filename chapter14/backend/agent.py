from pathlib import Path
from typing import Any, Callable

from chapter14.backend.models import (
    ResearchState,
    ResearchStatus,
    ResearchTask,
    TaskStatus,
)
from chapter14.backend.services.note_service import (
    NoteService,
)
from chapter14.backend.services.planning_service import (
    PlanningService,
)
from chapter14.backend.services.reporting_service import (
    ReportingService,
)
from chapter14.backend.services.search_service import (
    SearchService,
)
from chapter14.backend.services.summarization_service import (
    SummarizationService,
)


EventHandler = Callable[
    [
        str,
        str,
        dict[str, Any],
    ],
    None,
]


class DeepResearchAgent:
    """
    自动化深度研究智能体。

    负责协调：

    1. 研究任务规划；
    2. 网络资料搜索；
    3. 子任务总结；
    4. 研究笔记保存；
    5. 最终报告生成；
    6. 研究状态管理；
    7. 运行事件通知。
    """

    def __init__(
        self,
        planner: PlanningService,
        searcher: SearchService,
        summarizer: SummarizationService,
        reporter: ReportingService,
        workspace_root: str | Path = (
            "chapter14/workspace"
        ),
        event_handler: EventHandler | None = None,
    ) -> None:
        """
        初始化 Deep Research Agent。

        参数：
            planner:
                研究规划服务。

            searcher:
                搜索服务。

            summarizer:
                子任务总结服务。

            reporter:
                最终报告服务。

            workspace_root:
                研究笔记和报告的保存目录。

            event_handler:
                可选的事件处理函数。
                后续 SSE 会复用这个接口。
        """

        self._planner = planner
        self._searcher = searcher
        self._summarizer = summarizer
        self._reporter = reporter

        self._workspace_root = Path(
            workspace_root
        )

        self._event_handler = event_handler

        self.last_run_id: str | None = None
        self.last_note_dir: Path | None = None
        self.last_report_path: Path | None = None

    def research(
        self,
        topic: str,
    ) -> ResearchState:
        """
        执行一次完整的深度研究任务。

        参数：
            topic:
                用户输入的研究主题。

        返回：
            最终的 ResearchState。

        异常：
            RuntimeError:
                研究流程中的某个阶段执行失败。
        """

        state = ResearchState(
            topic=topic,
        )

        note_service = NoteService(
            topic=topic,
            workspace_root=self._workspace_root,
        )

        self.last_run_id = note_service.run_id
        self.last_note_dir = note_service.note_dir
        self.last_report_path = None

        try:
            note_service.save_state(state)

            self._run_planning_stage(
                state=state,
                note_service=note_service,
            )

            self._run_research_stage(
                state=state,
                note_service=note_service,
            )

            self._run_reporting_stage(
                state=state,
                note_service=note_service,
            )

            return state

        except Exception as exc:
            self._handle_failure(
                state=state,
                note_service=note_service,
                error=exc,
            )

            raise RuntimeError(
                "深度研究任务执行失败："
                f"{exc}"
            ) from exc

    def _run_planning_stage(
        self,
        state: ResearchState,
        note_service: NoteService,
    ) -> None:
        """
        执行研究规划阶段。
        """

        state.status = ResearchStatus.PLANNING
        state.error_message = None

        note_service.save_state(state)

        self._emit(
            event_type="planning_started",
            message="正在制定研究计划。",
            data={
                "topic": state.topic,
            },
        )

        tasks = self._planner.plan(
            state.topic
        )

        state.tasks = tasks
        state.status = ResearchStatus.RESEARCHING

        note_service.save_state(state)

        self._emit(
            event_type="planning_completed",
            message=(
                f"研究规划完成，共生成 "
                f"{len(tasks)} 个子任务。"
            ),
            data={
                "task_count": len(tasks),
                "tasks": [
                    task.model_dump(
                        mode="json"
                    )
                    for task in tasks
                ],
            },
        )

    def _run_research_stage(
        self,
        state: ResearchState,
        note_service: NoteService,
    ) -> None:
        """
        逐个执行搜索和总结。
        """

        for task in list(state.tasks):
            running_task = task.model_copy(
                update={
                    "status": TaskStatus.RUNNING,
                }
            )

            self._replace_task(
                state=state,
                updated_task=running_task,
            )

            note_service.save_state(state)

            self._emit(
                event_type="task_started",
                message=(
                    f"开始执行子任务 "
                    f"{running_task.id}："
                    f"{running_task.title}"
                ),
                data={
                    "task_id": running_task.id,
                    "title": running_task.title,
                    "query": running_task.query,
                },
            )

            self._emit(
                event_type="search_started",
                message=(
                    f"正在搜索："
                    f"{running_task.query}"
                ),
                data={
                    "task_id": running_task.id,
                    "query": running_task.query,
                },
            )

            search_results = (
                self._searcher.search(
                    running_task.query
                )
            )

            if not search_results:
                raise ValueError(
                    f"子任务 {running_task.id} "
                    "没有搜索到可用资料。"
                )

            self._emit(
                event_type="search_completed",
                message=(
                    f"子任务 {running_task.id} "
                    f"获得 {len(search_results)} "
                    "条搜索结果。"
                ),
                data={
                    "task_id": running_task.id,
                    "result_count": len(
                        search_results
                    ),
                },
            )

            self._emit(
                event_type="summarization_started",
                message=(
                    f"正在总结子任务 "
                    f"{running_task.id}。"
                ),
                data={
                    "task_id": running_task.id,
                },
            )

            task_summary = (
                self._summarizer.summarize(
                    task=running_task,
                    search_results=search_results,
                )
            )

            self._replace_task(
                state=state,
                updated_task=task_summary.task,
            )

            state.summaries.append(
                task_summary
            )

            note_service.save_task_summary(
                task_summary
            )

            note_service.save_sources(
                state.summaries
            )

            note_service.save_state(state)

            self._emit(
                event_type="task_completed",
                message=(
                    f"子任务 "
                    f"{task_summary.task.id} "
                    "执行完成。"
                ),
                data={
                    "task_id": (
                        task_summary.task.id
                    ),
                    "source_count": len(
                        task_summary.sources
                    ),
                },
            )

    def _run_reporting_stage(
        self,
        state: ResearchState,
        note_service: NoteService,
    ) -> None:
        """
        生成并保存最终研究报告。
        """

        state.status = ResearchStatus.REPORTING

        note_service.save_state(state)

        self._emit(
            event_type="reporting_started",
            message="正在生成最终研究报告。",
            data={
                "summary_count": len(
                    state.summaries
                ),
            },
        )

        report = self._reporter.generate(
            topic=state.topic,
            summaries=state.summaries,
        )

        state.final_report = report
        state.status = ResearchStatus.COMPLETED
        state.error_message = None

        self.last_report_path = (
            note_service.save_report(
                report
            )
        )

        note_service.save_sources(
            state.summaries
        )

        note_service.save_state(state)

        self._emit(
            event_type="research_completed",
            message="深度研究任务执行完成。",
            data={
                "run_id": note_service.run_id,
                "report_path": str(
                    self.last_report_path
                ),
            },
        )

    def _handle_failure(
        self,
        state: ResearchState,
        note_service: NoteService,
        error: Exception,
    ) -> None:
        """
        记录研究失败状态。

        当前处于 running 状态的子任务会被标记为 failed。
        """

        updated_tasks: list[ResearchTask] = []

        for task in state.tasks:
            if task.status == TaskStatus.RUNNING:
                updated_tasks.append(
                    task.model_copy(
                        update={
                            "status": (
                                TaskStatus.FAILED
                            ),
                        }
                    )
                )
            else:
                updated_tasks.append(task)

        state.tasks = updated_tasks
        state.status = ResearchStatus.FAILED
        state.error_message = str(error)

        try:
            note_service.save_state(state)
        except Exception:
            # 保存错误状态失败时，
            # 不覆盖原始业务异常。
            pass

        self._emit(
            event_type="research_failed",
            message="深度研究任务执行失败。",
            data={
                "error_type": (
                    type(error).__name__
                ),
                "error_message": str(error),
            },
        )

    @staticmethod
    def _replace_task(
        state: ResearchState,
        updated_task: ResearchTask,
    ) -> None:
        """
        根据任务 ID 替换 ResearchState 中的任务。
        """

        for index, task in enumerate(
            state.tasks
        ):
            if task.id == updated_task.id:
                state.tasks[index] = (
                    updated_task
                )
                return

        raise ValueError(
            "没有在研究状态中找到任务："
            f"{updated_task.id}"
        )

    def _emit(
        self,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        发送运行事件。

        没有配置事件处理函数时，不执行任何操作。
        """

        if self._event_handler is None:
            return

        self._event_handler(
            event_type,
            message,
            data or {},
        )