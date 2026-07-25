from pydantic import BaseModel, ConfigDict, Field


class ResearchRequest(BaseModel):
    """
    创建深度研究任务时的请求数据。
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    topic: str = Field(
        min_length=1,
        max_length=500,
        description="需要研究的主题",
        examples=[
            "MCP 协议对智能体开发有什么价值？"
        ],
    )


class ResearchResponse(BaseModel):
    """
    深度研究任务完成后的响应数据。
    """

    run_id: str

    topic: str

    status: str

    task_count: int = Field(
        ge=0,
    )

    summary_count: int = Field(
        ge=0,
    )

    report: str

    report_path: str | None = None



from enum import Enum


class JobStatus(str, Enum):
    """
    后台研究任务状态。
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchJobRecord(BaseModel):
    """
    后台研究任务的完整状态记录。
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    job_id: str = Field(
        min_length=1,
    )

    topic: str = Field(
        min_length=1,
    )

    status: JobStatus = JobStatus.QUEUED

    stage: str = "queued"

    message: str = "研究任务已创建，等待执行。"

    progress: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    task_count: int = Field(
        default=0,
        ge=0,
    )

    completed_task_count: int = Field(
        default=0,
        ge=0,
    )

    run_id: str | None = None

    report: str = ""

    report_path: str | None = None

    error_message: str | None = None


class CreateResearchJobResponse(BaseModel):
    """
    创建后台研究任务后的响应。
    """

    job_id: str

    status: JobStatus

    status_url: str


class ResearchJobResponse(ResearchJobRecord):
    """
    查询后台研究任务时返回的数据。
    """

    pass