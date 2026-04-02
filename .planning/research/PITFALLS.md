# Pitfalls Research

**Domain:** Multi-agent AI Decision Support Systems
**Researched:** 2026-04-02
**Confidence:** LOW (WebSearch blocked - unable to verify with current sources; based on training data)

## Critical Pitfalls

### Pitfall 1: Agent Routing Loops

**What goes wrong:**
Agents enter infinite loops where Router -> Agent A -> Agent B -> Router -> Agent A... with no termination condition. Decision system hangs or produces exponentially growing context.

**Why it happens:**
No explicit cycle detection or maximum hop count enforced. Each agent assumes another will handle termination. Mao's "主要矛盾" (principal contradiction) identification fails to break ties when multiple agents claim priority.

**How to avoid:**
- Implement hard timeout per agent (30-60 seconds)
- Set maximum routing hops (e.g., 5) with circuit breaker
- Add explicit "no agent available" fallback that returns to user
- Define termination conditions in Router that override agent recommendations

**Warning signs:**
- Token count growing without bound in single decision
- Log shows same agent called 3+ times
- Response time exceeds 2-minute SLA for quick decisions

**Phase to address:**
Phase 1 (Router implementation) must include loop prevention

---

### Pitfall 2: Bias Detection Conflicts with Decision Outcome

**What goes wrong:**
Bias Scanner flags a recommended decision as containing bias (e.g., "confirmation bias detected"), but Wise Decider has already committed to the path. System produces contradictory outputs: "Recommendation: X" followed by "Warning: X has bias risk."

**Why it happens:**
Agents run sequentially without conflict resolution protocol. Bias Scanner serves as post-hoc checker rather than integrated input. No mechanism to weight or adjudicate conflicts between agents.

**How to avoid:**
- Bias Scanner output must feed into Router's scenario classification BEFORE Wise Decider runs
- Define explicit conflict resolution: bias flag = require additional evidence OR route to Reverse Thinker
- Build "bias-rebuttal" loop: when bias detected, automatically invoke Reverse Thinker before final output

**Warning signs:**
- Bias Scanner logs show warnings but decision proceeds unchanged
- User sees multiple conflicting recommendations
- Phase 1/2 test cases reveal sequential (not parallel) agent execution

**Phase to address:**
Phase 3 (Bias Scanner) integration design - requires cross-agent protocol definition

---

### Pitfall 3: Business Rule Override Failure

**What goes wrong:**
System recommends a decision that violates WH ROI红线 (business red lines) - e.g., approving collaboration with negative expected ROI. The 6-agent system produces sophisticated reasoning that overrides hard business constraints.

**Why it happens:**
Business rules treated as "one of many inputs" rather than immutable constraints. Agents can theoretically recommend anything. No "guardrail layer" that exists above agent reasoning.

**How to avoid:**
- Implement ROI红线 as pre-filter: impossible for any agent to recommend ROI-negative paths
- Add "业务红线仲裁层" as first check in Router - reject/simplify scenarios that violate red lines
- Log all override events for audit
- Never allow agent reasoning to override hard constraints, even with sophisticated justification

**Warning signs:**
- Business red lines only checked after full agent chain completes
- No error/exception when agent recommends violating红线
- Testing reveals recommendations that contradict business rules

**Phase to address:**
Phase 1 (Router) - red line pre-filter must be implemented before any agent chain

---

### Pitfall 4: Context Window Overflow

**What goes wrong:**
Long-running decision threads accumulate context from all 6 agents, exceeding LLM context limits. Later agents receive truncated context, produce incomplete analysis, or repeat previous reasoning.

**Why it happens:**
Each agent appends to shared context without summarization. Multi-turn decisions (10+ minutes) accumulate prompts/responses from all agents. No context compression or history truncation strategy.

**How to avoid:**
- Implement rolling summarization: compress agent outputs after each phase
- Set maximum context budget (e.g., 32K tokens per decision)
- Design agents to output structured JSON with fixed schema, not prose
- Enable context-refresh: restart fresh context for sub-decisions

**Warning signs:**
- Token count approaching model limits in test runs
- Later agents produce repetitive or incomplete responses
- Context.json files growing unbounded

**Phase to address:**
Phase 1 (Router) - context management strategy must be defined before multi-agent design

