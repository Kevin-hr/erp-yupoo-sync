# ROADMAP: 决策认知系统 v2.0

**Granularity:** coarse (3-5 phases)
**Parallelization:** true
**Total v1 Requirements:** 22

## Phases

- [ ] **Phase 1: Foundation + Router** — Core types, decision router with scene classification, ROI red line pre-filter, circuit breaker
- [ ] **Phase 2: Primary Decision Loop** — Wise Decider, Bias Scanner, output formatting, WH business rules
- [ ] **Phase 3: Extended Agents** — Reverse Thinker, Second-Order Thinker, First-Principles Thinker
- [ ] **Phase 4: Orchestration + External Validation Stub** — Workflow orchestration, conflict resolution, 群众路线 placeholder

---

## Phase Details

### Phase 1: Foundation + Router

**Goal:** System can classify any incoming decision scenario and dispatch to appropriate agents with hard guards in place.

**Depends on:** Nothing (first phase)

**Requirements:** CORE-01, CORE-02, CORE-03, CORE-04, INFRA-01, INFRA-02, INFRA-03, META-01, META-02

**Success Criteria** (what must be TRUE):
1. User can input a decision scenario and receive a scene type classification (trivial/reversible/major/innovative) within 2 seconds
2. Router correctly identifies the main conflict (主要矛盾) from user-described scenario
3. Trivial/reversible decisions return a fast recommendation without invoking full agent chain (2-minute SLA)
4. ROI-negative scenarios are blocked at router level before any agent chain executes
5. Circuit breaker triggers and returns circuit_open error after 5 agent hops

**Plans:** 1 plan

Plans:
- [ ] 01-foundation-router/01-PLAN.md — Foundation: types.py, config.py, router with ROI guard and circuit breaker, CLI entry point

---

### Phase 2: Primary Decision Loop

**Goal:** User receives an actionable recommendation with confidence score for routine decisions, with 7-bias self-scan and WH business rule enforcement.

**Depends on:** Phase 1

**Requirements:** AGENT-01, AGENT-02, OUT-01, OUT-02, OUT-03, BIZ-01, BIZ-02, BIZ-03, BIZ-04, META-03

**Success Criteria** (what must be TRUE):
1. User receives a clear action recommendation (not analysis) with confidence score after invoking Wise Decider
2. User sees at least one bias flag (if any detected) in output before final recommendation
3. System blocks ROI-negative decisions and returns "止亏" recommendation with reason
4. System recommends "Model B 压测" for first-time influencer collaborations with $10/15 videos conditions
5. System rejects "免费送鞋" language and suggests compliant alternative terminology
6. Every decision is logged with timestamp, scenario type, agents invoked, and recommendation
7. Conflict between agents is flagged explicitly in output

**Plans:** TBD

---

### Phase 3: Extended Agents

**Goal:** High-stakes and strategic decisions can invoke Reverse, Second-Order, and First-Principles thinking paths.

**Depends on:** Phase 2

**Requirements:** AGENT-03, AGENT-04, AGENT-05

**Success Criteria** (what must be TRUE):
1. High-stakes decisions route to Reverse Thinker and receive three-step failure prevention analysis
2. Long-term project decisions route to Second-Order Thinker and receive 10-10-10 impact assessment
3. Strategic/innovative Type-C decisions route to First-Principles Thinker and receive four-step innovation analysis
4. Extended agents only invoke for appropriate decision types (not for trivial 2-minute decisions)

**Plans:** TBD

---

### Phase 4: Orchestration + External Validation Stub

**Goal:** All agents can be orchestrated in defined execution order with conflict resolution, and system has placeholder for future external validation.

**Depends on:** Phase 3

**Requirements:** META-04

**Success Criteria** (what must be TRUE):
1. Workflow orchestrator executes agents in correct sequence (Bias Scanner output feeds into Router before Wise Decider runs)
2. When agent outputs conflict, arbitration layer provides resolution and explains why one recommendation wins
3. System has documented placeholder for 群众路线 external validation (urlebird.com TikTok metrics) ready for v2 implementation
4. Parallel agents (where safe) execute concurrently to meet time SLA

**Plans:** TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Router | 0/1 | Not started | - |
| 2. Primary Decision Loop | 0/1 | Not started | - |
| 3. Extended Agents | 0/1 | Not started | - |
| 4. Orchestration + External Validation Stub | 0/1 | Not started | - |

---

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 1 | Pending |
| CORE-04 | Phase 1 | Pending |
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| META-01 | Phase 1 | Pending |
| META-02 | Phase 1 | Pending |
| AGENT-01 | Phase 2 | Pending |
| AGENT-02 | Phase 2 | Pending |
| OUT-01 | Phase 2 | Pending |
| OUT-02 | Phase 2 | Pending |
| OUT-03 | Phase 2 | Pending |
| BIZ-01 | Phase 2 | Pending |
| BIZ-02 | Phase 2 | Pending |
| BIZ-03 | Phase 2 | Pending |
| BIZ-04 | Phase 2 | Pending |
| META-03 | Phase 2 | Pending |
| AGENT-03 | Phase 3 | Pending |
| AGENT-04 | Phase 3 | Pending |
| AGENT-05 | Phase 3 | Pending |
| META-04 | Phase 4 | Pending |

**Coverage:** 22/22 requirements mapped (100%)

---

*Roadmap created: 2026-04-02*
