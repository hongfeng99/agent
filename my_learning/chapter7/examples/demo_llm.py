from hello_agents.llm import HelloAgentsLLM


def main() -> None:
    """
    测试 Chapter 7 中的 HelloAgentsLLM。
    """

    llm = HelloAgentsLLM()

    messages = [
        {
            "role": "user",
            "content": "请只回复：Chapter 7 LLM 测试成功",
        }
    ]

    result = llm.invoke(
        messages=messages,
        temperature=0,
    )

    print("模型回答：")
    print(result)


if __name__ == "__main__":
    main()