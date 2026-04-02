# Requirements: 决策认知系统 v2.0

**Defined:** 2026-04-02
**Core Value:** 帮助用户在复杂决策中快速识别主要矛盾，选择最优分析路径，输出可执行的决策建议

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core (Decision Loop)

- [ ] **CORE-01**: Decision Router (router-001) classifies scenario type (trivial/reversible/major/innovative) and emotion state
- [ ] **CORE-02**: Router identifies main conflict (主要矛盾) using 矛盾论 methodology
- [ ] **CORE-03**: Router implements 2-minute decision SLA for trivial/reversible scenarios
- [ ] **CORE-04**: Agent orchestration dispatches appropriate agents based on Router classification

### Agents

- [ ] **AGENT-01**: Wise Decider (wise-decider-001) — time travel test, 输得起原则, 扑克思维
- [ ] **AGENT-02**: Bias Scanner (bias-scanner-001) — 7 basic cognitive biases self-scan
- [ ] **AGENT-03**: Reverse Thinker (reverse-thinker-001) — three-step failure prevention (三步防错法)
- [ ] **AGENT-04**: Second-Order Thinker (second-order-001) — impact mapping, 10-10-10法则
- [ ] **AGENT-05**: First-Principles (first-principle-001) — 四步创新法 with 矛盾论 integration

### Output

- [ ] **OUT-01**: Recommendation Output — clear action suggestion with confidence scoring
- [ ] **OUT-02**: Decision Logging — store decisions with timestamp, scenario type, agents invoked, recommendation
- [ ] **OUT-03**: Conflict Resolution — explicit flag when agent outputs conflict

### Business Rules

- [ ] **BIZ-01**: ROI 为负 → must block and return "止亏" recommendation
- [ ] **BIZ-02**: 新人首次合作 → Model B 压测 ($10/15 videos) recommendation
- [ ] **BIZ-03**: 术语规范 enforcement — reject "免费送鞋" language, suggest alternatives
- [ ] **BIZ-04**: 流量标准 threshold — ≥1000 播放才算合格 for influencer decisions

### Meta-Framework

- [ ] **META-01**: 实事求是 integration — all agents grounded in actual evidence
- [ ] **META-02**: 矛盾论 — Router identifies main conflict before agent dispatch
- [ ] **META-03**: 实践论 — recommendations reference验证方法 (how to validate)
- [ ] **META-04**: 群众路线 stub — placeholder for future external validation (v2)

### Infrastructure

- [ ] **INFRA-01**: Python dataclass-based types.py with Pydantic 2.x validation
- [ ] **INFRA-02**: Workflow orchestrator with sequential/parallel execution modes
- [ ] **INFRA-03**: Circuit breaker — max agent hops limit to prevent infinite loops

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Agents

- **AGENT-06**: 群众路线 Agent — external validation with 三类人 (supporters/opponents/neutrals)

### Integration

- **INT-01**: Feishu Bitable logging — sync decisions to 飞书多维表
- **INT-02**: FastAPI wrapper — REST API for programmatic access
- **INT-03**: Caching layer — avoid re-running identical decisions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time data integration | Creates dependency; start with user-provided context |
| Full automation | Remove human agency; users want recommendations not mandates |
| Mobile push notifications | Context switching; aligned with async 2-min principle |
| Multi-user collaboration | Team workflows defer until single-user validated |
| English i18n | Chinese default; add after PMF confirmed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 1 | Pending |
| CORE-04 | Phase 1 | Pending |
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| AGENT-01 | Phase 2 | Pending |
| AGENT-02 | Phase 2 | Pending |
| OUT-01 | Phase 2 | Pending |
| OUT-02 | Phase 2 | Pending |
| OUT-03 | Phase 2 | Pending |
| AGENT-03 | Phase 3 | Pending |
| AGENT-04 | Phase 3 | Pending |
| AGENT-05 | Phase 3 | Pending |
| BIZ-01 | Phase 2 | Pending |
| BIZ-02 | Phase 2 | Pending |
| BIZ-03 | Phase 2 | Pending |
| BIZ-04 | Phase 2 | Pending |
| META-01 | Phase 1 | Pending |
| META-02 | Phase 1 | Pending |
| META-03 | Phase 2 | Pending |
| META-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after research synthesis*
