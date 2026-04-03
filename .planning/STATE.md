# STATE: 决策认知系统 v2.0

**Last updated:** 2026-04-02

## Project Reference

| Attribute | Value |
|-----------|-------|
| **Core Value** | 帮助用户在复杂决策中快速识别主要矛盾，选择最优分析路径，输出可执行的决策建议 |
| **Current Phase** | 0 - Not started |
| **Current Plan** | None |
| **Overall Status** | Planning |

## Current Position

| Phase | Goal | Status |
|-------|------|--------|
| 1. Foundation + Router | Core types, decision router, ROI guard, circuit breaker | Completed |
| 2. Primary Decision Loop | Wise Decider, Bias Scanner, output, WH business rules | Not started |
| 3. Extended Agents | Reverse, Second-Order, First-Principles thinkers | Not started |
| 4. Orchestration + External Validation Stub | Workflow orchestration, conflict resolution, 群众路线 placeholder | Not started |

**Progress:** 1/4 phases complete


## Performance Metrics

| Metric | Value |
|--------|-------|
| Total v1 Requirements | 22 |
| Requirements Mapped | 22 |
| Coverage | 100% |
| Phases Defined | 4 |

## Accumulated Context

### Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-02 | 4-phase roadmap (coarse) | Balance between dependency constraints and parallelization opportunity |
| 2026-04-02 | Phase 1 = Foundation + Router | Router is entry point; all agents depend on dispatch contract |
| 2026-04-02 | Phase 2 = Primary Decision Loop | Wise+Bias cover 80% usage; BIZ rules enforce WH red lines |
| 2026-04-02 | Phase 3 = Extended Agents | Conditional agents (Reverse/Second-Order/First-Principles) |
| 2026-04-02 | Phase 4 = Orchestration + Stub | Workflow wiring, conflict resolution, 群众路线 placeholder |

### Research Findings (Confidence: LOW)

| Area | Finding | Confidence |
|------|---------|------------|
| Stack | LangGraph 0.2.x recommended for orchestration beyond MVP | LOW |
| Stack | Pydantic 2.x for schema validation | LOW |
| Pitfall 1 | Agent routing loops — prevent with circuit breaker | LOW |
| Pitfall 2 | Bias conflicts with decisions — integrate bias output before Wise Decider | LOW |
| Pitfall 3 | ROI override failure — pre-filter in Router | LOW |

### Blockers

| Blocker | Impact | Resolution |
|---------|--------|------------|
| WebSearch blocked — cannot verify LangGraph version | Stack recommendation unverified | Defer stack decisions to planning phase |
| WebFetch blocked — cannot verify urlebird.com API | Phase 4 external validation stub only | Mark as v2 requirement |

### Todos

- [ ] Plan Phase 1 (Foundation + Router)
- [ ] Validate LangGraph stack recommendation when WebSearch available
- [ ] Verify Python version compatibility (avoid 3.14)

## Session Continuity

**Next action:** `/gsd:plan-phase 1` — Plan Phase 1: Foundation + Router

**Files created:**
- `.planning/ROADMAP.md` — 4-phase roadmap with success criteria
- `.planning/STATE.md` — Project state tracker
- `.planning/REQUIREMENTS.md` — Updated traceability (22/22 mapped)
- `.planning/phases/01-foundation-router/01-CONTEXT.md` — Phase 1 implementation context

**Session: 2026-04-02**
- Completed discuss-phase 1
- Decisions: types.py集中, ROI硬编码, max_hops=5, CLI单次命令, 全中文, graceful degradation, JSONL日志
