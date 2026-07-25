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
    ResearchEvent,
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

    除了保存任务状态，还保存每个任务产生的事件历史。
    """

    def __init__(self) -> None:
        self._jobs: dict[
            str,
            ResearchJobRecord,
        ] = {}

        self._events: dict[
            str,
            list[ResearchEvent],
        ] = {}

        self._next_sequence: dict[
            str,
            int,
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
            self._events[job_id] = []
            self._next_sequence[job_id] = 1

        self.append_event(
            job_id=job_id,
            event_type="job_queued",
            message="研究任务已创建，等待执行。",
            data={
                "topic": topic,
            },
        )

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

    def append_event(
        self,
        job_id: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> ResearchEvent:
        """
        为后台任务追加一条运行事件。
        """

        with self._lock:
            if job_id not in self._jobs:
                raise ResearchJobNotFoundError(
                    job_id
                )

            sequence = self._next_sequence[
                job_id
            ]

            event = ResearchEvent(
                sequence=sequence,
                job_id=job_id,
                event_type=event_type,
                message=message,
                data=data or {},
            )

            self._events[job_id].append(
                event
            )

            self._next_sequence[job_id] = (
                sequence + 1
            )

            return event.model_copy(
                deep=True
            )

    def get_events(
        self,
        job_id: str,
        after_sequence: int = 0,
    ) -> list[ResearchEvent]:
        """
        获取指定序号之后产生的事件。

        after_sequence=0 表示获取全部事件。
        """

        if after_sequence < 0:
            raise ValueError(
                "after_sequence 不能小于 0。"
            )

        with self._lock:
            if job_id not in self._jobs:
                raise ResearchJobNotFoundError(
                    job_id
                )

            return [
                event.model_copy(
                    deep=True
                )
                for event in self._events[job_id]
                if event.sequence > after_sequence
            ]

    def clear(self) -> None:
        """
        清空任务和事件。

        主要供自动化测试使用。
        """

        with self._lock:
            self._jobs.clear()
            self._events.clear()
            self._next_sequence.clear()


def create_job_event_handler(
    store: ResearchJobStore,
    job_id: str,
) -> EventHandler:
    """
    将 DeepResearchAgent 事件写入任务仓库。

    除了保存事件历史，还会同步更新任务进度。
    """

    def handle_event(
        event_type: str,
        message: str,
        data: dict[str, Any],
    ) -> None:
        store.append_event(
            job_id=job_id,
            event_type=event_type,
            message=message,
            data=data,
        )

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
                data.get(
                    "task_count",
                    0,
                )
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
            current_job = store.get(
                job_id
            )

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
                progress=min(
                    progress,
                    85,
                ),
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
                progress=99,
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
    在后台执行一次完整研究任务。
    """

    store.update(
        job_id,
        status=JobStatus.RUNNING,
        stage="initializing",
        message="正在初始化深度研究智能体。",
        progress=1,
        error_message=None,
    )

    store.append_event(
        job_id=job_id,
        event_type="job_started",
        message="后台研究任务开始执行。",
        data={
            "topic": topic,
        },
    )

    event_handler = create_job_event_handler(
        store=store,
        job_id=job_id,
    )

    try:
        agent = agent_factory(
            event_handler
        )

        state = agent.research(
            topic
        )

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

        store.append_event(
            job_id=job_id,
            event_type="job_completed",
            message="后台研究任务执行完成。",
            data={
                "run_id": agent.last_run_id,
                "report_path": report_path,
            },
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
        store.append_event(
            job_id=job_id,
            event_type="job_failed",
            message="后台研究任务执行失败。",
            data={
                "error_type": (
                    type(exc).__name__
                ),
                "error_message": str(exc),
            },
        )

        store.update(
            job_id,
            status=JobStatus.FAILED,
            stage="failed",
            message="深度研究任务执行失败。",
            error_message=str(exc),
        )