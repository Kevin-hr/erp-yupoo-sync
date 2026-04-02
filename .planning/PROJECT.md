# 决策认知系统 v2.0 (Decision Cognition System v2.0)

## What This Is

智能化决策支持系统，融入毛泽东思想四大方法论支柱（实事求是、矛盾论、实践论、群众路线），通过六大 Agent（决策路由器、智慧决策师、偏差扫描师、逆向思维师、二阶思维师、第一性原理师）实现分级决策流程。服务于 WH 网红 ROI 追踪项目的重大决策场景。

## Core Value

帮助用户在复杂决策中快速识别主要矛盾，选择最优分析路径，输出可执行的决策建议。2分钟内完成琐事决策，长期项目启用完整 Agent 链路。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 实现决策路由器 (router-001)：场景分类、主要矛盾识别、Agent 调度
- [ ] 实现智慧决策师 (wise-decider-001)：时间旅行测试、输得起原则、扑克思维
- [ ] 实现偏差扫描师 (bias-scanner-001)：7大偏差检测、群众路线外部校验
- [ ] 实现逆向思维师 (reverse-thinker-001)：三步防错法
- [ ] 实现二阶思维师 (second-order-001)：影响地图、10-10-10法则
- [ ] 实现第一性原理师 (first-principle-001)：四步创新法
- [ ] 集成 WH 业务红线规则：ROI 为负止亏、新人 Model B 压测、术语规范、流量标准

### Out of Scope

- 独立的 Web/桌面 UI 界面
- 多语言国际化支持
- 移动端推送通知

## Context

### 项目背景

WH 网红 ROI 追踪系统需要处理大量业务决策：
- 网红合作决策（是否合作、给什么条件）
- 新市场开拓方向
- 样品寄送决策
- 团队管理决策
- 日常运营选择

### 现有资源

- 已在 `C:\Users\Administrator\.claude\skills\decision-cognition-skill\` 存在 Python 工作流脚本
- 决策认知系统 v1.0 基础架构已定义
- WH 项目业务红线规则已沉淀

### 技术环境

- Python 执行环境
- Claude Code Agent 编排能力
- 飞书 Bitable 集成能力

## Constraints

- **体量审计**: 禁止在 Git 仓库推送超过 10MB 的非必要二进制文件
- **脚本编码**: Windows PowerShell 5.1 环境下，所有 `.ps1/.bat` 脚本必须纯 ASCII/英文
- **脱敏审计**: 强制检查 API Key 及环境变量泄露风险

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 采用毛泽东思想元框架 | 从"拆解重构"升级为"从实际出发+抓主要矛盾"，更贴合业务实际 | — Pending |
| 默认极简，按需启用 Agent | 2分钟上限原则，避免过度分析 | — Pending |
| WH 业务红线仲裁优先 | ROI 为负必须止亏，保护业务底线 | — Pending |

---
*Last updated: 2026-04-02 after initialization from GEMINI.md*
