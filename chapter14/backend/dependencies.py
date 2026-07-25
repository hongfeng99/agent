from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

from chapter14.backend.agent import (
    DeepResearchAgent,
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


def build_deep_research_agent() -> DeepResearchAgent:
    """
    创建一套完整的 DeepResearchAgent 及其依赖服务。

    FastAPI 会通过 Depends 调用这个函数。
    测试时可以替换这个依赖，避免调用真实模型和搜索接口。
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
    )