---

### Pitfall 5: Parallel vs Sequential Execution Ambiguity

**What goes wrong:**
Design assumes agents can run in parallel (speed benefit), but they actually have data dependencies requiring sequential execution. Implementation runs them parallel anyway, producing inconsistent results based on race conditions.

**Why it happens:**
Architecture diagram shows "all 6 agents" but doesn't specify execution order. Phase dependencies unclear: e.g., Reverse Thinker needs Wise Decider output, but diagram shows them side-by-side.

**How to avoid:**
- Document explicit data flow: which agent outputs feed into which agent inputs
- Implement sequential execution with checkpointing by default; optimize to parallel only after verified safe
- Create "agent compatibility matrix" showing which pairs can execute in parallel
- Use explicit async/await with dependency declarations

**Warning signs:**
- Agent outputs vary between runs with same inputs
- Timing-dependent bugs in test suite
- No clear "agent A output -> agent B input" documentation

**Phase to address:**
Phase 2 (Agent Design) - execution order and dependencies must be explicit in architecture

---

### Pitfall 6: First Principles becomes Over-Engineering

**What goes wrong:**
First Principles Agent (第一性原理师) is invoked for every decision, including trivial ones. Users wait 5+ minutes for "innovative solutions" to "should I send this sample today." System violates 2-minute decision principle.

**Why it happens:**
No cost-benefit routing. No "decision weight" classification. Router doesn't distinguish between "major strategic decision" (10+ minutes appropriate) vs "daily operational decision" (2 minutes max).

**How to avoid:**
- Implement decision urgency classification in Router: A (2min max), B (10min), C (strategic, 30min+)
- Only invoke First Principles for Type C decisions
- Default routing for Type A: direct pattern match to previous similar decisions
- Track "over-engineered" decisions: when Type A takes >5 minutes

**Warning signs:**
- Average decision time exceeds 2 minutes for routine decisions
- First Principles agent invoked for sample-shipping decisions
- User reports "I asked a simple question and waited 10 minutes"

**Phase to address:**
Phase 1 (Router) - decision classification must gate agent invocation

---

### Pitfall 7: Mass Line External Validation Never Executes

**What goes wrong:**
Bias Scanner's "群众路线外部校验" (external validation via mass line) is designed but never actually calls external data. System validates against internal assumptions only, defeating the purpose.

**Why it happens:**
External validation marked as "optional enhancement." No integration points defined. Assumes external data sources will be added later. Validation becomes empty ritual.

**How to avoid:**
- Define minimum viable external validation: 1 data point (e.g., urlebird.com for TikTok metrics) as Phase 1 requirement
- Treat "no external data" as degraded mode, not success
- Require external validation output to explicitly change bias score
- Track "validation coverage" - % of decisions with actual external checks

**Warning signs:**
- External validation logs show null/empty responses
- Bias Scanner output never changes based on external data
- Integration marked "TODO" for >2 phases

**Phase to address:**
Phase 3 (Bias Scanner) - external validation must have defined data source in Phase 1

---

### Pitfall 8: Agent Persona Creep

**What goes wrong:**
Each agent (Wise Decider, Reverse Thinker, etc.) accumulates system prompts and examples until they become slow, inconsistent, and contradictory. Agent A says "consider X" while Agent B says "X is irrelevant."

**Why it happens:**
No unified agent prompt template. Each agent grows its system prompt independently. "Just one more example" syndrome. No cross-agent prompt review.

**How to avoid:**
- Maintain single source of truth for agent personas in config
- Define shared "decision-making vocabulary" all agents must use
- Cap system prompt length per agent (e.g., 2K tokens max)
- Quarterly prompt audit: find contradictions between agent instructions

**Warning signs:**
- Agent outputs contradict each other on same input
- System prompts exceed 4K tokens per agent
- "Add few-shot example" commits without reviewing existing examples

