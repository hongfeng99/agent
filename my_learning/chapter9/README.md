# Chapter 9 上下文工程

## 1. 学习目标

理解上下文工程与提示工程的区别，并实现一个能够管理
多来源上下文的长程代码库维护助手。

## 2. 已实现模块

### ContextBuilder

实现 GSSC 流水线：

- Gather：汇集候选上下文
- Select：基于相关性、新近性和 token 预算筛选信息
- Structure：构造固定上下文分区
- Compress：对超限上下文进行压缩

### NoteTool

支持：

- create
- read
- update
- search
- list
- summary
- delete

### TerminalTool

支持安全、只读的文件访问：

- pwd
- list_files
- tree
- read_file
- search_text
- file_info
- change_dir

### CodebaseMaintainer

整合：

- ContextBuilder
- NoteTool
- TerminalTool
- 真实 LLM
- 自动 blocker/action 笔记
- 跨会话状态恢复
- 会话报告

## 3. 运行方法

```powershell
python my_learning/chapter9/examples/12_codebase_maintainer_real_llm_demo.py