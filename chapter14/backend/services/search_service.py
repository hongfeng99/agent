import os
from typing import Any

import requests

from chapter14.backend.models import SearchResult
from chapter14.backend.utils.source_utils import (
    deduplicate_results,
    truncate_text,
)


class SearchService:
    """
    Tavily 搜索服务。

    负责：

    1. 接收搜索关键词；
    2. 调用 Tavily Search API；
    3. 解析搜索结果；
    4. 转换为 SearchResult；
    5. 对 URL 去重；
    6. 限制摘要长度。
    """

    API_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str | None = None,
        max_results: int = 5,
        max_snippet_chars: int = 1500,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        """
        初始化搜索服务。

        参数：
            api_key:
                Tavily API Key。未传入时从环境变量
                TAVILY_API_KEY 读取。

            max_results:
                最多返回多少条搜索结果。

            max_snippet_chars:
                每条搜索结果摘要的最大字符数。

            timeout:
                HTTP 请求超时时间。

            session:
                requests.Session 实例。
                单元测试时可以传入假 Session。
        """

        resolved_api_key = (
            api_key
            or os.getenv("TAVILY_API_KEY", "")
        ).strip()

        if not resolved_api_key:
            raise ValueError(
                "没有找到 Tavily API Key。"
                "请传入 api_key，或设置环境变量 "
                "TAVILY_API_KEY。"
            )

        if max_results < 1:
            raise ValueError(
                "max_results 必须大于等于 1。"
            )

        if max_snippet_chars < 4:
            raise ValueError(
                "max_snippet_chars 必须大于等于 4。"
            )

        if timeout <= 0:
            raise ValueError(
                "timeout 必须大于 0。"
            )

        self._api_key = resolved_api_key
        self._max_results = max_results
        self._max_snippet_chars = (
            max_snippet_chars
        )
        self._timeout = timeout
        self._session = (
            session
            or requests.Session()
        )

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:
        """
        根据搜索关键词执行 Tavily 搜索。

        参数：
            query:
                可以直接交给搜索引擎的检索语句。

        返回：
            经过清洗、截断和去重的搜索结果列表。
        """

        if not isinstance(query, str):
            raise TypeError(
                "query 必须是字符串，"
                f"实际类型为：{type(query).__name__}"
            )

        cleaned_query = query.strip()

        if not cleaned_query:
            raise ValueError(
                "搜索关键词不能为空。"
            )

        payload = {
            "api_key": self._api_key,
            "query": cleaned_query,
            "search_depth": "advanced",
            "max_results": self._max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            response = self._session.post(
                self.API_URL,
                json=payload,
                timeout=self._timeout,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Tavily 搜索请求失败：{cleaned_query}"
            ) from exc

        try:
            response_data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Tavily 返回的内容不是合法 JSON。"
            ) from exc

        return self._parse_results(
            response_data
        )

    def _parse_results(
        self,
        response_data: Any,
    ) -> list[SearchResult]:
        """
        解析 Tavily 的原始响应数据。
        """

        if not isinstance(
            response_data,
            dict,
        ):
            raise RuntimeError(
                "Tavily 返回结果必须是 JSON 对象。"
            )

        raw_results = response_data.get(
            "results",
            [],
        )

        if not isinstance(raw_results, list):
            raise RuntimeError(
                "Tavily 返回结果中的 results "
                "字段必须是列表。"
            )

        parsed_results: list[
            SearchResult
        ] = []

        for raw_result in raw_results:
            if not isinstance(
                raw_result,
                dict,
            ):
                continue

            title = str(
                raw_result.get(
                    "title",
                    "",
                )
            ).strip()

            url = str(
                raw_result.get(
                    "url",
                    "",
                )
            ).strip()

            snippet_value = (
                raw_result.get("content")
                or raw_result.get("snippet")
                or ""
            )

            snippet = truncate_text(
                str(snippet_value),
                max_chars=(
                    self._max_snippet_chars
                ),
            )

            if not title or not url:
                continue

            parsed_results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                )
            )

        unique_results = (
            deduplicate_results(
                parsed_results
            )
        )

        return unique_results[
            : self._max_results
        ]