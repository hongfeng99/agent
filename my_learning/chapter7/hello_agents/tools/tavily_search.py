import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from tavily import TavilyClient

from .base import Tool


load_dotenv()


class TavilySearchTool(Tool):
    """
    Tavily 网络搜索工具。

    用于查询：
    1. 最新信息；
    2. 新闻和公开资料；
    3. 当前版本、日期、政策等可能变化的信息。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_max_results: int = 3,
    ) -> None:
        super().__init__(
            name="tavily_search",
            description=(
                "搜索互联网上的公开信息，适合查询最新或需要外部资料的问题。"
                "参数格式："
                '{"query": "搜索问题", "max_results": 3}。'
                "query 是必填字符串，max_results 是可选整数。"
            ),
        )

        self.api_key = (
            api_key
            or os.getenv("TAVILY_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "未找到 TAVILY_API_KEY，"
                "请检查项目中的 .env 文件。"
            )

        if not isinstance(default_max_results, int):
            raise TypeError(
                "default_max_results 必须是整数。"
            )

        if not 1 <= default_max_results <= 10:
            raise ValueError(
                "default_max_results 必须在 1 到 10 之间。"
            )

        self.default_max_results = default_max_results

        self.client = TavilyClient(
            api_key=self.api_key
        )

    def run(
        self,
        parameters: Dict[str, Any],
    ) -> str:
        """
        执行网络搜索。

        参数示例：

        {
            "query": "Python 最新稳定版本",
            "max_results": 3
        }
        """

        if not isinstance(parameters, dict):
            raise TypeError(
                "parameters 必须是字典。"
            )

        query = parameters.get("query")

        if not isinstance(query, str):
            raise TypeError(
                "query 必须是字符串。"
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "搜索问题 query 不能为空。"
            )

        max_results = parameters.get(
            "max_results",
            self.default_max_results,
        )

        if not isinstance(max_results, int):
            raise TypeError(
                "max_results 必须是整数。"
            )

        if not 1 <= max_results <= 10:
            raise ValueError(
                "max_results 必须在 1 到 10 之间。"
            )

        response = self.client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )

        results = response.get("results", [])

        if not results:
            return "没有搜索到相关结果。"

        formatted_results = []

        for index, item in enumerate(
            results,
            start=1,
        ):
            title = str(
                item.get("title", "未命名结果")
            ).strip()

            content = str(
                item.get("content", "没有摘要")
            ).strip()

            url = str(
                item.get("url", "没有链接")
            ).strip()

            # 防止 Observation 过长。
            if len(content) > 500:
                content = content[:500] + "……"

            formatted_results.append(
                f"{index}. {title}\n"
                f"摘要：{content}\n"
                f"来源：{url}"
            )

        return "\n\n".join(formatted_results)