from dotenv import load_dotenv

from chapter14.backend.services.search_service import (
    SearchService,
)


def main() -> None:
    """
    使用真实 Tavily API 执行搜索。
    """

    load_dotenv()

    search_service = SearchService(
        max_results=5,
        max_snippet_chars=500,
    )

    query = (
        "Model Context Protocol "
        "architecture overview"
    )

    print("=" * 70)
    print("Deep Research Agent：搜索阶段")
    print("=" * 70)
    print(f"搜索关键词：{query}")
    print()
    print("正在调用 Tavily 搜索……")

    try:
        results = search_service.search(
            query
        )
    except Exception as exc:
        print()
        print("搜索失败。")
        print(
            f"异常类型："
            f"{type(exc).__name__}"
        )
        print(f"异常信息：{exc}")
        raise

    print()
    print(f"共获得 {len(results)} 条结果：")

    for index, result in enumerate(
        results,
        start=1,
    ):
        print()
        print("-" * 70)
        print(f"{index}. {result.title}")
        print(f"来源：{result.url}")
        print(f"摘要：{result.snippet}")

    print()
    print("=" * 70)
    print("搜索完成")
    print("=" * 70)


if __name__ == "__main__":
    main()