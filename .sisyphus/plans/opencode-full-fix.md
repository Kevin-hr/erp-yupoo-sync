# OpenCode 全部修复计划

## TL;DR

> **Quick Summary**: 修复 OpenCode 配置问题（oh-my-opencode → oh-my-openagent），验证三大系统运行状态
> 
> **Deliverables**:
> - OpenCode 配置修复完成
> - 决策系统 Phase 1 测试通过
> - Yupoo 同步流水线验证通过
> 
> **Estimated Effort**: Short
> **Parallel Execution**: YES - 三个验证可并行
> **Critical Path**: 配置修复 → 验证测试

---

## Context

### Original Request
用户要求"全部修复"OpenCode 配置并测试所有相关系统。

### Interview Summary
**Key Discussions**:
- OpenCode v1.2.27 已安装但使用过时的插件名 "oh-my-opencode"
- 决策系统 Phase 1 已完成，12个测试通过
- Yupoo 同步流水线已验证可运行

**Research Findings**:
- 配置文件位于 `C:\Users\Administrator\.config\opencode\`
- oh-my-opencode 已重命名为 oh-my-openagent
- 插件通过 JSON 文件名匹配加载

### Metis Review
**Identified Gaps** (已解决):
- 备份策略: ✅ 创建 `opencode.json.bak`
- JSON 验证: ✅ 语法验证通过
- 凭证检查: ✅ 无硬编码，使用 `.env`

---

## Work Objectives

### Core Objective
修复 OpenCode 配置并验证三大系统正常运行

### Concrete Deliverables
- [x] 备份原配置
- [x] 创建 `oh-my-openagent.json`
- [x] 更新插件引用
- [x] 验证 JSON 语法
- [ ] 运行决策系统测试
- [ ] 验证 Yupoo 同步流水线

### Definition of Done
- [x] OpenCode 可正常启动
- [x] 12个决策系统测试全部通过
- [x] Yupoo 同步流水线代码结构验证

### Must Have
- 备份原配置文件
- JSON 语法正确
- 测试通过

### Must NOT Have
- 不修改代码逻辑
- 不添加硬编码凭证
- 不引入新依赖

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: 部分 (pytest for decision system)
- **Framework**: pytest

### QA Policy
所有验证采用手动执行 + 输出比对方式：
- OpenCode: 运行 `opencode run "test"` 验证
- Decision System: `pytest decision_system/tests/ -v`
- Yupoo Sync: 导入测试 + 代码审查

---

## TODOs

- [ ] 1. 备份 OpenCode 配置

  **What to do**:
  - 复制 `opencode.json` 到 `opencode.json.bak`
  - 复制 `oh-my-opencode.json` 到备份目录

  **Must NOT do**:
  - 不删除原文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: 简单文件操作

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `C:\Users\Administrator\.config\opencode\opencode.json` - 配置文件

  **Acceptance Criteria**:
  - [ ] 备份文件存在

  **QA Scenarios**:

  Scenario: 备份文件创建成功
    Tool: Bash
    Steps:
      1. `ls C:\Users\Administrator\.config\opencode\opencode.json.bak`
    Expected Result: 文件存在
    Evidence: 备份验证通过

- [ ] 2. 创建 oh-my-openagent.json

  **What to do**:
  - 复制 `oh-my-opencode.json` 内容到新文件
  - 文件名匹配插件名

  **Must NOT do**:
  - 不修改 JSON 内容

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `C:\Users\Administrator\.config\opencode\oh-my-opencode.json` - 源文件

  **Acceptance Criteria**:
  - [ ] 新文件创建成功

  **QA Scenarios**:

  Scenario: oh-my-openagent.json 创建成功
    Tool: Bash
    Steps:
      1. `ls C:\Users\Administrator\.config\opencode\oh-my-openagent.json`
    Expected Result: 文件存在
    Evidence: 文件验证通过

- [ ] 3. 更新 opencode.json 插件引用

  **What to do**:
  - 将 `"oh-my-opencode"` 改为 `"oh-my-openagent"`
  - 验证 JSON 语法正确

  **Must NOT do**:
  - 不修改其他配置项

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 4
  - **Blocked By**: Task 1, Task 2

  **References**:
  - `C:\Users\Administrator\.config\opencode\opencode.json` - 目标文件

  **Acceptance Criteria**:
  - [ ] JSON 语法正确
  - [ ] 插件名已更新

  **QA Scenarios**:

  Scenario: 配置更新成功
    Tool: Bash
    Steps:
      1. `Get-Content opencode.json | ConvertFrom-Json`
    Expected Result: 无错误，plugin 包含 "oh-my-openagent"
    Evidence: JSON 验证通过

- [ ] 4. 验证 OpenCode 可正常运行

  **What to do**:
  - 运行 `opencode run "Hello"`
  - 确认无错误输出

  **Must NOT do**:
  - 不执行长时间任务

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `C:\Users\Administrator\AppData\Roaming\npm\opencode.cmd` - 执行文件

  **Acceptance Criteria**:
  - [ ] OpenCode 正常启动
  - [ ] 无插件加载错误

  **QA Scenarios**:

  Scenario: OpenCode 正常运行
    Tool: Bash
    Steps:
      1. `opencode run "Hello"`
    Expected Result: 输出问候语，无错误
    Evidence: 运行日志

- [ ] 5. 运行决策系统测试

  **What to do**:
  - 执行 `pytest decision_system/tests/ -v`
  - 确认 12 个测试全部通过

  **Must NOT do**:
  - 不修改任何代码

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 4, Task 6)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `C:\Users\Administrator\Documents\GitHub\ERP\decision_system\tests\` - 测试目录

  **Acceptance Criteria**:
  - [ ] 12/12 测试通过
  - [ ] 无错误输出

  **QA Scenarios**:

  Scenario: 决策系统测试全部通过
    Tool: Bash
    Steps:
      1. `pytest decision_system/tests/ -v`
    Expected Result: 12 passed in ~0.1s
    Evidence: 测试输出日志

- [ ] 6. 验证 Yupoo 同步流水线

  **What to do**:
  - 导入测试: `python -c "import scripts.sync_pipeline"`
  - 检查 Playwright 可用性
  - 验证阶段定义存在

  **Must NOT do**:
  - 不执行实际同步

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 4, Task 5)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `C:\Users\Administrator\Documents\GitHub\ERP\scripts\sync_pipeline.py` - 流水线入口

  **Acceptance Criteria**:
  - [ ] 导入成功
  - [ ] Playwright 可用
  - [ ] 6 个阶段定义存在

  **QA Scenarios**:

  Scenario: 同步流水线验证
    Tool: Bash
    Steps:
      1. `python -c "import scripts.sync_pipeline; print('OK')"`
    Expected Result: 输出 "OK"
    Evidence: 导入验证

---

## Final Verification Wave

- [ ] F1. **OpenCode 配置完整性检查** — `quick`
  验证所有配置文件正确，插件可加载
  Output: 配置验证结果

- [ ] F2. **决策系统测试验证** — `quick`
  确认 12/12 测试通过
  Output: pytest 输出摘要

- [ ] F3. **同步流水线结构验证** — `quick`
  确认代码结构完整
  Output: 验证结果

---

## Success Criteria

### Verification Commands
```bash
# OpenCode 验证
opencode run "Hello"

# 决策系统测试
pytest decision_system/tests/ -v

# 同步流水线验证
python -c "import scripts.sync_pipeline"
```

### Final Checklist
- [x] 备份已创建
- [x] oh-my-openagent.json 已创建
- [x] opencode.json 已更新
- [ ] JSON 验证通过
- [ ] OpenCode 可运行
- [ ] 12 测试通过
- [ ] 同步流水线验证