**Phase to address:**
Phase 2 (Agent Implementation) - establish prompt governance before agent development

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-code business rules in Router | Fast to implement | Rules become scattered, untestable | Never - use config file |
| Skip external validation | Faster initial build | Bias detection unreliable | Only for Phase 1 MVP, must add in Phase 2 |
| Sequential agent execution | Simple implementation | Slow for parallelizable tasks | Default until parallelism verified safe |
| JSON output without schema validation | Faster iteration | Silent failures on malformed output | Only in early prototyping |
| Single context thread | Simpler state management | Context overflow in long sessions | Must implement compression by Phase 2 |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| 飞书 Bitable | Writing decisions back without validation | Decisions go to "pending" table, require human confirmation |
| WH ROI Tracker | Using outdated ROI thresholds | Pull thresholds from config on every decision, not cached |
| TikTok metrics API | Not handling rate limits | Implement exponential backoff, queue requests |
| Claude API | No timeout on agent calls | Hard timeout + circuit breaker per agent |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| All 6 agents in chain | 10+ minute response time | Route based on decision type; only invoke needed agents | Every non-strategic decision |
| No context compression | Context grows unbounded | Rolling summarization every 3 agent calls | Decisions > 10 minutes |
| Synchronous logging | I/O blocking decision flow | Async logging with buffer flush | High-frequency decisions |
| No decision caching | Same question repeated wastes API calls | LRU cache for decision patterns | Repeated question patterns |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging full decision context | Business strategy leaked if logs exposed | Sanitize logs; never log ROI calculations or competitor info |
| Storing API keys in agent prompts | Key exposure in logs/context | Use environment variables; never in system prompts |
| No audit trail for decisions | Regulatory/business risk | Every decision logged with timestamp, input hash, output hash |
| Allowing agent to modify red lines | Business constraint bypass | Red lines in immutable config, not editable by agents |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No explanation of decision path | User doesn't trust output | Include "which agents contributed" summary |
| Verbose multi-agent output | Takes longer to read than decide | Cap total output: 500 words max for Type A |
| Asking user for input mid-decision | Breaks flow; unclear what to answer | Collect all user input at decision start |
| Different output format per agent | Inconsistent presentation | Single unified output template for all agents |

---

## "Looks Done But Isn't" Checklist

- [ ] **Router:** Often missing actual agent scheduling logic - verify with test: does it call correct agent?
- [ ] **Bias Scanner:** Often returns "bias detected" without changing recommendation - verify: does bias flag alter output?
- [ ] **Business Red Lines:** Often implemented as suggestions, not constraints - verify: does system reject red-line violations?
- [ ] **External Validation:** Often returns null without failing - verify: does "no data" trigger fallback behavior?
- [ ] **Context Management:** Often doesn't actually compress - verify: does token count stay bounded in 10-decision session?

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Agent routing loop | MEDIUM | Kill session; add hop counter; redeploy router |
| Context overflow | LOW | Clear context; implement summarization; restart |
| Bias conflict | MEDIUM | Roll back decision; fix conflict resolution protocol; re-run |
| Red line violation | HIGH | Audit all decisions since last valid state; implement guardrail |
| External validation failure | LOW | Use cached fallback data; alert on prolonged failure |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Agent routing loops | Phase 1: Router | Unit test with mock agents; verify max hops enforced |
| Bias conflicts | Phase 1: Router + Phase 3: Bias Scanner | Integration test: bias flag must alter routing |
| Business rule override | Phase 1: Router | Negative test: ROI-negative input must return error |
| Context overflow | Phase 1: Architecture | Load test: 10 sequential decisions; verify token growth bounded |
| Parallel/sequential ambiguity | Phase 2: Agent Design | Documented dependency matrix before implementation |
| First Principles over-use | Phase 1: Router | Decision type classification must gate First Principles |
| Mass Line never executes | Phase 3: Bias Scanner | Integration test: external endpoint returns data or graceful fallback |
| Agent persona creep | Phase 2: Agent Implementation | Prompt length cap enforced in code review |

---

## Sources

- Training data (2024-2025): Multi-agent system architecture patterns, LangChain multi-agent patterns, AI decision support system failures
- Confidence: LOW - WebSearch blocked; unable to verify with current sources

**Recommendation:** Once WebSearch is available, verify these pitfalls against:
- Recent LangChain/CrewAI multi-agent failure post-mortems
- AI agent orchestration reliability reports (2025-2026)
- Decision support system case studies in production

---
*Pitfalls research for: Multi-agent AI Decision Support Systems*
*Researched: 2026-04-02*
