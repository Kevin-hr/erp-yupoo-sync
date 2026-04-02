# Phase 1: Foundation + Router - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the foundational type system, decision router with ROI pre-filter and circuit breaker, and a working CLI entry point. This is the platform on which all subsequent agents run.

Scope:
- `types.py` — centralized dataclass definitions
- `DecisionRouter` — scene classification, main conflict identification, ROI pre-filter, 2-min timeout, circuit breaker
- `cli.py` — single-shot CLI entry point
- `config.py` — configuration constants (ROI thresholds hardcoded, max hops configurable)
- Decision logging to JSONL

Out of scope: Agent implementations (Phase 2), Workflow orchestration (Phase 4)

</domain>

<decisions>
## Implementation Decisions

### Type System
- **集中管理**: 所有核心类型放在 `types.py`，agents import 它，不内联定义
- **核心类型**: `SceneType`, `MainConflict`, `AgentSpec` — 场景类型、主要矛盾、Agent规格元数据
- **结果类型**: `RouterResult`, `AgentResult` 作为基类，具体 Agent 返回子类

### Router Behavior
- **ROI 红线**: Router 第一步检查 ROI，为负直接 block，不走 Agent 链
- **2分钟 SLA**: Simple timeout 实现 — LLM 调用加 timeout 参数
- **主要矛盾提取**: Keyword pattern matching（保持当前实现，不引入 LLM 推理）
- **场景分类输出**: JSON dataclass，不输出自然语言描述

### Circuit Breaker
- **触发条件**: Max hops = 5（硬编码）
- **行为**: 超过 5 次 agent 调用后触发熔断，返回 `circuit_open` 错误

### CLI Interface
- **交互形态**: 单次命令 `python -m decision_system "你的决策描述"`
- **输出语言**: 全中文输出
- **错误策略**: Graceful degradation — 单个 Agent 失败降级，返回部分结果+警告
- **日志存储**: JSONL 文件，每次决策追加到文件

### Code Organization
- **目录结构**: `decision_system/` 包，包含 `types.py`, `router.py`, `agents/`, `cli.py`
- **配置**: `config.py` 存 ROI 阈值（硬编码）和 max_hops（可配置）
- **CLI 入口**: `__main__.py` 支持 `python -m decision_system`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\agents\router.py` — 现有 DecisionRouter 实现，包含场景分类逻辑、关键词检测、矛盾提取
- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\workflow.py` — 现有 Workflow 类，展示了 agent 调用模式和仲裁逻辑

### Patterns to Follow
- dataclass-based result types (RouterResult, DecisionResult 等)
- `to_json()` 方法序列化模式
- `analyze()` 主入口方法签名

### What to Change
- types 从 inline 移到 `types.py`
- Router 需要新增: ROI pre-filter, simple timeout, circuit breaker hop counter
- 当前 Workflow 是顺序执行，Phase 1 还不涉及并行

</code_context>

<specifics>
## Specific Ideas

- "2分钟上限原则" — trivial/reversible 场景不触发完整 Agent 链
- "ROI 为负止亏" — 新人合作 ROI 负数 → 直接 block
- "实事求是" — Router 分类基于实际关键词，不是 LLM 猜测

</specifics>

<deferred>
## Deferred Ideas

- SQLite 决策日志存储 — Phase 2 或 Phase 4 再考虑，当前用 JSONL
- 自然语言输出 — Phase 2 输出格式化再考虑
- Config 文件化 ROI 阈值 — 当前硬编码，后续按需改为 config

</deferred>

---
*Phase: 01-foundation-router*
*Context gathered: 2026-04-02*
