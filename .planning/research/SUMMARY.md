# Project Research Summary

**Project:** 决策认知系统 v2.0 (Decision Cognition System)
**Domain:** Multi-Agent AI Decision Support Systems
**Researched:** 2026-04-02
**Confidence:** LOW (WebSearch/WebFetch blocked in environment — all findings based on training data, require validation)

## Executive Summary

The 决策认知系统 v2.0 is a 6-agent AI decision support system built around 毛泽东思想 methodology (矛盾论, 实践论, 群众路线) for Chinese business culture. Unlike Western AI decision tools that focus on data-driven analysis, this system uniquely integrates Maoist philosophical frameworks with multi-agent orchestration to produce actionable recommendations with hard ROI constraints. The existing implementation uses pure Python dataclasses with no external orchestration framework — a valid MVP approach, but one that will require framework investment as complexity grows.

Research recommends using **LangGraph** as the orchestration backbone when migrating beyond MVP, paired with **Claude (Anthropic)** as the LLM and **Pydantic 2.x** for schema validation. The most critical risks are agent routing loops, bias detection conflicts with final decisions, and business rule override failures — all of which must be addressed in Phase 1 Router design. The architecture is well-defined with a clear 6-phase build order, but all technology version recommendations should be verified against current documentation before production use.

## Key Findings

### Recommended Stack

The current pure Python dataclass approach is valid for MVP but has a clear upgrade path. For production-scale multi-agent systems, **LangGraph 0.2.x** is recommended over alternatives (CrewAI, Temporal) because it supports cycles (critical for iterative bias scanning), conditional branching, and native checkpointing. **LangChain Anthropic** provides the official Claude integration with tool calling and streaming support. **Pydantic 2.x** enforces type-safe agent input/output schemas. **Python 3.11 or 3.12** — NOT 3.14, which is too new for ML/agent package compatibility.

**Core technologies:**
- **LangGraph 0.2.x**: Multi-agent workflow orchestration — graph-based state machine ideal for decision pipelines with conditional routing and cycle support
- **LangChain Anthropic**: Claude API integration — official LangChain integration handling tool calling and streaming
- **Pydantic 2.x**: Data validation — defines agent input/output schemas with type safety
- **structlog 24.x**: Structured logging — debug agent workflows in production
- **SQLite**: Persistent decision logging — zero-config, file-based, sufficient for single-user workflow

### Expected Features

**Must have (table stakes):**
- Decision Router with scenario classification — distinguishes trivial/reversible/major/innovative decisions
- Wise Decider (80% usage rate) — primary decision agent with time-travel and "输得起" principles
- Basic Bias Scanner (7 cognitive biases) — self-scan only for MVP, no external validation
- Clear recommendation output with confidence scoring — users want action, not analysis
- Decision logging — audit trail for all decisions

**Should have (competitive differentiators):**
- 毛泽东思想 methodology integration — unique to Chinese business culture, not found in Western tools
- 6 specialized agents depth — Router + Wise + Bias + Reverse + Second-order + First-principles
- 2-Minute Decision Principle — built-in timeboxing prevents over-analysis paralysis
- WH Business Rule Integration — ROI red lines as hard constraints (ROI为负止亏)
- 群众路线 External Validation — three-perspective external check (supporters/opponents/neutrals)
- Reverse Thinker + Second-Order Thinker — triggered for high-stakes and long-term decisions

**Defer (v2+):**
- Multi-user collaboration workflows
- CRM/ERP/spreadsheet data integrations
- Decision templates for common patterns
- Mobile push notifications
- English language support

### Architecture Approach

The system follows a **Pipeline Orchestration** pattern with a central **Workflow/Arbitration layer**. The Router is the critical first component — it performs scene classification, identifies the principal contradiction (主要矛盾), and determines which agents to invoke. Agents are arranged as nodes in the graph, with the Router acting as conditional edges. The Meta-Framework (毛泽东思想四大支柱) acts as implicit constraints across all agents rather than as a standalone computation node, preserving agent boundaries while enforcing philosophical methodology.

