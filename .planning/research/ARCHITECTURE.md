# Architecture Research

**Domain:** Multi-Agent AI Decision Support Systems
**Researched:** 2026-04-02
**Confidence:** MEDIUM (based on existing codebase analysis + general architecture patterns)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      元框架层 (Meta-Framework)                       │
│  毛泽东思想四大支柱：实事求是 / 矛盾论 / 实践论 / 群众路线              │
├─────────────────────────────────────────────────────────────────────┤
│                      Agent 编排层 (Orchestration)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Router   │→ │ Wise     │→ │ Bias     │→ │ Reverse  │            │
│  │ 路由器   │  │ Decider  │  │ Scanner  │  │ Thinker  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       └─────────────┴──────┬─────┴─────────────┘                   │
│                            ↓                                        │
│                    ┌──────────────┐                                 │
│                    │ Arbitration  │                                 │
│                    │ 冲突仲裁器    │                                 │
│                    └──────┬───────┘                                 │
├───────────────────────────┼─────────────────────────────────────────┤
│                      输出层 (Output)                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Final Report │  │ JSON Struct  │  │ Action Items │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Boundary (Talks To) |
|-----------|----------------|---------------------|
| **Router (router-001)** | 场景分类、主要矛盾识别、Agent调度决策 | 输入层、Orchestration |
| **WiseDecider (wise-decider-001)** | 时间旅行测试、输得起原则、扑克思维 | Router输出、Arbitration |
| **BiasScanner (bias-scanner-001)** | 7大偏差检测、群众路线外部校验 | Router输出、Arbitration |
| **ReverseThinker (reverse-thinker-001)** | 三步防错法、地狱阶梯推演 | Router输出、Arbitration |
| **SecondOrderThinker (second-order-001)** | 影响地图、10-10-10法则 | Router输出、Arbitration |
| **FirstPrincipleThinker (first-principle-001)** | 类比陷阱识别、基本真理拆解、矛盾论 | Router输出、Arbitration |
| **Workflow (Orchestrator)** | 串联各Agent、处理冲突仲裁、格式化输出 | 所有Agent |
| **Meta-Framework** | 提供哲学指导原则（矛盾优先、实践验证） | 所有Agent（隐式约束） |

---

## Recommended Project Structure

```
decision-cognition/
├── agents/                      # 核心Agent实现
│   ├── router.py               # 决策路由器
│   ├── wise_decider.py        # 智慧决策师
│   ├── bias_scanner.py        # 偏差扫描师
│   ├── reverse_thinker.py     # 逆向思维师
│   ├── second_order.py         # 二阶思维师
│   ├── first_principle.py     # 第一性原理师
│   └── types.py                # 共享数据结构（dataclass定义）
│
├── framework/                   # 元框架层
│   ├── contradictions.py      # 矛盾论实现
│   ├── practice.py             # 实践论实现
│   └── mass_line.py            # 群众路线实现
│
├── workflow.py                 # Agent编排和工作流 orchestration
├── arbitration.py              # 冲突仲裁逻辑
├── output.py                   # 输出格式化
│
├── api/                        # API层（未来扩展）
│   └── routes.py
│
├── data/                       # 业务规则和数据
│   ├── biases.yaml            # 偏差定义配置
│   ├── red_lines.yaml         # 防错红线规则
│   └── mvp_templates.yaml     # MVP验证模板
│
└── tests/                      # 测试
    ├── agents/
    └── workflow/
```

### Structure Rationale

