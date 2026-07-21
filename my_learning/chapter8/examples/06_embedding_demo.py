from memory import create_embedding_model


def main() -> None:
    """
    测试 TF-IDF 文本嵌入和相似度计算。
    """

    embedding_model = create_embedding_model(
        model_type="tfidf"
    )

    documents = [
        "用户正在学习 Hello-Agents Chapter 8 的记忆系统。",
        "用户已经完成 Chapter 7 的工具注册功能。",
        "用户今天喝了一杯水。",
        "苹果是一种常见水果。",
    ]

    query = "我正在学习 Agent 的记忆功能"

    scores = embedding_model.similarity_scores(
        query=query,
        documents=documents,
    )

    print("查询内容：")
    print(query)

    print("\n原始相似度结果：")

    for document, score in zip(
        documents,
        scores,
    ):
        print(
            f"- 相似度：{score:.4f}\n"
            f"  文本：{document}"
        )

    ranked_results = sorted(
        zip(documents, scores),
        key=lambda result: result[1],
        reverse=True,
    )

    print("\n按相似度排序：")

    for index, (document, score) in enumerate(
        ranked_results,
        start=1,
    ):
        print(
            f"{index}. {document}\n"
            f"   相似度：{score:.4f}"
        )

    # similarity_scores() 内部已经调用过 fit()，
    # 因此现在可以直接把查询转换成向量。
    query_vector = embedding_model.embed_text(
        query
    )

    print("\n查询向量信息：")
    print("向量维度：", len(query_vector))
    print("前 10 个数值：", query_vector[:10])


if __name__ == "__main__":
    main()