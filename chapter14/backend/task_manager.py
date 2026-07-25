from collections.abc import Callable
from threading import RLock
from typing import Any
from uuid import uuid4

from chapter14.backend.agent import (
    DeepResearchAgent,
    EventHandler,
)
from chapter14.backend.api_models import (
    JobStatus,
    ResearchJobRecord,
)
from chapter14.backend.models import (
    TaskStatus,
)


AgentFactory = Callable[
    [EventHandler | None],
    DeepResearchAgent,
]


class ResearchJobNotFoundError(KeyError):
    """
    请求的后台研究任务不存在。
    """


class ResearchJobStore:
    """
    线程安全的内存任务状态仓库。

    当前版本适合本地学习和单进程运行。
    服务重启后，内存中的任务状态会消失。
    """

    def __init__(self) -> None:
        self._jobs: dict[
            str,
            ResearchJobRecord,
        ] = {}

        self._lock = RLock()

    def create(
        self,
        topic: str,
    ) -> ResearchJobRecord:
        """
        创建一个等待执行的研究任务。
        """

        job_id = uuid4().hex

        job = ResearchJobRecord(
            job_id=job_id,
            topic=topic,
        )

        with self._lock:
            self._jobs[job_id] = job

        return job.model_copy(
            deep=True
        )

    def get(
        self,
        job_id: str,
    ) -> ResearchJobRecord:
        """
        根据 job_id 查询任务。
        """

        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                raise ResearchJobNotFoundError(
                    job_id
                )

            return job.model_copy(
                deep=True
            )

    def update(
        self,
        job_id: str,
        **changes: Any,
    ) -> ResearchJobRecord:
        """
        更新后台研究任务状态。
        """

        with self._lock:
            current_job = self._jobs.get(
                job_id
            )

            if current_job is None:
                raise ResearchJobNotFoundError(
                    job_id
                )

            job_data = current_job.model_dump()
            job_data.update(changes)

            updated_job = (
                ResearchJobRecord.model_validate(
                    job_data
                )
            )

            self._jobs[job_id] = updated_job

            return updated_job.model_copy(
                deep=True
            )

    def clear(self) -> None:
        """
        清空所有任务。

        主要供自动化测试使用。
        """

        with self._lock:
            self._jobs.clear()


def create_job_event_handler(
    store: ResearchJobStore,
    job_id: str,
) -> EventHandler:
    """
    为指定后台任务创建 Agent 事件处理函数。

    DeepResearchAgent 发送的事件会被转换为：

    1. 当前阶段；
    2. 进度百分比；
    3. 当前提示信息；
    4. 已完成子任务数量。
    """

    def handle_event(
        event_type: str,
        message: str,
        data: dict[str, Any],
    ) -> None:
        if event_type == "planning_started":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="planning",
                message=message,
                progress=5,
            )
            return

        if event_type == "planning_completed":
            task_count = int(
                data.get("task_count", 0)
            )

            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="researching",
                message=message,
                progress=15,
                task_count=task_count,
            )
            return

        if event_type == "task_started":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="researching",
                message=message,
            )
            return

        if event_type == "search_started":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="searching",
                message=message,
            )
            return

        if event_type == "search_completed":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="summarizing",
                message=message,
            )
            return

        if event_type == "summarization_started":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="summarizing",
                message=message,
            )
            return

        if event_type == "task_completed":
            current_job = store.get(job_id)

            completed_count = (
                current_job.completed_task_count
                + 1
            )

            task_count = max(
                current_job.task_count,
                completed_count,
                1,
            )

            progress = 15 + int(
                70
                * completed_count
                / task_count
            )

            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="researching",
                message=message,
                progress=min(progress, 85),
                completed_task_count=(
                    completed_count
                ),
            )
            return

        if event_type == "reporting_started":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="reporting",
                message=message,
                progress=90,
            )
            return

        if event_type == "research_completed":
            store.update(
                job_id,
                status=JobStatus.RUNNING,
                stage="completed",
                message=message,
                progress=100,
            )
            return

        if event_type == "research_failed":
            store.update(
                job_id,
                status=JobStatus.FAILED,
                stage="failed",
                message=message,
                error_message=str(
                    data.get(
                        "error_message",
                        "未知错误",
                    )
                ),
            )

    return handle_event


def execute_research_job(
    job_id: str,
    topic: str,
    store: ResearchJobStore,
    agent_factory: AgentFactory,
) -> None:
    """
    在后台执行一次完整的深度研究任务。

    该函数会捕获异常并保存失败状态，
    避免后台异常直接影响 FastAPI 请求。
    """

    store.update(
        job_id,
        status=JobStatus.RUNNING,
        stage="initializing",
        message="正在初始化深度研究智能体。",
        progress=1,
        error_message=None,
    )

    event_handler = create_job_event_handler(
        store=store,
        job_id=job_id,
    )

    try:
        agent = agent_factory(
            event_handler
        )

        state = agent.research(topic)

        completed_task_count = sum(
            task.status
            == TaskStatus.COMPLETED
            for task in state.tasks
        )

        report_path = None

        if agent.last_report_path is not None:
            report_path = str(
                agent.last_report_path
            )

        store.update(
            job_id,
            status=JobStatus.COMPLETED,
            stage="completed",
            message="深度研究任务执行完成。",
            progress=100,
            task_count=len(state.tasks),
            completed_task_count=(
                completed_task_count
            ),
            run_id=agent.last_run_id,
            report=state.final_report,
            report_path=report_path,
            error_message=None,
        )

    except Exception as exc:
        store.update(
            job_id,
            status=JobStatus.FAILED,
            stage="failed",
            message="深度研究任务执行失败。",
            error_message=str(exc),
        )