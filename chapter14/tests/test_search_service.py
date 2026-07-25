from typing import Any

import pytest
import requests

from chapter14.backend.services.search_service import (
    SearchService,
)


class FakeResponse:
    """
    模拟 requests.Response。
    """

    def __init__(
        self,
        response_data: Any = None,
        http_error: Exception | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self.response_data = response_data
        self.http_error = http_error
        self.json_error = json_error

    def raise_for_status(self) -> None:
        """
        模拟 HTTP 状态检查。
        """

        if self.http_error is not None:
            raise self.http_error

    def json(self) -> Any:
        """
        模拟 JSON 响应解析。
        """

        if self.json_error is not None:
            raise self.json_error

        return self.response_data


class FakeSession:
    """
    模拟 requests.Session。
    """

    def __init__(
        self,
        response: FakeResponse,
    ) -> None:
        self.response = response
        self.called_url = ""
        self.called_json: dict[str, Any] = {}
        self.called_timeout: float | None = None

    def post(
        self,
        url: str,
        json: dict[str, Any],
        timeout: float,
    ) -> FakeResponse:
        """
        模拟 HTTP POST 请求。
        """

        self.called_url = url
        self.called_json = json
        self.called_timeout = timeout

        return self.response


def test_search_service_returns_results() -> None:
    """
    验证搜索服务能够解析正常结果。
    """

    response = FakeResponse(
        response_data={
            "results": [
                {
                    "title": "MCP Introduction",
                    "url": (
                        "https://example.com/mcp"
                    ),
                    "content": (
                        "MCP 是一种连接模型、"
                        "数据和工具的协议。"
                    ),
                },
                {
                    "title": "MCP Architecture",
                    "url": (
                        "https://example.org/"
                        "architecture"
                    ),
                    "content": (
                        "MCP 包含 Host、Client "
                        "和 Server。"
                    ),
                },
            ]
        }
    )

    fake_session = FakeSession(response)

    service = SearchService(
        api_key="test-api-key",
        session=fake_session,  # type: ignore[arg-type]
    )

    results = service.search(
        "Model Context Protocol"
    )

    assert len(results) == 2

    assert (
        results[0].title
        == "MCP Introduction"
    )

    assert (
        results[0].url
        == "https://example.com/mcp"
    )

    assert (
        fake_session.called_url
        == SearchService.API_URL
    )

    assert (
        fake_session.called_json["query"]
        == "Model Context Protocol"
    )

    assert (
        fake_session.called_json["api_key"]
        == "test-api-key"
    )


def test_search_service_removes_duplicates() -> None:
    """
    验证重复 URL 会被去除。
    """

    response = FakeResponse(
        response_data={
            "results": [
                {
                    "title": "结果一",
                    "url": "https://example.com/a",
                    "content": "摘要一",
                },
                {
                    "title": "重复结果",
                    "url": "https://example.com/a/",
                    "content": "摘要二",
                },
                {
                    "title": "结果二",
                    "url": "https://example.com/b",
                    "content": "摘要三",
                },
            ]
        }
    )

    service = SearchService(
        api_key="test-api-key",
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    results = service.search(
        "测试关键词"
    )

    assert len(results) == 2
    assert results[0].title == "结果一"
    assert results[1].title == "结果二"


def test_search_service_skips_invalid_items() -> None:
    """
    缺少标题或 URL 的结果应该被跳过。
    """

    response = FakeResponse(
        response_data={
            "results": [
                {
                    "title": "",
                    "url": "https://example.com/a",
                    "content": "没有标题",
                },
                {
                    "title": "没有 URL",
                    "url": "",
                    "content": "没有 URL",
                },
                {
                    "title": "有效结果",
                    "url": "https://example.com/c",
                    "content": "有效摘要",
                },
            ]
        }
    )

    service = SearchService(
        api_key="test-api-key",
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    results = service.search(
        "测试关键词"
    )

    assert len(results) == 1
    assert results[0].title == "有效结果"


def test_search_service_truncates_snippet() -> None:
    """
    过长摘要应该被截断。
    """

    response = FakeResponse(
        response_data={
            "results": [
                {
                    "title": "测试结果",
                    "url": "https://example.com",
                    "content": "abcdefghijk",
                }
            ]
        }
    )

    service = SearchService(
        api_key="test-api-key",
        max_snippet_chars=8,
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    results = service.search(
        "测试关键词"
    )

    assert results[0].snippet == "abcde..."
    assert len(results[0].snippet) == 8


def test_search_service_rejects_empty_query() -> None:
    """
    空搜索关键词应该被拒绝。
    """

    service = SearchService(
        api_key="test-api-key",
    )

    with pytest.raises(
        ValueError,
        match="搜索关键词不能为空",
    ):
        service.search("   ")


def test_search_service_rejects_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    未配置 API Key 时应该抛出异常。
    """

    monkeypatch.delenv(
        "TAVILY_API_KEY",
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="没有找到 Tavily API Key",
    ):
        SearchService()


def test_search_service_wraps_http_error() -> None:
    """
    HTTP 请求异常应该被转换成 RuntimeError。
    """

    response = FakeResponse(
        http_error=requests.HTTPError(
            "模拟 HTTP 错误"
        )
    )

    service = SearchService(
        api_key="test-api-key",
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Tavily 搜索请求失败",
    ):
        service.search("测试关键词")


def test_search_service_rejects_invalid_json() -> None:
    """
    返回内容不是合法 JSON 时应该抛出异常。
    """

    response = FakeResponse(
        json_error=ValueError(
            "模拟 JSON 解析错误"
        )
    )

    service = SearchService(
        api_key="test-api-key",
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="不是合法 JSON",
    ):
        service.search("测试关键词")


def test_search_service_rejects_invalid_results_field() -> None:
    """
    results 字段不是列表时应该抛出异常。
    """

    response = FakeResponse(
        response_data={
            "results": "错误的结果类型"
        }
    )

    service = SearchService(
        api_key="test-api-key",
        session=FakeSession(  # type: ignore[arg-type]
            response
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="results 字段必须是列表",
    ):
        service.search("测试关键词")