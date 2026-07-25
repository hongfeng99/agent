from datetime import date
from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
)

PLANNER_SYSTEM_PROMPT = """
你是一名专业的深度研究规划专家。

你的职责是：

1. 理解用户提出的研究主题；
2. 将复杂主题拆分成多个清晰、独立的研究子任务；
3. 为每个子任务设计适合搜索引擎使用的检索语句；
4. 只输出符合要求的 JSON 数组；
5. 不直接回答研究问题。
""".strip()


def build_planning_prompt(
    topic: str,
    current_date: date | None = None,
    min_tasks: int = 3,
    max_tasks: int = 5,
) -> str:
    """
    根据研究主题构建任务规划提示词。

    参数：
        topic:
            用户输入的研究主题。

        current_date:
            当前日期。默认使用程序运行当天的日期。

        min_tasks:
            最少生成的研究子任务数量。

        max_tasks:
            最多生成的研究子任务数量。

    返回：
        可以发送给大模型的规划提示词。
    """

    if not isinstance(topic, str):
        raise TypeError(
            "topic 必须是字符串，"
            f"实际类型为：{type(topic).__name__}"
        )

    topic = topic.strip()

    if not topic:
        raise ValueError("研究主题不能为空。")

    if min_tasks < 1:
        raise ValueError("min_tasks 必须大于等于 1。")

    if max_tasks < min_tasks:
        raise ValueError(
            "max_tasks 不能小于 min_tasks。"
        )

    effective_date = current_date or date.today()

    return f"""
请为下面的研究主题制定一份深度研究计划。

当前日期：
{effective_date.isoformat()}

研究主题：
{topic}

请将研究主题拆分为 {min_tasks}～{max_tasks} 个子任务。

每个子任务必须包含：

1. title：
   简洁明确的任务标题。

2. intent：
   说明这个子任务要解决什么问题，以及它为什么重要。

3. query：
   可以直接提交给搜索引擎的检索语句。
   query 应当具体、准确，并根据主题需要加入时间、机构、
   技术名称或其他限定词。

规划要求：

1. 子任务之间不能明显重复；
2. 子任务应当共同覆盖研究主题的主要方面；
3. 子任务应当按照合理顺序排列；
4. 优先采用“基本概念 → 核心机制 → 实际应用 →
   对比分析 → 最新趋势”的逻辑；
5. 对于需要最新资料的问题，应当在 query 中体现时间要求；
6. 必须生成至少 {min_tasks} 个且最多 {max_tasks} 个子任务；
7. 只返回 JSON 数组；
8. 不要使用 Markdown 代码块；
9. 不要在 JSON 前后添加解释。

返回格式：

[
  {{
    "title": "子任务标题",
    "intent": "该子任务的研究目的",
    "query": "可以直接执行的搜索语句"
  }},
  {{
    "title": "另一个子任务标题",
    "intent": "该子任务的研究目的",
    "query": "另一个搜索语句"
  }}
]
""".strip()



SUMMARIZER_SYSTEM_PROMPT = """
你是一名严谨的研究资料分析专家。

你的职责是：

1. 根据给定的研究任务和搜索资料生成研究总结；
2. 只使用提供的搜索资料，不得编造事实；
3. 合并多个来源中的重复信息；
4. 保留重要的概念、数据、时间和机构名称；
5. 使用来源编号标记信息出处；
6. 当资料不足时，明确说明证据不足；
7. 输出结构清晰的 Markdown 内容。
""".strip()


def build_summarization_prompt(
    task: ResearchTask,
    search_results: list[SearchResult],
) -> str:
    """
    根据研究任务和搜索结果构建总结提示词。

    参数：
        task:
            当前需要总结的研究子任务。

        search_results:
            搜索服务返回的资料列表。

    返回：
        可以发送给大模型的总结提示词。
    """

    if not search_results:
        raise ValueError(
            "搜索结果不能为空，无法生成任务总结。"
        )

    formatted_sources: list[str] = []

    for index, result in enumerate(
        search_results,
        start=1,
    ):
        snippet = (
            result.snippet
            or "该来源没有提供摘要。"
        )

        formatted_sources.append(
            f"""
[{index}]
标题：{result.title}
URL：{result.url}
内容：
{snippet}
""".strip()
        )

    sources_text = "\n\n".join(
        formatted_sources
    )

    return f"""
请根据下面的研究任务和搜索资料生成研究总结。

研究任务标题：
{task.title}

研究目的：
{task.intent}

搜索关键词：
{task.query}

搜索资料：
{sources_text}

总结要求：

1. 直接回答研究目的所提出的问题；
2. 只使用上面提供的搜索资料；
3. 不得补充资料中没有出现的事实；
4. 对重要结论使用 [1]、[2] 等来源编号；
5. 同一个结论可以同时引用多个来源，例如 [1][3]；
6. 合并重复信息，不要逐条机械复述搜索结果；
7. 对来源之间存在的差异或冲突进行说明；
8. 资料不足时明确写出“现有资料不足以确认”；
9. 使用 Markdown 格式；
10. 不要输出 JSON；
11. 不要单独重复列出完整 URL；
12. 输出内容应包含以下结构：

## 核心结论

用一段话概括本任务最重要的结论。

## 详细分析

按照合理逻辑展开分析，并添加来源编号。

## 局限性

说明当前资料存在的不足、时效性或证据限制。
""".strip()