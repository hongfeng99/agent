# Chapter 8：记忆与检索

本目录是《Hello Agents》第八章“记忆与检索”的学习与实践代码。

本章从基础记忆数据结构开始，逐步实现工作记忆、情景记忆、语义记忆、记忆管理器、RAG 检索管线、MemoryTool 和 RAGTool，最后组合成一个具备文档问答、长期记忆和学习记录能力的 `LearningAssistant`。

---

## 1. 学习目标

本章主要完成以下目标：

1. 理解 Agent 为什么需要记忆；
2. 区分工作记忆、情景记忆和语义记忆；
3. 实现记忆的添加、搜索、更新、遗忘和整合；
4. 实现基于 TF-IDF 的基础文本检索；
5. 理解 RAG 的文档分块、检索、上下文构建和生成流程；
6. 将 Memory 和 RAG 封装成 Agent 工具；
7. 构建可交互的学习文档问答助手；
8. 使用 pytest 对主要功能进行自动化测试。

---

## 2. 已实现功能

### 2.1 记忆系统

当前实现了三类记忆。

#### WorkingMemory

工作记忆用于保存当前任务所需的临时信息，当前支持：

- 容量限制；
- TTL 过期清理；
- 重复内容处理；
- 重要性评分；
- 基于 TF-IDF 的内容检索；
- 纯内存存储。

#### EpisodicMemory

情景记忆用于保存具体发生过的事件，当前支持：

- JSON 文件持久化；
- 按内容检索；
- 按时间范围过滤；
- 按会话编号过滤；
- 保存事件元数据。

#### SemanticMemory

语义记忆用于保存稳定的事实、概念和学习笔记，当前支持：

- JSON 文件持久化；
- 按内容检索；
- 按知识分类过滤；
- 保存长期稳定知识。

---

### 2.2 MemoryManager

`MemoryManager` 统一协调不同类型的记忆，并支持：

- 添加记忆；
- 根据 ID 查询记忆；
- 跨类型搜索记忆；
- 更新记忆；
- 删除记忆；
- 遗忘低重要性记忆；
- 将工作记忆整合到长期记忆；
- 查看记忆统计；
- 清空指定类型或全部记忆。

记忆管理流程如下：

```text
MemoryItem
    ↓
MemoryManager
    ↓
根据 memory_type 分发
    ↓
WorkingMemory / EpisodicMemory / SemanticMemory
```

---

### 2.3 MemoryTool

`MemoryTool` 将记忆系统封装为统一工具，支持以下操作：

```text
add
get
search
update
forget
consolidate
stats
clear
```

所有操作都返回 JSON 字符串，成功结果包含：

```json
{
  "success": true,
  "action": "add",
  "result": {}
}
```

失败结果包含：

```json
{
  "success": false,
  "action": "unknown_action",
  "error": "错误信息"
}
```

`AgentMemoryTool` 进一步将 `MemoryTool` 适配到 Chapter 7 的：

```text
Tool
ToolRegistry
ReActAgent
```

---

### 2.4 RAG 系统

当前实现了一个基础 RAG 管线：

```text
读取文档
    ↓
文本分块
    ↓
TF-IDF 向量化
    ↓
计算余弦相似度
    ↓
返回 Top-K 文本块
    ↓
构建参考上下文
    ↓
调用大模型生成答案
```

当前支持：

- `.txt` 文件；
- `.md` 文件；
- 固定字符数分块；
- 相邻文本块重叠；
- TF-IDF 文本表示；
- 余弦相似度检索；
- Top-K 排序；
- 最低相关度过滤；
- 来源文件记录；
- 文本块序号记录；
- 基于检索结果生成答案；
- 资料不足时不调用大模型。

---

### 2.5 DocumentProcessor

`DocumentProcessor` 负责文档读取和文本分块。

第一版支持：

```text
.txt
.md
```

文本分块使用滑动窗口：

```text
chunk_size = 每个文本块的最大字符数
chunk_overlap = 相邻文本块重复保留的字符数
step = chunk_size - chunk_overlap
```

例如：

```text
chunk_size = 150
chunk_overlap = 30
step = 120
```

第一个文本块：

```text
0～150
```

第二个文本块：

```text
120～270
```

两个文本块之间存在 30 个字符的重叠。

---

### 2.6 RAGPipeline

`RAGPipeline` 负责完整的 RAG 业务流程，主要接口包括：

```python
pipeline.add_file(...)
pipeline.add_text(...)
pipeline.search(...)
pipeline.build_context(...)
pipeline.ask(...)
pipeline.stats()
pipeline.clear()
```

`search()` 只负责检索：

```text
用户查询
    ↓
查询向量化
    ↓
与全部文本块计算相似度
    ↓
按分数降序排列
    ↓
返回 Top-K 文本块
```

`ask()` 负责完整问答：

```text
用户问题
    ↓
search()
    ↓
build_context()
    ↓
构建 messages
    ↓
llm.invoke()
    ↓
返回 RAGAnswer
```

---

### 2.7 RAGTool

`RAGTool` 将 `RAGPipeline` 封装为 Chapter 7 的标准工具，支持：

```text
add_file
add_text
search
ask
stats
clear
```

在 `ReActAgent` 中推荐优先调用：

```json
{
  "action": "search",
  "query": "什么是工作记忆？",
  "top_k": 3,
  "min_score": 0.01
}
```

这样职责更加清晰：

```text
RAGTool 负责检索
ReActAgent 负责组织最终答案
```

---

### 2.8 Memory 与 RAG 综合 Agent

当前已经将以下两个工具同时注册到一个 `ReActAgent`：

```text
memory
rag
```

Agent 可以根据问题类型选择工具。

查询个人学习进度：

```text
我目前已经完成了哪些内容？
    ↓
调用 memory.search
```

查询文档知识：

```text
工作记忆有什么特点？
    ↓
调用 rag.search
```

生成个性化学习计划：

```text
查询个人学习进度
    ↓
memory.search
    ↓
查询 Chapter 8 课程知识
    ↓
rag.search
    ↓
综合两个工具结果
    ↓
生成下一步学习计划
```

---

### 2.9 LearningAssistant

`LearningAssistant` 将 Memory 和 RAG 封装成可重复使用的应用类。

主要接口包括：

```python
assistant.load_document(...)
assistant.ask(...)
assistant.add_note(...)
assistant.recall(...)
assistant.get_stats(...)
assistant.generate_report(...)
```

#### load_document()

执行流程：

```text
读取文档
    ↓
调用 RAGTool.add_file
    ↓
建立知识库
    ↓
将文档加载事件写入情景记忆
```

#### ask()

执行流程：

```text
记录用户问题到工作记忆
    ↓
调用 RAGTool.ask
    ↓
基于知识库生成答案
    ↓
将问答事件写入情景记忆
```

#### add_note()

执行流程：

```text
用户输入学习笔记
    ↓
保存到语义记忆
```

#### recall()

执行流程：

```text
输入回顾关键词
    ↓
搜索工作记忆、情景记忆和语义记忆
    ↓
返回历史学习内容
```

#### generate_report()

生成包含以下内容的 JSON 学习报告：

```text
会话信息
学习时长
加载文档数量
提问数量
笔记数量
Memory 统计
RAG 统计
近期学习记录
```

---

## 3. 项目结构

```text
chapter8/
├── assistant/
│   ├── __init__.py
│   └── learning_assistant.py
├── data/
│   └── .gitkeep
├── examples/
│   ├── 01_*.py
│   ├── ...
│   ├── 14_memory_agent_demo.py
│   ├── 15_document_chunk_demo.py
│   ├── 16_rag_retrieval_demo.py
│   ├── 17_rag_answer_demo.py
│   ├── 18_rag_tool_demo.py
│   ├── 19_rag_agent_demo.py
│   ├── 20_memory_rag_agent_demo.py
│   └── 21_learning_assistant_cli.py
├── knowledge_base/
│   └── chapter8_notes.md
├── memory/
│   ├── __init__.py
│   ├── base.py
│   ├── embedding.py
│   ├── manager.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── document.py
│   │   └── pipeline.py
│   ├── storage/
│   │   └── json_store.py
│   └── types/
│       ├── working.py
│       ├── episodic.py
│       └── semantic.py
├── reports/
│   └── .gitkeep
├── tests/
│   ├── conftest.py
│   ├── test_document_processor.py
│   ├── test_rag_pipeline.py
│   ├── test_memory_manager.py
│   ├── test_memory_tool.py
│   └── test_learning_assistant.py
├── tools/
│   ├── __init__.py
│   ├── agent_memory_tool.py
│   ├── memory_tool.py
│   └── rag_tool.py
└── README.md
```

---

## 4. Memory 和 RAG 的区别

| 对比项 | Memory | RAG |
|---|---|---|
| 数据来源 | 用户交互和 Agent 历史 | 外部文档和知识库 |
| 主要用途 | 个性化和历史回顾 | 补充外部知识 |
| 典型问题 | 我之前学到了哪里 | 工作记忆是什么 |
| 更新方式 | 随用户交互持续更新 | 主动加载文档 |
| 当前工具 | MemoryTool | RAGTool |
| 是否记录用户偏好 | 是 | 通常不是 |
| 是否用于文档问答 | 不是主要用途 | 是 |

两者组合后，Agent 既可以知道用户过去完成过什么，也可以从外部知识库中获取客观资料。

---

## 5. 环境要求

推荐环境：

```text
Python 3.10+
```

主要依赖：

```text
openai
python-dotenv
scikit-learn
pytest
```

安装 pytest：

```bash
python -m pip install pytest
```

