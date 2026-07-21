# Chapter 7：构建自己的 Agent 框架

本项目是 Hello-Agents Chapter 7 的学习实践，实现了一个简化但完整的 Python Agent 框架。

## 1. 已实现功能

### 基础组件

- `HelloAgentsLLM`：统一封装大模型调用
- `Message`：统一消息对象
- `Config`：统一配置对象
- `Agent`：所有 Agent 的抽象基类
- 自定义异常体系

### Agent

- `SimpleAgent`：基础多轮对话
- `ReActAgent`：思考、工具调用、观察和最终回答
- `ReflectionAgent`：初始回答、反思和改进
- `PlanAndSolveAgent`：规划、逐步执行和结果汇总

### 工具系统

- `Tool`：工具抽象基类
- `ToolRegistry`：工具注册与执行
- `CalculatorTool`：基于 AST 的安全计算器
- `TavilySearchTool`：网络搜索工具
- `ToolChain`：固定顺序工具链
- `AsyncToolExecutor`：并发工具执行器

### 测试

使用 `pytest` 测试：

- 消息和配置
- Agent 历史管理
- 安全计算器
- 工具注册表
- 工具链
- 异步执行器
- ReActAgent
- ReflectionAgent
- PlanAndSolveAgent

## 2. 项目结构

```text
hello_agents/
├── agents/
├── tools/
├── agent.py
├── config.py
├── exceptions.py
├── llm.py
└── message.py