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