import asyncio
import json
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from chapter14.backend.agent import (
    DeepResearchAgent,
)
from chapter14.backend.api_models import (
    CreateResearchJobResponse,
    JobStatus,
    ResearchEvent,
    ResearchJobResponse,
    ResearchRequest,
    ResearchResponse,
)
from chapter14.backend.dependencies import (
    AgentFactory,
    build_deep_research_agent,
    get_agent_factory,
    get_research_job_store,
)
from chapter14.backend.task_manager import (
    ResearchJobNotFoundError,
    ResearchJobStore,
    execute_research_job,
)


app = FastAPI(
    title="Chapter 14 Deep Research Agent",
    description=(
        "基于任务规划、网络搜索、资料总结和报告生成的"
        "自动化深度研究智能体。"
    ),
    version="0.2.0",
)


@app.get(
    "/health",
    summary="服务健康检查",
)
def health_check() -> dict[str, str]:
    """
    检查 FastAPI 服务是否正常运行。
    """

    return {
        "status": "ok",
        "service": "deep-research-agent",
    }


@app.post(
    "/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="同步执行深度研究任务",
)
def create_research(
    request: ResearchRequest,
    agent: DeepResearchAgent = Depends(
        build_deep_research_agent
    ),
) -> ResearchResponse:
    """
    同步执行完整研究流程。

    该接口会等待全部研究完成后再返回。
    """

    try:
        state = agent.research(
            request.topic
        )
    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "深度研究任务执行失败："
                f"{exc}"
            ),
        ) from exc

    if not agent.last_run_id:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="研究完成，但没有生成运行编号。",
        )

    report_path = None

    if agent.last_report_path is not None:
        report_path = str(
            agent.last_report_path
        )

    return ResearchResponse(
        run_id=agent.last_run_id,
        topic=state.topic,
        status=state.status.value,
        task_count=len(state.tasks),
        summary_count=len(state.summaries),
        report=state.final_report,
        report_path=report_path,
    )


@app.post(
    "/research/tasks",
    response_model=CreateResearchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建后台深度研究任务",
)
def create_background_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    store: ResearchJobStore = Depends(
        get_research_job_store
    ),
    agent_factory: AgentFactory = Depends(
        get_agent_factory
    ),
) -> CreateResearchJobResponse:
    """
    创建后台研究任务并立即返回 job_id。
    """

    job = store.create(
        request.topic
    )

    background_tasks.add_task(
        execute_research_job,
        job.job_id,
        request.topic,
        store,
        agent_factory,
    )

    return CreateResearchJobResponse(
        job_id=job.job_id,
        status=job.status,
        status_url=(
            f"/research/tasks/{job.job_id}"
        ),
    )


@app.get(
    "/research/tasks/{job_id}",
    response_model=ResearchJobResponse,
    summary="查询后台研究任务状态",
)
def get_background_research(
    job_id: str,
    store: ResearchJobStore = Depends(
        get_research_job_store
    ),
) -> ResearchJobResponse:
    """
    查询后台研究任务的进度、状态和最终报告。
    """

    try:
        job = store.get(job_id)
    except ResearchJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有找到指定的研究任务。",
        ) from exc

    return ResearchJobResponse.model_validate(
        job.model_dump()
    )





def format_sse_event(
    event: ResearchEvent,
) -> str:
    """
    将 ResearchEvent 转换为 SSE 文本格式。
    """

    payload = {
        "sequence": event.sequence,
        "job_id": event.job_id,
        "message": event.message,
        "data": event.data,
        "created_at": (
            event.created_at.isoformat()
        ),
    }

    payload_text = json.dumps(
        payload,
        ensure_ascii=False,
    )

    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {payload_text}\n\n"
    )


async def generate_research_events(
    job_id: str,
    request: Request,
    store: ResearchJobStore,
    after_sequence: int,
):
    """
    持续读取任务事件并输出 SSE 数据。

    当任务完成、失败或客户端断开连接时结束。
    """

    current_sequence = after_sequence

    while True:
        if await request.is_disconnected():
            return

        events = store.get_events(
            job_id=job_id,
            after_sequence=current_sequence,
        )

        for event in events:
            current_sequence = (
                event.sequence
            )

            yield format_sse_event(
                event
            )

        job = store.get(
            job_id
        )

        terminal_statuses = {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
        }

        if (
            job.status in terminal_statuses
            and not events
        ):
            return

        await asyncio.sleep(0.5)


@app.get(
    "/research/tasks/{job_id}/events",
    summary="订阅后台研究任务事件",
)
async def stream_background_research_events(
    job_id: str,
    request: Request,
    after: int = Query(
        default=0,
        ge=0,
        description="只返回该事件序号之后的事件",
    ),
    last_event_id: str | None = Header(
        default=None,
        alias="Last-Event-ID",
    ),
    store: ResearchJobStore = Depends(
        get_research_job_store
    ),
) -> StreamingResponse:
    """
    通过 Server-Sent Events 实时推送研究进度。

    浏览器断线重连时，可以通过 Last-Event-ID
    从上一次收到的事件之后继续获取。
    """

    try:
        store.get(job_id)
    except ResearchJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有找到指定的研究任务。",
        ) from exc

    after_sequence = after

    if last_event_id is not None:
        try:
            header_sequence = int(
                last_event_id
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Last-Event-ID 必须是整数。"
                ),
            ) from exc

        after_sequence = max(
            after_sequence,
            header_sequence,
        )

    return StreamingResponse(
        generate_research_events(
            job_id=job_id,
            request=request,
            store=store,
            after_sequence=after_sequence,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )