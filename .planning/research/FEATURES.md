# Feature Research

**Domain:** AI Decision Support Systems (DSS)
**Researched:** 2026-04-02
**Confidence:** LOW

> **Research Constraint:** WebSearch/WebFetch/Context7 unavailable. Findings based on training knowledge (6-18 months stale). All claims require validation against current market offerings.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any AI decision support system. Missing these = product feels broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Scenario Classification** | Users need the system to understand what type of decision they're facing | MEDIUM | Must distinguish trivial/reversible/major/innovative |
| **Multi-Agent Orchestration** | Complex decisions require multiple analytical perspectives | HIGH | Agent coordination adds significant complexity |
| **Bias Detection** | Users know they have blind spots and want AI to catch them | MEDIUM | 7 basic cognitive biases are standard |
| **Recommendation Output** | Users want a clear action suggestion, not just analysis | LOW | "Just tell me what to do" |
| **Confidence/Probability Scoring** | Users want to know how sure the system is | MEDIUM | Calibrated confidence matters |
| **Decision Logging** | Users expect history for audit and learning | LOW | Basic persistence required |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but create real competitive moat.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **毛泽东思想 Methodology** | Unique Chinese-context framework that resonates with business culture | MEDIUM | 实事求是/矛盾论/实践论/群众路线 - not found in Western tools |
| **First-Principles + 矛盾论 Integration** | Ability to identify main conflict (主要矛盾) before analyzing | MEDIUM | Most Western tools skip conflict identification |
| **6 Specialized Agents** | Depth of analysis paths vs. single-LLM recommendation | HIGH | Router + Wise + Bias + Reverse + Second-order + First-principles |
| **2-Minute Decision Principle** | Built-in timeboxing prevents over-analysis paralysis | LOW | Differentiates from analysis-paralysis tools |
| **WH Business Rule Integration** | Domain-specific ROI rules (ROI为负止亏) embedded as hard constraints | MEDIUM | Competitors lack this domain knowledge |
| **群众路线 External Validation** | Real external perspective gathering (三类人: supporters/opponents/neutrals) | MEDIUM | Unique to this system - most tools only do internal reflection |
| **Time-Travel Testing** | "Will I regret this in 10 years?" framing | LOW | Novel emotional anchor not common in Western tools |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems or dilute focus.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time Data Integration** | "More data = better decisions" | Creates dependency on data pipelines; slows initial deployment | Start with user-provided context, add integrations after validation |
| **Full Multi-language Support** | "Should support English and Chinese" | i18n doubles maintenance burden; distracts from core value | Default Chinese, add English after PMF |
| **Mobile Push Notifications** | "Want to get decisions on my phone" | Context switching interrupts decision flow; not aligned with 2-min principle | Keep focus on async text-based interaction |
| **Decision Automation** | "Just make the decision for me" | Removes human agency; users don't trust fully automated decisions | Recommendation, not automation |
| **Unlimited Agent Paths** | "Why only 6 agents? More is better" | Complexity explosion; analysis paralysis returns | Stay disciplined with 6 agents |
| **External API Dependencies** | "Connect to CRM/ERP/etc." | Integration hell; creates fragile dependencies | Mock capability, implement after validation |

---

## Feature Dependencies

```
[Scenario Classification (Router)]
    └──requires──> [Decision Complexity Assessment]
                          └──requires──> [Agent Selection & Orchestration]

[Bias Detection (Bias-Scanner)]
    └──requires──> [群众路线 External Validation]
                          └──requires──> [Multi-Perspective Gathering]

[First-Principles Analysis]
    └──requires──> [矛盾论 Main Conflict Identification]
                          └──requires──> [Basic Assumption Decomposition]

[Second-Order Thinking]
    └──requires──> [First-Order Impact Mapping]

[Recommendation Output]
    └──requires──> [Confidence Scoring]

[WH Business Rules]
    └──requires──> [All Agent Outputs] (overlay constraint, not dependency)
```

### Dependency Notes

- **Scenario Classification requires Decision Complexity Assessment:** Cannot route without first understanding complexity level
- **Bias Detection enhances Recommendation Output:** Bias scan should feed into final recommendation with explicit flags
- **群众路线 External Validation requires Multi-Perspective Gathering:** Must gather 3 perspectives before validation
- **First-Principles requires 矛盾论:** Cannot重构 without first identifying the main conflict
- **WH Business Rules conflicts with Full Automation:** ROI rules are hard constraints that override agent recommendations when triggered