**Major components:**
1. **Router (router-001)** — scene classification, principal contradiction identification, agent dispatch decisions; must be built before all other agents
2. **WiseDecider (wise-decider-001)** — primary decision agent (80% usage), implements time-travel testing and poker thinking
3. **BiasScanner (bias-scanner-001)** — 7 cognitive biases, mass line external validation; output must feed into Router before Wise Decider runs
4. **ReverseThinker (reverse-thinker-001)** — three-step error prevention, hell-step deduction; invoked for high-stakes decisions
5. **SecondOrderThinker (second-order-001)** — impact mapping, 10-10-10法则; invoked for long-term projects
6. **FirstPrincipleThinker (first-principle-001)** — analogy trap detection, basic truth decomposition; only for Type C strategic decisions
7. **Workflow + Arbitration** — orchestrates all agents, handles conflict resolution, formats final output
8. **Meta-Framework** — implicit constraints (实事求是, 矛盾论, 实践论, 群众路线) applied across all agents

### Critical Pitfalls

1. **Agent Routing Loops** — agents enter infinite Router -> Agent A -> Agent B -> Router cycles with no termination. Prevention: hard timeout per agent (30-60s), maximum routing hops (5) with circuit breaker, explicit "no agent available" fallback.

2. **Bias Detection Conflicts with Decision Outcome** — Bias Scanner flags a decision but Wise Decider has already committed, producing contradictory outputs. Prevention: Bias Scanner output must feed into Router's scenario classification BEFORE Wise Decider runs; bias flag = require additional evidence or route to Reverse Thinker.

3. **Business Rule Override Failure** — system recommends decisions violating WH ROI red lines (e.g., ROI-negative collaborations). Prevention: implement ROI red lines as pre-filter in Router before any agent chain; never allow agent reasoning to override hard constraints.

4. **Context Window Overflow** — long-running decision threads accumulate context from all 6 agents, exceeding LLM limits. Prevention: rolling summarization, maximum context budget (32K tokens), structured JSON output (not prose), context-refresh for sub-decisions.

5. **First Principles becomes Over-Engineering** — First Principles agent invoked for trivial decisions (sample shipping), violating 2-minute decision principle. Prevention: decision urgency classification in Router (A=2min max, B=10min, C=strategic 30min+); only invoke First Principles for Type C decisions.

## Implications for Roadmap

Based on research, a 6-phase build order emerges from architecture dependencies and pitfall prevention requirements:

### Phase 1: Foundation + Router
**Rationale:** Router is the entry point and scheduler — all other agents depend on it. This phase must establish data structures, context management strategy, decision classification, loop prevention, and ROI red line guardrails before any agent chain can run safely.
**Delivers:** types.py dataclasses, router.py with scene classification and agent dispatch, context management strategy, hard timeouts, ROI red line pre-filter
**Avoids:** Pitfalls 1 (routing loops), 3 (business rule override), 4 (context overflow), 6 (first principles over-use), 8 (agent persona creep — establish prompt governance here)

### Phase 2: Core Agents (Wise + Bias)
**Rationale:** Wise Decider handles 80% of decisions; Bias Scanner output must be integrated with Router before Wise Decider runs (Pitfall 2 prevention). These two agents cover the primary decision loop.
**Delivers:** wise_decider.py, bias_scanner.py (7 biases, self-scan only), basic recommendation output with confidence scoring
**Implements:** Pipeline orchestration pattern, decision logging

### Phase 3: Extended Agents (Reverse + Second-Order + First-Principles)
**Rationale:** These agents are invoked conditionally based on Router classification. They can be developed in parallel once Phase 2 establishes the agent interface contract.
**Delivers:** reverse_thinker.py (high-stakes), second_order.py (long-term), first_principle.py (strategic/innovative Type C only)
**Avoids:** Pitfall 6 (first principles over-use — classification gates these invocations)

### Phase 4: Workflow Orchestration + Arbitration
**Rationale:** With all agents implemented, wire them together with explicit data flow, execution order, and conflict resolution rules. Define the agent compatibility matrix for parallel vs. sequential execution.
**Delivers:** workflow.py orchestration, arbitration.py conflict resolution, unified output template
**Avoids:** Pitfall 5 (parallel vs. sequential ambiguity — must document dependencies)

