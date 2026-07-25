from enum import Enum

from pydantic import BaseModel,ConfigDict,Field

class TaskStatus(str,Enum):
    """
    干个研究子任务的执行状态。
    """
    

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"



class ResearchStatus(str,Enum):
    """
    整个研究任务的执行状态。
    """

    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"



class ResearchTask(BaseModel):
    """
    研究规划阶段生成的单个子任务。

    id:
        子任务编号，从 1 开始。

    title:
        子任务标题。

    intent:
        该子任务希望解决的问题。

    query:
        用于搜索资料的关键词。

    status:
        当前执行状态。
    """
        
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(
        ge=1,
        description="子任务编号，从 1 开始",
    )

    title: str = Field(
        min_length=1,
        description="子任务标题",
    )

    intent: str = Field(
        min_length=1,
        description="子任务的研究目的",
    )

    query: str = Field(
        min_length=1,
        description="用于检索资料的搜索关键词",
    )

    status: TaskStatus = TaskStatus.PENDING



class SearchResult(BaseModel):
    """
    搜索工具返回的单条搜索结果。
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=1,
        description="搜索结果标题",
    )

    url: str = Field(
        min_length=1,
        description="搜索结果链接",
    )

    snippet: str = Field(
        default="",
        description="搜索结果摘要",
    )



class TaskSummary(BaseModel):
    """
    单个研究子任务的总结结果。
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    task: ResearchTask

    summary: str = Field(
        min_length=1,
        description="根据搜索资料生成的任务总结",
    )

    sources: list[SearchResult] = Field(
        default_factory=list,
        description="生成总结时使用的资料来源",
    )




class ResearchState(BaseModel):
    """
    完整研究任务在运行过程中的状态。
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(
        min_length=1,
        description="用户输入的研究主题",
    )

    tasks: list[ResearchTask] = Field(
        default_factory=list,
        description="规划阶段生成的研究子任务",
    )

    summaries: list[TaskSummary] = Field(
        default_factory=list,
        description="已经完成的子任务总结",
    )

    final_report: str = Field(
        default="",
        description="最终生成的 Markdown 报告",
    )

    status: ResearchStatus = ResearchStatus.CREATED

    error_message: str | None = Field(
        default=None,
        description="研究失败时记录的错误信息",
    )