---

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed to validate the concept with real users.

- [ ] **Decision Router (router-001)** -- always-on, determines scenario type and complexity
- [ ] **Scenario Classification** -- trivial/reversible/major/innovative + emotion state
- [ ] **Wise Decider (wise-decider-001)** -- 80% usage rate, primary decision agent
- [ ] **Bias Scanner (bias-scanner-001)** -- 7 basic biases, self-scan only (no external validation)
- [ ] **Basic Recommendation Output** -- clear action suggestion with confidence
- [ ] **Decision Logging** -- store decisions for later review

### Add After Validation (v1.x)

Features to add once core is working and validated.

- [ ] **Reverse Thinker (reverse-thinker-001)** -- triggered for high-stakes decisions
- [ ] **Second-Order Thinker (second-order-001)** -- triggered for long-term projects
- [ ] **群众路线 External Validation** -- 3-person external check (v2.0 upgrade)
- [ ] **First-Principles (first-principle-001)** -- innovation scenarios (v2.0 upgrade)
- [ ] **WH Business Rule Integration** -- ROI constraints as hard overrides

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Multi-user Collaboration** -- team decision workflows
- [ ] **Data Source Integrations** -- CRM, ERP, spreadsheet connections
- [ ] **Decision Templates** -- pre-built flows for common business decisions
- [ ] **Mobile Access** -- phone notification and quick input
- [ ] **English Language Support** -- internationalization

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Decision Router (router-001) | HIGH | MEDIUM | P1 |
| Scenario Classification | HIGH | MEDIUM | P1 |
| Wise Decider (wise-decider-001) | HIGH | MEDIUM | P1 |
| Basic Bias Detection (7 biases) | HIGH | LOW | P1 |
| Recommendation Output | HIGH | LOW | P1 |
| Decision Logging | MEDIUM | LOW | P1 |
| Reverse Thinker (reverse-thinker-001) | MEDIUM | MEDIUM | P2 |
| Second-Order Thinker (second-order-001) | MEDIUM | MEDIUM | P2 |
| 群众路线 External Validation | HIGH | HIGH | P2 |
| First-Principles (first-principle-001) | MEDIUM | HIGH | P2 |
| WH Business Rules | HIGH | MEDIUM | P2 |
| Multi-user Collaboration | LOW | HIGH | P3 |
| Data Integrations | MEDIUM | HIGH | P3 |
| Mobile Access | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (core loop)
- P2: Should have, add when validated
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Palantir | IBM Watson | ChatGPT/Claude | Our Approach |
|---------|----------|------------|----------------|--------------|
| **Decision Framework** | Generic data analytics | Medical/legal domain focus | General conversation | 毛泽东思想 methodology |
| **Agent Specialization** | Multiple AI models | Expert systems | Single LLM | 6 specialized agents |
| **Bias Detection** | Data pattern bias | Domain-specific checks | Limited | 7 cognitive biases + 群众路线 |
| **Time Horizon** | Real-time + predictive | Historical analysis | Current session | 2-min to 10-year time travel |
| **Complexity Handling** | High (enterprise) | Medium | Low | Low-to-medium (2-min default) |
| **Domain Knowledge** | Generic | Medical/legal | General | WH influencer ROI specific |
| **Output Format** | Visualizations | Reports | Text | Action recommendation + reasoning |

**Key Insight:** Most Western AI tools focus on data-driven analysis. The 毛泽东思想 framework with 矛盾论 (main conflict identification) and 群众路线 (mass line external validation) is a unique differentiator for Chinese business culture that Western tools do not offer.

---

## Sources

- [Training Knowledge - LOW CONFIDENCE] Traditional DSS literature
- [Training Knowledge - LOW CONFIDENCE] Palantir/G走进AI platform capabilities
- [Training Knowledge - LOW CONFIDENCE] IBM Watson decision support case studies
- [Training Knowledge - LOW CONFIDENCE] Cognitive bias research (Tversky/Kahneman)
- [Internal - MEDIUM CONFIDENCE] Existing decision-cognition-skill v2.0 SKILL.md

> **Validation Required:** All external competitive analysis needs verification against current product offerings (2026 state). Schedule 2-hour competitive review with real product walkthroughs before finalizing.

---
*Feature research for: 决策认知系统 v2.0*
*Researched: 2026-04-02*
*Research mode: Ecosystem*