大模型配置放在项目的 `.env` 文件中，例如：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_base_url
LLM_MODEL_ID=your_model_name
LLM_TIMEOUT=60
```

不要将 `.env` 提交到 GitHub。

---

## 6. 运行示例

进入 Chapter 8 目录：

```bash
cd my_learning/chapter8
```

### 6.1 运行记忆 Agent

```bash
python examples/14_memory_agent_demo.py
```

### 6.2 运行文档分块

```bash
python examples/15_document_chunk_demo.py
```

### 6.3 运行基础 RAG 检索

```bash
python examples/16_rag_retrieval_demo.py
```

### 6.4 运行 RAG 问答

```bash
python examples/17_rag_answer_demo.py
```

### 6.5 运行 RAGTool

```bash
python examples/18_rag_tool_demo.py
```

### 6.6 运行 RAG Agent

```bash
python examples/19_rag_agent_demo.py
```

### 6.7 运行 Memory + RAG 综合 Agent

```bash
python examples/20_memory_rag_agent_demo.py
```

### 6.8 运行 LearningAssistant CLI

```bash
python examples/21_learning_assistant_cli.py
```

CLI 菜单包括：

```text
1. 加载文档
2. 向文档提问
3. 添加学习笔记
4. 回顾学习记录
5. 查看学习统计
6. 生成学习报告
0. 退出
```

加载测试文档时可以输入：

```text
knowledge_base/chapter8_notes.md
```

---

## 7. 运行自动化测试

进入 Chapter 8 目录：

```bash
cd my_learning/chapter8
```

运行全部测试：

```bash
python -m pytest tests -v
```

使用简洁模式：

```bash
python -m pytest tests -q
```

运行单个测试文件：

```bash
python -m pytest tests/test_document_processor.py -v
```

```bash
python -m pytest tests/test_rag_pipeline.py -v
```

```bash
python -m pytest tests/test_memory_manager.py -v
```

```bash
python -m pytest tests/test_memory_tool.py -v
```

```bash
python -m pytest tests/test_learning_assistant.py -v
```

自动化测试覆盖：

- Document 数据校验；
- TXT 和 Markdown 文件读取；
- 文档分块；
- chunk overlap；
- RAG 文本添加；
- Top-K 检索；
- 最低分数过滤；
- RAG 上下文构建；
- FakeLLM 问答；
- 无资料时禁止调用 LLM；
- 记忆添加、查询、搜索和更新；
- 记忆删除、遗忘和整合；
- 工作记忆容量限制；
- 长期记忆持久化；
- MemoryTool 参数处理；
- MemoryTool 结构化错误；
- LearningAssistant 文档加载；
- LearningAssistant 文档问答；
- 学习笔记保存；
- 学习记录回顾；
- 学习统计；
- JSON 报告生成。

测试使用 `FakeLLM`，不会请求真实的大模型 API，也不会消耗模型额度。

---

## 8. 数据文件说明

运行过程中生成的记忆文件保存在：

```text
chapter8/data/
```

生成的学习报告保存在：

```text
chapter8/reports/
```

这些 JSON 文件属于运行时数据，不提交到 GitHub。

`.gitignore` 应包含：

```gitignore
my_learning/chapter8/data/*.json
!my_learning/chapter8/data/.gitkeep

my_learning/chapter8/reports/*.json
!my_learning/chapter8/reports/.gitkeep
```

---

## 9. 当前局限

当前版本主要用于学习 Memory 和 RAG 的底层原理，存在以下限制：

1. 文档只支持 `.txt` 和 `.md`；
2. 使用 TF-IDF，而不是真正的语义 Embedding；
3. 中文检索主要依赖字符级特征和关键词重叠；
4. RAG 文本块只保存在内存中；
5. 程序重启后需要重新加载知识文档；
6. 长期记忆使用 JSON 文件，不适合大规模数据；
7. 尚未实现感知记忆；
8. 尚未接入 Qdrant、Neo4j 或 SQLite；
9. 尚未实现 PDF 和 Word 文档解析；
10. 尚未实现多模态检索；
11. 尚未实现 MQE；
12. 尚未实现 HyDE；
13. 尚未实现重排序模型；
14. 跨记忆类型检索还可以进一步统一相关度评分。

---

## 10. 后续优化方向

后续可以逐步扩展：

- 使用 Embedding API 替换 TF-IDF；
- 使用本地 SentenceTransformer；
- 使用 Qdrant 保存文档向量；
- 使用 SQLite 保存文档元数据；
- 使用 Neo4j 构建知识图谱；
- 增加 PDF 和 Word 文档解析；
- 增加语义分块；
- 增加检索结果重排序；
- 实现 MQE 多查询扩展；
- 实现 HyDE 假设文档检索；
- 增加感知记忆；
- 使用 Gradio 构建 Web 页面；
- 增加多用户和多会话支持。

---

## 11. 当前状态

Chapter 8 第一版已经完成：

```text
Memory
+ RAG
+ Tool
+ ReActAgent
+ LearningAssistant
+ Automated Tests
```

当前已经跑通从底层数据结构到最终学习助手的完整链路，并为主要模块建立了自动化测试。