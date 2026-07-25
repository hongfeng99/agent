from hello_agents import HelloAgentsLLM

from chapter14.backend.models import ResearchTask
from chapter14.backend.prompts import (
    PLANNER_SYSTEM_PROMPT,
    build_planning_prompt,
)
from chapter14.backend.utils.json_parser import (
    parse_research_tasks,
)


class PlanningService:
    """
    深度研究任务规划服务。

    负责：

    1. 根据研究主题构建规划提示词；
    2. 调用大模型；
    3. 解析大模型返回的 JSON；
    4. 转换成 ResearchTask 列表；
    5. 验证任务数量和重复情况。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
        min_tasks: int = 3,
        max_tasks: int = 5,
    ) -> None:
        """
        初始化规划服务。
        """

        if min_tasks < 1:
            raise ValueError(
                "min_tasks 必须大于等于 1。"
            )

        if max_tasks < min_tasks:
            raise ValueError(
                "max_tasks 不能小于 min_tasks。"
            )

        self._llm = llm
        self._min_tasks = min_tasks
        self._max_tasks = max_tasks

    def plan(
        self,
        topic: str,
    ) -> list[ResearchTask]:
        """
        根据研究主题生成研究子任务。
        """

        planning_prompt = build_planning_prompt(
            topic=topic,
            min_tasks=self._min_tasks,
            max_tasks=self._max_tasks,
        )

        messages = [
            {
                "role": "system",
                "content": PLANNER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": planning_prompt,
            },
        ]

        try:
            response_text = self._llm.invoke(
                messages,
            )
        except Exception as exc:
            raise RuntimeError(
                "调用研究规划模型失败。"
            ) from exc

        if not isinstance(response_text, str):
            raise TypeError(
                "规划模型应当返回字符串，"
                f"实际类型为："
                f"{type(response_text).__name__}"
            )

        tasks = parse_research_tasks(
            response_text
        )

        self._validate_task_count(tasks)
        self._validate_duplicate_tasks(tasks)

        return tasks

    def _validate_task_count(
        self,
        tasks: list[ResearchTask],
    ) -> None:
        """
        验证研究子任务数量。
        """

        task_count = len(tasks)

        if not (
            self._min_tasks
            <= task_count
            <= self._max_tasks
        ):
            raise ValueError(
                "研究子任务数量不符合要求："
                f"要求 {self._min_tasks}～"
                f"{self._max_tasks} 个，"
                f"实际得到 {task_count} 个。"
            )

    @staticmethod
    def _validate_duplicate_tasks(
        tasks: list[ResearchTask],
    ) -> None:
        """
        验证任务标题和搜索语句是否重复。
        """

        seen_titles: set[str] = set()
        seen_queries: set[str] = set()

        for task in tasks:
            normalized_title = (
                task.title.strip().casefold()
            )
            normalized_query = (
                task.query.strip().casefold()
            )

            if normalized_title in seen_titles:
                raise ValueError(
                    "研究计划中存在重复标题："
                    f"{task.title}"
                )

            if normalized_query in seen_queries:
                raise ValueError(
                    "研究计划中存在重复搜索语句："
                    f"{task.query}"
                )

            seen_titles.add(normalized_title)
            seen_queries.add(normalized_query)