---
name: decision-cognition
description: Optimized ERP Project AI Rulebook (v2.1).
---

# GEMINI.md — ERP Project Rulebook (AI 规则手册 v2.1)

## §1 Hard Constraints (硬性红线)

| 领域 | 核心规则 (Absolute Rules) |
| :--- | :--- |
| **写作** | 所有文档/注释必须包含 **中文标注**；`.ps1 / .bat` 脚本严禁中文字符 (ASCII-ONLY)。 |
| **框架** | 结构化分析遵守 **MECE**；执行计划包含 **5W1H** (Who/What/Where/When/Why/How)。 |
| **审计** | 严禁推送 >10MB 二进制文件；强制检查 API Key/环境变量泄露风险。 |
| **ERP 业务** | 图片数 ≤ 14 (第15位预留)；并发数 ≤ 3；Yupoo/ERP 禁用共享 Cookie。 |
| **操作** | 严禁终端脚本冷启动浏览器，必须使用 `browser_subagent`；**见验证码立即停报**。 |

---

## §2 Decision Cognition System (决策认知系统)

> **原则：实事求是 · 矛盾论 · 实践论 · 群众路线**

### [Quick Router] (决策路由)
1. **主要矛盾**：决策前先问“当前核心阻碍是什么？”
2. **可逆性**：
    - **可逆/低成本** → `wise-decider` (快速试错/扑克思维)。
    - **不可逆/高成本** → `bias-scanner` (偏差扫描/冷处理) + `reverse-thinker` (逆向防错)。
3. **创新突破**：回到 `first-principle` (第一性原理)，拆解本质，重构方案。

### [Conflict Arbitration] (冲突仲裁)
- **偏差扫描核心**：大脑会骗你，群众路线(外部校验)优先。
- **逆向优先**：先保证“不死”(不封号/断流)再追求效果。
- **动态更新**：基于 `bayes-updater` (贝叶斯) 随新证据持续修正判断。

---

## §3 Implementation Standard (执行标准)

- **可视化**：开始必有计划，每步必有进度(%)，完成必有截图验证。
- **闭环思维**：凡事有交代，件件有着落，事事有回音。
- **工业级自动化**：优先考虑高并发、云原生流水线，消除人机耦合。

> **一句话总结**：默认智慧决策，感觉不对偏差扫描，大额投入逆向思维，长期项目二阶思维，创新突破第一性原理。2分钟内搞不定听直觉。
