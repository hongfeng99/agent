import sys
from pathlib import Path


CHAPTER9_DIR = (
    Path(__file__).resolve().parent.parent
)

PROJECT_DIR = CHAPTER9_DIR.parent.parent

sys.path.insert(
    0,
    str(CHAPTER9_DIR),
)


from agents import CodebaseMaintainer
from integrations import RealLLMAdapter


# =========================================================
# 根据你自己的 llm_client.py 位置修改这里。
# 例如 llm_client.py 位于 my_learning/chapter7：
# =========================================================

LLM_CLIENT_DIR = (
    PROJECT_DIR
    / "my_learning"
    / "chapter4"
)

sys.path.insert(
    0,
    str(LLM_CLIENT_DIR),
)


from llm_client import HelloAgentsLLM


def main() -> None:
    """
    使用真实大模型运行 CodebaseMaintainer。
    """

    # 1. 创建你之前实现的大模型客户端。
    real_client = HelloAgentsLLM()

    # 2. 将客户端适配成 invoke(prompt) 接口。
    #
    # 下面假设你的 HelloAgentsLLM 使用：
    #
    #     think(messages)
    #
    # 如果实际方法不同，根据前面的表格修改。
    llm = RealLLMAdapter(
        llm_client=real_client,
        method_name="think",
        input_mode="messages",
    )

    # 3. 初始化代码库维护助手。
    maintainer = CodebaseMaintainer(
        project_name="hello_agents_chapter9",
        codebase_path=PROJECT_DIR,
        llm=llm,
        notes_workspace=(
            CHAPTER9_DIR
            / "data"
            / "real_maintainer_notes"
        ),
        focus_path="my_learning/chapter9",
    )

    # 4. 使用真实模型分析 ContextBuilder。
    response = maintainer.run(
        user_input=(
            "请根据当前真实代码，说明 "
            "ContextBuilder 的主要职责、"
            "GSSC 处理流程以及目前实现的局限。"
        ),
        mode="auto",
    )

    print("\n" + "=" * 80)
    print("真实模型回答")
    print("=" * 80)
    print(response)
    print("=" * 80)

    print("\n当前会话统计：")
    stats = maintainer.get_stats()

    print(
        f"运行次数：{stats['runs']}"
    )

    print(
        "Terminal 信息包数量："
        f"{stats['terminal_packets']}"
    )

    print(
        "对话历史消息数："
        f"{stats['history_messages']}"
    )


if __name__ == "__main__":
    main()