# Chapter 10：智能体通信协议

## 学习目标

- 理解 MCP、A2A、ANP 的职责与区别
- 编写自定义 MCP Server
- 通过 A2A 完成 Agent 间任务委托
- 通过 ANP 完成服务发现与路由
- 完成 ANP + A2A + MCP 组合实验

## 协议分工

- MCP：Agent 与工具、资源通信
- A2A：Agent 与 Agent 通信
- ANP：服务注册、发现和路由

## 最终架构

用户任务
→ ANP 选择 real_code_analyst
→ A2A 发送任务到 5001
→ 远程 Agent 通过 MCP 读取 Chapter 9 源码
→ LLM 分析 ContextBuilder
→ A2A 返回结果

## 核心文件

- 05_codebase_mcp_server.py
- 06_codebase_mcp_client.py
- 07_codebase_mcp_agent.py
- 08_a2a_code_analyst_server.py
- 09_a2a_code_analyst_client.py
- 10_a2a_coordinator_agent.py
- 11_a2a_mcp_code_analyst_server.py
- 12_a2a_mcp_coordinator_agent.py
- 13_anp_service_discovery.py
- 14_anp_scheduler_agent.py
- 15_full_protocol_pipeline.py