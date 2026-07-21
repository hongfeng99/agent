import sys
from pathlib import Path


CHAPTER8_DIR = Path(__file__).resolve().parents[1]
CHAPTER7_DIR = CHAPTER8_DIR.parent / "chapter7"

if str(CHAPTER8_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER8_DIR))

if str(CHAPTER7_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER7_DIR))


from hello_agents import (
    Config,
    HelloAgentsLLM,
    ReActAgent,
    ToolRegistry,
)

from memory import create_embedding_model
from memory.rag import (
    DocumentProcessor,
    RAGPipeline,
)

from tools.rag_tool import RAGTool


DOCUMENT_PATH = (
    CHAPTER8_DIR
    / "knowledge_base"
    / "chapter8_notes.md"
)


def create_rag_tool(
    llm: HelloAgentsLLM,
) -> RAGTool:
    """
    创建已经初始化知识库的 RAGTool。
    """

    document_processor = DocumentProcessor(
        chunk_size=150,
        chunk_overlap=30,
    )

    embedding_model = create_embedding_model(
        model_type="tfidf"
    )

    pipeline = RAGPipeline(
        document_processor=document_processor,
        embedding_model=embedding_model,
        llm=llm,
    )

    # 第一版先由 Python 预加载知识库。
    # 暂时不让模型自己决定文件路径。
    chunks = pipeline.add_file(
        str(DOCUMENT_PATH)
    )

    print(
        f"知识库初始化完成，共加载 "
        f"{len(chunks)} 个文本块。"
    )

    return RAGTool(
        pipeline=pipeline
    )


def create_agent() -> ReActAgent:
    """
    创建具有 RAG 检索能力的 Agent。
    """

    llm = HelloAgentsLLM()

    rag_tool = create_rag_tool(llm)

    registry = ToolRegistry()
    registry.register(rag_tool)

    config = Config(
        temperature=0,
        max_tokens=1200,
        max_history_length=20,
        max_steps=6,
        debug=True,
    )

    agent = ReActAgent(
        name="RAG学习助手",
        llm=llm,
        tool_registry=registry,
        system_prompt=(
            "你是一名基于知识库回答问题的学习助手。"
            "当用户询问 Chapter 8、记忆系统或 RAG 时，"
            "必须先调用 rag 工具搜索知识库，"
            "不能仅凭自己的知识直接回答。"
            "优先使用 action=search，"
            "再根据检索结果组织最终答案。"
            "回答时应注明资料来源和文本块序号。"
            "如果工具没有找到相关资料，"
            "应明确告诉用户知识库资料不足。"
        ),
        config=config,
    )

    return agent


def run_question(
    agent: ReActAgent,
    question: str,
) -> None:
    """
    执行一个问题并打印结果。
    """

    print("\n" + "=" * 70)
    print("用户问题")
    print("=" * 70)
    print(question)

    answer = agent.run(question)

    print("\n" + "=" * 70)
    print("Agent 最终回答")
    print("=" * 70)
    print(answer)

    print("\n" + "=" * 70)
    print("本次执行轨迹")
    print("=" * 70)

    for trace_item in agent.current_trace:
        print(trace_item)


def main() -> None:
    if not DOCUMENT_PATH.exists():
        raise FileNotFoundError(
            f"知识文档不存在：{DOCUMENT_PATH}"
        )

    agent = create_agent()

    # 1. 测试知识库内的问题
    run_question(
        agent,
        (
            "工作记忆和情景记忆分别有什么特点？"
            "请根据知识库回答。"
        ),
    )

    # 2. 测试 RAG 流程问题
    run_question(
        agent,
        (
            "RAG 的数据准备阶段和查询阶段"
            "分别包含哪些步骤？"
        ),
    )

    # 3. 测试知识库之外的问题
    run_question(
        agent,
        (
            "请根据当前知识库说明"
            "苹果树应该在什么季节修剪。"
        ),
    )


if __name__ == "__main__":
    main()