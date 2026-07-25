from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    status,
)

from chapter14.backend.agent import (
    DeepResearchAgent,
)
from chapter14.backend.api_models import (
    CreateResearchJobResponse,
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