### Phase 5: 群众路线 External Validation + Meta-Framework Integration
**Rationale:** External validation was flagged as likely to never execute if deferred (Pitfall 7). Define minimum viable external validation (1 data point: urlebird.com for TikTok metrics) as a Phase 1 requirement but full implementation here.
**Delivers:** mass_line.py external validation, meta-framework as implicit constraint layer, external data source integration

### Phase 6: Integration & Extension
**Rationale:** Post-MVP enhancements including Feishu Bitable logging, caching layer, and API surface.
**Delivers:** feishu integration, LRU decision caching, optional FastAPI layer

### Phase Ordering Rationale

- **Router before agents:** Router determines which agents run and in what order — cannot build agents without this contract
- **Wise+Bias before Reverse/Second-Order:** Primary decision loop (80% usage) must work before conditional agents
- **Bias Scanner integration in Router before Wise Decider:** Pitfall 2 prevention — bias flags must alter routing, not just warn
- **Context management in Phase 1:** Cannot safely run multi-agent chains without bounded context (Pitfall 4)
- **Red line pre-filter in Phase 1:** Business constraints must exist above agent reasoning (Pitfall 3)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** External data source validation (urlebird.com TikTok metrics) — needs API verification and rate limit research
- **Phase 3:** First-Principles agent prompt engineering — unique methodology with sparse documentation
- **Phase 5:** 群众路线 external validation protocol — novel approach, no established patterns in existing tools
- **All phases:** LangGraph 0.2.x API stability — recommend validating against current documentation since WebSearch blocked

Phases with standard patterns (skip research-phase):
- **Phase 1:** Pydantic 2.x schema validation — well-documented, established patterns
- **Phase 2:** Basic 7-bias detection — standard cognitive bias research, well-documented
- **Phase 4:** FastAPI/structlog integration — standard Python web patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | LOW | Based on training data (2024); WebSearch blocked — cannot verify LangGraph 0.2.x, Python 3.14 incompatibility, or package version numbers against current documentation |
| Features | MEDIUM | Based on existing decision-cognition-skill v2.0 SKILL.md (internal source), supplemented by training knowledge; competitive analysis requires real product walkthroughs |
| Architecture | MEDIUM | Based on existing codebase analysis + general software engineering patterns; build order well-reasoned but Phase 5-6 are extrapolated |
| Pitfalls | LOW | Based on training data only; WebSearch blocked — cannot verify against real LangChain/CrewAI failure post-mortems or 2025-2026 production reports |

**Overall confidence:** LOW

### Gaps to Address

- **LangGraph version/API stability:** All stack recommendations require validation against current official docs once WebSearch is available
- **Competitive analysis:** Palantir, IBM Watson, ChatGPT/Claude feature comparison needs real product walkthroughs (scheduled but not yet executed)
- **Pitfall validation:** Agent routing loop patterns, bias conflict scenarios, and red line override failures should be validated against real multi-agent production failures
- **External validation source:** urlebird.com rate limits and data freshness need verification before Phase 5 commitment
- **Python version:** Python 3.14 ML package compatibility claims based on training knowledge — should verify with current package changelogs

## Sources

### Primary (HIGH confidence)
- None available — all primary sources (Context7, official docs, live API verification) blocked by WebSearch/WebFetch restrictions

### Secondary (MEDIUM confidence)
- Existing decision-cognition-skill v2.0 codebase analysis — direct code inspection, reliable
- General software engineering multi-agent patterns — training knowledge, broadly accurate

### Tertiary (LOW confidence)
- [Training data 2024] LangGraph 0.2.x architecture patterns — version numbers unverified
- [Training data 2024] CrewAI 0.80+ role-based patterns — version numbers unverified
- [Training data 2024] Python 3.14 ML package compatibility — likely accurate but unverified
- [Training data] Palantir/IBM Watson competitive analysis — 6-18 months stale
- [Training data] Multi-agent failure post-mortems — cannot cite specific cases without verification

**Recommendation:** Once WebSearch is available, priority verifications:
1. LangGraph current version and API stability (langgraph.github.io)
2. Python 3.11/3.12 vs 3.14 package compatibility (numpy, pydantic official docs)
3. Multi-agent orchestration failure patterns (LangChain blog, CrewAI GitHub issues)
4. Competitive product current feature sets (Palantir AIP, IBM Watson Discovery)

---
*Research completed: 2026-04-02*
*Ready for roadmap: yes*
