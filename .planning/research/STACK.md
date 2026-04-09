# Stack Research

**Domain:** Multi-Agent Decision Support Systems (Decision Cognition Systems)
**Researched:** 2026-04-02
**Confidence:** LOW (Cannot verify with web sources - WebSearch/WebFetch denied in environment)

## Executive Summary

The existing decision-cognition-skill implements 6 specialized agents using pure Python dataclasses with no external orchestration framework. This is a valid "start simple" approach. However, for production-grade multi-agent systems with complex routing, state management, and LLM integration, industry standard frameworks exist that reduce boilerplate and provide battle-tested patterns.

## Actual Implementation (2026-04-08 Verified)

### Core Architecture: Pure Python Dataclass

**结论：不采用任何外部编排框架。**

当前实现使用**纯 Python dataclass + 原生 asyncio** 实现决策系统：

| 组件 | 实现方式 | 说明 |
|------|---------|------|
| 状态管理 | `@dataclass` + `PipelineState` | `sync_pipeline.py:242-254` |
| 决策路由 | `DecisionRouter` (pure Python) | `decision_system/router.py` |
| 工作流编排 | `DecisionWorkflow` (顺序调度) | `decision_system/workflow.py` |
| 熔断器 | `CircuitBreaker` ( dataclass) | `decision_system/circuit_breaker.py` |
| Agent | Python dataclass | `decision_system/types.py` |

**不采用 LangGraph / CrewAI 的理由：**
1. 当前决策场景是**顺序执行**（路由器→Agent→结果），无需图结构的条件分支
2. 无需 cycles/循环支持（BiasScanner 是一次性调用）
3. 无状态持久化需求（每次 CLI 调用独立）
4. **引入 LangGraph 增加复杂度但无实际收益**

**LangGraph 适用场景（未来可能）：**
- 需要图结构条件分支的复杂 Agent 流
- 需要 cycle（迭代式 Refinement）
- 需要 Checkpointing 跨对话持久化状态
- 当前 ERP 同步流水线的并行化改造（`concurrent_batch_sync.py`）更适合用 asyncio.Semaphore 而非 LangGraph

### LLM Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **LangChain OpenAI** | 0.3.x | OpenAI GPT-4o/4-turbo integration | Standard interface for OpenAI models; streaming support built-in |
| **LangChain Anthropic** | 0.3.x | Claude integration | Official LangChain integration for Claude; handles tool calling, streaming |
| **LiteLLM** | 1.5+ | Unified LLM interface | Single API for 50+ LLMs; useful if project adds local models later |

**For this project**: Use LangChain with Anthropic Claude (since project uses Claude Code which suggests Anthropic preference). OpenAI as fallback.

### State Management

| Technology | Purpose | Why Recommended |
|------------|---------|-----------------|
| **LangGraph Checkpointing** | Built-in state persistence | Native to LangGraph; no separate DB needed for prototype |
| **SQLite** | Persistent storage for decisions | Zero-config, file-based, sufficient for single-user workflow |

### API/Web Framework (if needed later)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **FastAPI** | 0.115+ | REST API layer | Modern async Python web framework; automatic OpenAPI docs; pairs well with LangGraph |
| **Uvicorn** | 0.30+ | ASGI server | Standard ASGI server for FastAPI |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Pydantic** | 2.x | Data validation | Define agent input/output schemas; type-safe |
| **Logfire** | 0.9+ | Observability | Python-native tracing; see agent decision paths |
| **structlog** | 24.x | Structured logging | Debug agent workflows |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **AutoGen 0.x (old)** | Complex setup, verbose; 2024 framework churn | LangGraph (more stable API) |
| **LangChain 0.1 (old)** | Breaking changes between versions | LangGraph directly (not LangChain) |
| **CrewAI as sole orchestrator** | Good for role-based, less flexible for complex state machines | LangGraph for complex routing |
| **Python 3.14** | Very new (Oct 2024); many ML packages not yet compatible | Python 3.11 or 3.12 for ML/agent work |

## Alternative Considerations

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| LangGraph | CrewAI | If agents are purely role-based with simple delegation (no cycles) |
| LangGraph | Temporal | For enterprise-grade workflow persistence (overkill for single-user) |
| Claude (Anthropic) | GPT-4o (OpenAI) | If project prioritizes function calling stability |
| SQLite | PostgreSQL | Only if multi-user or need vector similarity search later |

## Stack Patterns by Variant

**If keeping pure Python (no external framework):**
- Continue with current dataclass-based agent pattern
- Add explicit state machine using `enum` for agent states
- Use `functools.singledispatch` for agent dispatching
- Rationale: Valid for simple flows; scales poorly beyond 10 agents

**If adopting LangGraph:**
- Replace workflow.py orchestration with LangGraph StateGraph
- Agents become "nodes" in the graph
- Router becomes conditional edges
- Checkpointing replaces manual state tracking
- Rationale: Industry standard; handles complex flows; built-in persistence

**If using CrewAI:**
- Define each agent (router, decider, etc.) as CrewAI agents with roles
- Use tasks for each step; crew orchestrates delegation
- Rationale: Cleaner for committee-style voting; less flexible for complex state

## Version Compatibility

| Package | Python Version | Notes |
|---------|----------------|-------|
| LangGraph 0.2.x | 3.10 - 3.12 | Python 3.14 not officially supported yet |
| CrewAI 0.80+ | 3.10 - 3.12 | Similar Python version constraints |
| LangChain 0.3.x | 3.8 - 3.12 | Broader compatibility but use 3.11+ |
| Pydantic 2.x | 3.9+ | Well maintained |

## Installation

```bash
# Recommended: Use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows: venv\Scripts\activate

# Core packages
pip install langgraph langchain-openai langchain-anthropic

# Supporting
pip install pydantic structlog

# For FastAPI later (if needed)
pip install fastapi uvicorn
```

## Existing Implementation Analysis

The current `decision-cognition-skill` uses:
- Pure Python 3.14 with dataclasses
- No external agent frameworks
- Manual workflow orchestration in `workflow.py`
- Router-based agent dispatching
- No persistent state management

This is a valid **minimal viable approach** for prototyping. The upgrade path is:
1. Phase 1: Keep current architecture, add Pydantic schemas
2. Phase 2: Add LiteLLM for unified LLM interface
3. Phase 3: Migrate to LangGraph if complexity grows

## Sources

- [T2: Training data] LangGraph architecture patterns
- [T2: Training data] CrewAI role-based agent patterns
- [T2: Training data] Multi-agent system design principles
- [T2: Training data] LangChain ecosystem 2024-2025 trends
- [T2: Training data] Python 3.14 ML package compatibility notes

**Confidence Note**: All technology recommendations based on training data from 2024. Cannot verify with Context7 or official docs due to WebSearch/WebFetch restrictions in environment. **Validate all version numbers before production use.**

---
*Stack research for: Multi-Agent Decision Support Systems*
*Researched: 2026-04-02*
