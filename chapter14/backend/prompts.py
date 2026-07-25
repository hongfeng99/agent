from datetime import date


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