- **agents/**: 每个Agent独立实现，边界清晰，方便单独测试和替换
- **framework/**: 将毛泽东思想方法论抽离为独立模块，便于迭代优化
- **workflow.py**: 作为单一编排入口，协调所有Agent
- **data/**: 配置与代码分离，业务规则可热更新
- **api/**: 预留API扩展口，与CLI解耦

---

## Architectural Patterns

### Pattern 1: Pipeline Orchestration (当前实现)

**What:** Agent按固定顺序执行，Router决定调用哪些Agent
**When to use:** 决策流程相对确定、分支不多
**Trade-offs:**
- Pros: 简单清晰、易于理解和调试
- Cons: 无法并行、长链路延迟高

**Example:**
```python
# Router决定调度 → 顺序执行 → Arbitration合并结果
router_result = router.analyze(user_input)
agents_to_run = router_result.recommended_agents
for agent_id in agents_to_run:
    result = execute_agent(agent_id, user_input)
final = arbitration.merge(results)
```

### Pattern 2: Hierarchical Arbitration (冲突解决)

**What:** 冲突时按优先级规则决定听哪个Agent的
**When to use:** 多Agent结论冲突时
**Trade-offs:**
- Pros: 决策明确、避免无限争议
- Cons: 规则僵化、可能丢失有价值信息

**Example:**
```python
# 冲突仲裁规则优先级
RULES = [
    ("bias_high_risk", bias_scanner.take_precedence),   # 偏差高风险优先
    ("innovative", first_principle.take_precedence),     # 创新场景优先
    ("major", combine_all),                              # 重大决策综合分析
]
```

### Pattern 3: Meta-Framework as隐式约束

**What:** 哲学方法论不直接实现为Agent，而是作为所有Agent的约束条件
**When to use:** 方法论需要贯穿全局、但不适合独立为计算节点
**Trade-offs:**
- Pros: 不破坏Agent边界、方法论灵活演进
- Cons: 难以测试和验证、依赖团队共识

---

## Data Flow

### Request Flow

```
[User Input]
    ↓
[Router.analyze()] ──────────────────────────────────────┐
    ↓                                                    │
[Scene Classification]                                   │
    ↓                                                    │
[Agent Dispatch] ────────────────────────────────────────┼──→ [Arbitration]
    ↓                                                    │           ↓
[Parallel/ Sequential Agent Execution]                  │    [Final Decision]
    ↓                                                    │           ↓
[Agent Results] ─────────────────────────────────────────┘    [Action Output]
```

### State Management

```
WorkflowResult (immutable dataclass)
    ├── router_result: Optional[RouterResult]
    ├── decider_result: Optional[DecisionResult]
    ├── scanner_result: Optional[ScanResult]
    ├── reverse_result: Optional[ReverseResult]
    ├── second_order_result: Optional[SecondOrderResult]
    ├── first_principle_result: Optional[FirstPrincipleResult]
    ├── final_decision: str
    ├── final_action: str
    └── workflow_steps: List[str]
```

### Key Data Flows

1. **场景分类流程:** 用户输入 → Router分析 → 场景类型 + 推荐Agent列表
2. **Agent执行流程:** 推荐Agent → 顺序/并行执行 → 各Agent返回Result
3. **仲裁合并流程:** 多Agent结果 → 冲突检测 → 规则仲裁 → 最终决策
4. **输出格式化流程:** WorkflowResult → 格式化为Report/JSON → 用户可见输出

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 users/day | 单体Python脚本足够，workflow.py顺序执行 |
| 100-1K users/day | 引入缓存层（热门场景结果缓存）、Agent结果缓存 |
| 1K-10K users/day | Agent并行执行（asyncio）、热点预计算 |
| 10K+ users/day | 考虑拆分：Router服务化、各Agent独立部署、消息队列 |

### Scaling Priorities

1. **First bottleneck:** Router成为单点 → 水平扩展Router服务
2. **Second bottleneck:** Agent串行执行慢 → 并行化或异步队列化
3. **Third bottleneck:** 仲裁规则固化 → 规则引擎外置

---

## Anti-Patterns

### Anti-Pattern 1: Agent职责不清

**What people do:** 在多个Agent中重复实现相似逻辑（如多个Agent都做关键词匹配）
**Why it's wrong:** 代码重复、维护成本高、一致性难保证
**Do this instead:** 将通用逻辑抽取到 shared/utils.py 或 framework/ 层

### Anti-Pattern 2: 仲裁规则过于复杂

**What people do:** 在Arbitration中实现复杂的加权评分、贝叶斯推理
**Why it's wrong:** 失去可解释性、用户无法理解决策依据
**Do this instead:** 保持仲裁规则简单明确（if-else优先），或输出"冲突点由用户判断"

### Anti-Pattern 3: Meta-Framework变成装饰器

**What people do:** 将毛泽东思想作为函数装饰器硬编码到每个Agent
**Why it's wrong:** 框架入侵Agent逻辑、难以测试、哲学与方法论混杂
**Do this instead:** Meta-Framework作为设计原则文档+代码审查清单，不直接耦合

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Claude Code Agent | 直接调用 / 工作流脚本 | 当前通过Python subprocess |
| Feishu Bitable | Webhook / API轮询 | 记录决策日志到飞书 |
| 用户输入源 | CLI / API / Webhook | 当前是直接Python调用 |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Router ↔ Agent | dataclass传递 | Router输出作为Agent输入的一部分 |
| Agent ↔ Arbitration | dataclass返回 | 无直接依赖 |
| Workflow ↔ All | 方法调用 | 强耦合但可接受 |

---

## Build Order Implications

基于依赖关系的构建顺序：

```
Phase 1: 数据结构层
├── types.py (dataclass定义)
└── 验证: 单元测试

Phase 2: Router (必须先构建)
├── router.py
└── 验证: 场景分类准确性

Phase 3: 单Agent实现 (可并行)
├── wise_decider.py
├── bias_scanner.py
├── reverse_thinker.py
├── second_order.py
└── first_principle.py

Phase 4: Workflow编排
├── workflow.py
└── arbitration.py

Phase 5: 输出格式化
├── output.py (JSON/Report格式化)
└── 验证: 端到端测试

Phase 6: 集成与扩展
├── API层 (可选)
├── 缓存层 (可选)
└── 飞书集成 (可选)
```

**关键依赖:** Router必须在所有Agent之前完成，因为Router决定调度策略。

---

## Sources

- 现有代码库分析: `C:\Users\Administrator\.claude\skills\decision-cognition-skill\`
- 多Agent系统架构模式: 通用软件工程最佳实践
- 决策支持系统: 《Thinking, Fast and Slow》决策框架

---
*Architecture research for: 决策认知系统 v2.0*
*Researched: 2026-04-02*
