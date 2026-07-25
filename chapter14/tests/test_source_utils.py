import pytest

from chapter14.backend.models import SearchResult
from chapter14.backend.utils.source_utils import (
    deduplicate_results,
    normalize_url,
    truncate_text,
)


def test_truncate_text_keeps_short_text() -> None:
    """
    未超过长度限制的文本不应该被截断。
    """

    result = truncate_text(
        "这是一段简短文本。",
        max_chars=20,
    )

    assert result == "这是一段简短文本。"


def test_truncate_text_limits_long_text() -> None:
    """
    超过限制的文本应该被截断。
    """

    result = truncate_text(
        "abcdefghijk",
        max_chars=8,
    )

    assert result == "abcde..."
    assert len(result) == 8


def test_truncate_text_strips_whitespace() -> None:
    """
    文本首尾空格应该被删除。
    """

    result = truncate_text(
        "  测试文本  ",
        max_chars=20,
    )

    assert result == "测试文本"


def test_truncate_text_rejects_small_limit() -> None:
    """
    max_chars 小于 4 时应该抛出异常。
    """

    with pytest.raises(
        ValueError,
        match="max_chars 必须大于等于 4",
    ):
        truncate_text(
            "测试文本",
            max_chars=3,
        )


def test_normalize_url() -> None:
    """
    验证 URL 标准化。
    """

    result = normalize_url(
        " HTTPS://Example.COM/path/#section "
    )

    assert result == (
        "https://example.com/path"
    )


def test_normalize_url_preserves_query() -> None:
    """
    URL 查询参数应该被保留。
    """

    result = normalize_url(
        "https://example.com/search?q=mcp"
    )

    assert result == (
        "https://example.com/search?q=mcp"
    )


def test_deduplicate_results() -> None:
    """
    验证重复 URL 会被去除。
    """

    results = [
        SearchResult(
            title="结果一",
            url="https://example.com/mcp",
            snippet="摘要一",
        ),
        SearchResult(
            title="结果一的重复项",
            url="https://example.com/mcp/",
            snippet="摘要二",
        ),
        SearchResult(
            title="结果二",
            url="https://example.org/agent",
            snippet="摘要三",
        ),
    ]

    unique_results = deduplicate_results(
        results
    )

    assert len(unique_results) == 2
    assert unique_results[0].title == "结果一"
    assert unique_results[1].title == "结果二"


def test_deduplicate_results_preserves_order() -> None:
    """
    去重后应当保持原始结果顺序。
    """

    results = [
        SearchResult(
            title="A",
            url="https://example.com/a",
        ),
        SearchResult(
            title="B",
            url="https://example.com/b",
        ),
        SearchResult(
            title="重复 A",
            url="https://example.com/a/",
        ),
    ]

    unique_results = deduplicate_results(
        results
    )

    assert [
        item.title
        for item in unique_results
    ] == ["A", "B"]