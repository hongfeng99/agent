from collections.abc import Callable

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.agent import (
    DeepResearchAgent,
    EventHandler,
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
from chapter14.backend.task_manager import (
    ResearchJobStore,
)


AgentFactory = Callable[
    [EventHandler | None],
    DeepResearchAgent,
]


def create_deep_research_agent(
    event_handler: EventHandler | None = None,
) -> DeepResearchAgent:
    """
    创建完整的 DeepResearchAgent。

    event_handler 用于接收 Agent 运行事件，
    后台任务状态和后续 SSE 都会使用它。
    """

    load_dotenv()

    llm = HelloAgentsLLM()

    planner = PlanningService(
        llm=llm,
        min_tasks=3,
        max_tasks=5,
    )

    searcher = SearchService(
        max_results=5,
        max_snippet_chars=1200,
    )

    summarizer = SummarizationService(
        llm=llm,
    )

    reporter = ReportingService(
        llm=llm,
    )

    return DeepResearchAgent(
        planner=planner,
        searcher=searcher,
        summarizer=summarizer,
        reporter=reporter,
        event_handler=event_handler,
    )


def build_deep_research_agent() -> DeepResearchAgent:
    """
    为同步 /research 接口创建 Agent。
    """

    return create_deep_research_agent()


def get_agent_factory() -> AgentFactory:
    """
    返回后台任务使用的 Agent 工厂函数。
    """

    return create_deep_research_agent


_job_store = ResearchJobStore()


def get_research_job_store() -> ResearchJobStore:
    """
    返回全局后台任务状态仓库。
    """

    return _job_store