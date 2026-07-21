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
from memory.manager import MemoryManager
from memory.rag import (
    DocumentProcessor,
    RAGPipeline,
)
from memory.types.episodic import EpisodicMemory
from memory.types.semantic import SemanticMemory
from memory.types.working import WorkingMemory

from tools.agent_memory_tool import AgentMemoryTool
from tools.memory_tool import MemoryTool
from tools.rag_tool import RAGTool


DATA_DIR = CHAPTER8_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

KNOWLEDGE_DOCUMENT_PATH = (
    CHAPTER8_DIR
    / "knowledge_base"
    / "chapter8_notes.md"
)

EPISODIC_MEMORY_PATH = (
    DATA_DIR
    / "learning_assistant_episodic.json"
)

SEMANTIC_MEMORY_PATH = (
    DATA_DIR
    / "learning_assistant_semantic.json"
)


def create_agent_memory_tool() -> AgentMemoryTool:
    """
    创建 Agent 可以使用的记忆工具。
    """

    working_memory = WorkingMemory()

    episodic_memory = EpisodicMemory(
        storage_path=str(
            EPISODIC_MEMORY_PATH
        ),
    )

    semantic_memory = SemanticMemory(
        storage_path=str(
            SEMANTIC_MEMORY_PATH
        ),
    )

    memory_manager = MemoryManager(
        memories={
            "working": working_memory,
            "episodic": episodic_memory,
            "semantic": semantic_memory,
        }
    )

    memory_tool = MemoryTool(
        manager=memory_manager
    )

    return AgentMemoryTool(
        memory_tool=memory_tool
    )


def create_rag_tool(
    llm: HelloAgentsLLM,
) -> RAGTool:
    """
    创建并初始化 RAG 工具。
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

    chunks = pipeline.add_file(
        str(KNOWLEDGE_DOCUMENT_PATH)
    )

    print(
        f"RAG 知识库初始化完成，"
        f"共加载 {len(chunks)} 个文本块。"
    )

    return RAGTool(
        pipeline=pipeline
    )


def create_learning_agent() -> ReActAgent:
    """
    创建同时具有记忆和 RAG 能力的学习助手。
    """

    llm = HelloAgentsLLM()

    memory_tool = (
        create_agent_memory_tool()
    )

    rag_tool = create_rag_tool(llm)

    registry = ToolRegistry()

    registry.register(memory_tool)
    registry.register(rag_tool)

    config = Config(
        temperature=0,
        max_tokens=1500,
        max_history_length=30,
        max_steps=10,
        debug=True,
    )

    system_prompt = """
你是一名具有长期记忆和知识库检索能力的学习助手。

你可以使用两个工具：

1. memory
用于处理用户个人信息，例如：
- 用户已经学到了哪里；
- 用户完成了哪些任务；
- 用户遇到过哪些问题；
- 用户的学习偏好；
- 用户要求保存或回顾的信息。

2. rag
用于查询外部知识库中的客观知识，例如：
- Chapter 8 的知识点；
- 工作记忆、情景记忆和语义记忆的定义；
- RAG 的处理流程；
- 教材或学习笔记中的内容。

工具选择规则：

1. 用户要求“记住、保存、记录”信息时，
   必须调用 memory 工具的 add 操作。

2. 用户询问自己的历史、进度或偏好时，
   必须调用 memory 工具的 search 操作。

3. 用户询问 Chapter 8、Memory 或 RAG 知识时，
   必须调用 rag 工具的 search 操作。

4. 用户要求根据自己的进度制定下一步计划时，
   必须先调用 memory 搜索学习进度，
   再调用 rag 搜索课程知识，
   最后综合两个工具的结果回答。

5. 不能声称已经保存记忆，
   除非 memory 工具返回保存成功。

6. 不能声称知识来自知识库，
   除非已经调用 rag 工具。

7. 使用 rag 工具时优先使用 search 操作，
   外层 Agent 根据检索结果生成最终回答。

8. 如果工具没有找到相关内容，
   必须明确说明资料不足。
""".strip()

    return ReActAgent(
        name="Chapter8学习助手",
        llm=llm,
        tool_registry=registry,
        system_prompt=system_prompt,
        config=config,
    )


def run_task(
    agent: ReActAgent,
    task_name: str,
    user_input: str,
) -> None:
    """
    运行一次 Agent 任务并打印结果。
    """

    print("\n" + "=" * 70)
    print(task_name)
    print("=" * 70)

    print("\n用户输入：")
    print(user_input)

    answer = agent.run(user_input)

    print("\nAgent 回答：")
    print(answer)

    print("\n本次执行轨迹：")

    for trace_item in agent.current_trace:
        print(trace_item)


def main() -> None:
    if not KNOWLEDGE_DOCUMENT_PATH.exists():
        raise FileNotFoundError(
            "知识库文档不存在："
            f"{KNOWLEDGE_DOCUMENT_PATH}"
        )

    agent = create_learning_agent()

    # 任务一：保存个人学习进度
    run_task(
        agent=agent,
        task_name="任务一：保存学习进度",
        user_input=(
            "请记住：我已经完成了 "
            "Chapter 8 的基础记忆系统、"
            "MemoryTool、基础 RAG 检索、"
            "RAG 问答和 RAGTool，"
            "现在正在学习 Memory 与 RAG 的组合。"
            "请把它保存为 episodic 记忆，"
            "importance 设置为 0.9。"
        ),
    )

    # 任务二：查询知识库
    run_task(
        agent=agent,
        task_name="任务二：查询 Chapter 8 知识",
        user_input=(
            "请查询知识库并解释："
            "Memory 和 RAG 分别解决什么问题？"
        ),
    )

    # 任务三：回顾个人学习进度
    run_task(
        agent=agent,
        task_name="任务三：回顾学习进度",
        user_input=(
            "请查询我的记忆，"
            "告诉我目前已经完成了哪些内容。"
        ),
    )

    # 任务四：同时使用两个工具
    run_task(
        agent=agent,
        task_name="任务四：生成个性化下一步计划",
        user_input=(
            "请先查询我的学习进度，"
            "再查询 Chapter 8 知识库，"
            "结合两部分信息告诉我接下来"
            "最应该完成哪三项任务。"
        ),
    )


if __name__ == "__main__":
    main()