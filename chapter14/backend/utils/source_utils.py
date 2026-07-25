from urllib.parse import urlsplit, urlunsplit

from chapter14.backend.models import SearchResult


def truncate_text(
    text: str,
    max_chars: int = 2000,
) -> str:
    """
    将文本限制在指定字符数以内。

    如果文本长度没有超过限制，直接返回原文本；
    如果超过限制，则截断并在末尾添加省略号。
    """

    if not isinstance(text, str):
        raise TypeError(
            "text 必须是字符串，"
            f"实际类型为：{type(text).__name__}"
        )

    if max_chars < 4:
        raise ValueError(
            "max_chars 必须大于等于 4。"
        )

    cleaned_text = text.strip()

    if len(cleaned_text) <= max_chars:
        return cleaned_text

    return cleaned_text[: max_chars - 3] + "..."


def normalize_url(url: str) -> str:
    """
    对 URL 进行基础标准化。

    处理内容：

    1. 去除首尾空格；
    2. scheme 和域名转换为小写；
    3. 去除 URL 中的锚点；
    4. 去除路径末尾多余的斜杠。

    该函数主要用于判断两个搜索结果是否来自同一个 URL。
    """

    if not isinstance(url, str):
        raise TypeError(
            "url 必须是字符串，"
            f"实际类型为：{type(url).__name__}"
        )

    cleaned_url = url.strip()

    if not cleaned_url:
        return ""

    parts = urlsplit(cleaned_url)

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    path = parts.path

    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            parts.query,
            "",
        )
    )


def deduplicate_results(
    results: list[SearchResult],
) -> list[SearchResult]:
    """
    根据标准化后的 URL 对搜索结果去重。

    保留第一次出现的结果。
    """

    unique_results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for result in results:
        normalized_url = normalize_url(
            result.url
        )

        if not normalized_url:
            continue

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)
        unique_results.append(result)

    return unique_results