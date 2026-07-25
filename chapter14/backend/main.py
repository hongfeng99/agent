from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
)

from chapter14.backend.agent import (
    DeepResearchAgent,
)
from chapter14.backend.api_models import (
    ResearchRequest,
    ResearchResponse,
)
from chapter14.backend.dependencies import (
    build_deep_research_agent,
)


app = FastAPI(
    title="Chapter 14 Deep Research Agent",
    description=(
        "基于任务规划、网络搜索、资料总结和报告生成的"
        "自动化深度研究智能体。"
    ),
    version="0.1.0",
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
    summary="执行深度研究任务",
)
def create_research(
    request: ResearchRequest,
    agent: DeepResearchAgent = Depends(
        build_deep_research_agent
    ),
) -> ResearchResponse:
    """
    同步执行一次完整的深度研究任务。

    当前接口会等待规划、搜索、总结和报告生成全部完成后，
    再将最终结果返回给客户端。
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

    run_id = agent.last_run_id

    if not run_id:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="研究任务完成，但没有生成运行编号。",
        )

    report_path = None

    if agent.last_report_path is not None:
        report_path = str(
            agent.last_report_path
        )

    return ResearchResponse(
        run_id=run_id,
        topic=state.topic,
        status=state.status.value,
        task_count=len(state.tasks),
        summary_count=len(state.summaries),
        report=state.final_report,
        report_path=report_path,
    )