from datetime import date

from chapter14.backend.models import (
    ResearchTask,
    SearchResult,
    TaskSummary,
)
from chapter14.backend.utils.source_utils import (
    normalize_url,
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





REPORTER_SYSTEM_PROMPT = """
你是一名严谨的深度研究报告撰写专家。

你的职责是：

1. 根据多个研究子任务的总结撰写完整报告；
2. 综合不同子任务中的信息，而不是简单拼接；
3. 只使用提供的研究总结和资料来源；
4. 不得编造资料中没有出现的事实；
5. 使用统一的全局来源编号；
6. 明确区分事实、分析和推断；
7. 输出结构清晰的 Markdown 研究报告。
""".strip()


def build_reporting_prompt(
    topic: str,
    summaries: list[TaskSummary],
) -> str:
    """
    根据多个子任务总结构建最终报告提示词。

    该函数会：

    1. 整理所有子任务总结；
    2. 对所有来源 URL 去重；
    3. 为来源分配统一的全局编号；
    4. 建立任务内部来源编号与全局编号的对应关系；
    5. 构建最终报告生成提示词。
    """

    if not isinstance(topic, str):
        raise TypeError(
            "topic 必须是字符串，"
            f"实际类型为：{type(topic).__name__}"
        )

    cleaned_topic = topic.strip()

    if not cleaned_topic:
        raise ValueError(
            "研究主题不能为空。"
        )

    if not summaries:
        raise ValueError(
            "子任务总结不能为空，无法生成最终报告。"
        )

    global_sources: list[SearchResult] = []

    # 标准化 URL -> 全局来源编号
    source_number_map: dict[str, int] = {}

    formatted_task_sections: list[str] = []

    for summary_index, task_summary in enumerate(
        summaries,
        start=1,
    ):
        if not isinstance(
            task_summary,
            TaskSummary,
        ):
            raise TypeError(
                "summaries 中的元素必须是 TaskSummary，"
                f"第 {summary_index} 个元素实际类型为："
                f"{type(task_summary).__name__}"
            )

        local_to_global_lines: list[str] = []

        for local_index, source in enumerate(
            task_summary.sources,
            start=1,
        ):
            normalized_url = normalize_url(
                source.url
            )

            source_key = (
                normalized_url
                or source.url.strip()
            )

            if source_key not in source_number_map:
                global_sources.append(source)

                source_number_map[source_key] = (
                    len(global_sources)
                )

            global_number = source_number_map[
                source_key
            ]

            local_to_global_lines.append(
                f"- 任务内来源 [{local_index}] "
                f"对应全局来源 [{global_number}]"
            )

        if local_to_global_lines:
            source_mapping_text = "\n".join(
                local_to_global_lines
            )
        else:
            source_mapping_text = (
                "- 当前子任务没有可用来源"
            )

        task = task_summary.task

        formatted_task_sections.append(
            f"""
### 子任务 {task.id}：{task.title}

研究目的：
{task.intent}

搜索语句：
{task.query}

子任务总结：
{task_summary.summary}

来源编号对应关系：
{source_mapping_text}
""".strip()
        )

    formatted_global_sources: list[str] = []

    for global_number, source in enumerate(
        global_sources,
        start=1,
    ):
        snippet = (
            source.snippet
            or "该来源没有提供摘要。"
        )

        formatted_global_sources.append(
            f"""
[{global_number}]
标题：{source.title}
URL：{source.url}
摘要：
{snippet}
""".strip()
        )

    task_sections_text = "\n\n".join(
        formatted_task_sections
    )

    global_sources_text = "\n\n".join(
        formatted_global_sources
    )

    return f"""
请根据下面的研究主题、子任务总结和全局来源列表，
生成一份完整的 Markdown 深度研究报告。

研究主题：
{cleaned_topic}

以下是已经完成的子任务总结：

{task_sections_text}

以下是去重后的全局来源列表：

{global_sources_text}

报告要求：

1. 只使用上面提供的子任务总结和资料来源；
2. 不得添加现有资料中没有出现的事实；
3. 正文引用必须使用全局来源编号，例如 [1]、[2]；
4. 不要继续使用子任务内部的局部来源编号；
5. 同一结论由多个来源支持时，可以写成 [1][3]；
6. 应当综合多个子任务，而不是机械拼接原始总结；
7. 删除重复观点；
8. 对不同来源之间的差异或冲突进行说明；
9. 推断性内容必须明确写成“基于现有资料可以推断”；
10. 资料不足时明确写出“现有资料不足以确认”；
11. 不要输出 JSON；
12. 不要使用 Markdown 代码块包裹整篇报告；
13. 参考资料中的编号必须与正文编号一致；
14. 参考资料不得包含全局来源列表之外的 URL。

报告必须使用以下结构：

# {cleaned_topic}

## 摘要

简要介绍研究问题、研究范围和主要结论。

## 研究背景

说明该主题的基本背景及研究意义。

## 主要发现

按照合理逻辑划分三级标题，综合分析各个研究子任务。

## 综合分析

说明不同子任务之间的联系、共同结论和重要差异。

## 局限性

说明资料覆盖范围、来源质量、时效性以及证据限制。

## 结论

概括本次研究得出的核心结论。

## 参考资料

使用下面的格式列出所有在正文中实际引用的资料：

[1] [来源标题](来源 URL)
[2] [来源标题](来源 URL)
""".strip()