# Work Plan: ERP v2.2.0 - P0 问题修复

## TL;DR

> **目标**: 修复 Release v2.1.0 中审计发现的 6 个 P0 问题，提升代码质量和生产稳定性
> 
> **交付物**: 
> - P0-1: 凭证缺失时显式报错
> - P0-2: Cookie 过期检测
> - P0-3: 独立浏览器上下文
> - P0-4: sync_pipeline.py 测试
> - P0-5: workflow.py 测试
> - P0-6: requirements.txt
> 
> **估算工作量**: Medium (预计 3-4 小时)
> **并行执行**: YES - Wave 1 可并行

---

## Context

### 审计发现

| 问题 | 严重性 | 来源 |
|------|--------|------|
| P0-1: 凭证硬编码默认值 | P0 | concurrent_batch_v2.py L183/295 (需验证) |
| P0-2: Cookie 无过期检测 | P0 | sync_pipeline.py L366-375 |
| P0-3: concurrent_batch_sync.py 共享 context | P0 | L391-398 |
| P0-4: sync_pipeline.py 零测试 | P0 | 803行无pytest |
| P0-5: workflow.py run() 无测试 | P0 | L75-102 |
| P0-6: 无 requirements.txt | P0 | 依赖未锁定 |

### Metis 审查发现

| 发现 | 影响 |
|------|------|
| P0-1 可能在 concurrent_batch_v2.py 而非 sync_pipeline.py | 需预检确认文件 |
| concurrent_batch_v2.py vs concurrent_batch_sync.py 需确认 | 确定修复范围 |
| 缺少明确的验收标准 | 每个任务需定义清晰标准 |
| P0-3 修复可能涉及 CDP 端口架构变更 | 需评估范围 |

---

## Work Objectives

### Core Objective
修复 6 个 P0 问题，使 ERP 同步流水线达到生产就绪状态。

### Definition of Done

- [ ] 所有 6 个 P0 问题已修复
- [ ] 所有新增测试通过
- [ ] requirements.txt 可成功安装
- [ ] 无回归问题

### Must Have

- P0-1: 凭证缺失时显式 ValueError，清晰提示缺失的变量名
- P0-2: Cookie 过期检测，过期时 logger.warning 并拒绝使用
- P0-3: 每个 worker 独立 Browser Context，无共享状态
- P0-4: sync_pipeline.py 至少 5 个测试用例
- P0-5: workflow.py run() 方法分支 100% 覆盖
- P0-6: requirements.txt 包含所有依赖并锁定版本

### Must NOT Have

- 不添加新的并发功能（P0-3 仅修复 bug，不引入新架构）
- 不重构 workflow.py（仅添加测试）
- 不修改 CLI 参数（保持向后兼容）
- 不添加类型注解（除非 P0 修复必需）

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (decision_system 有 pytest)
- **Automated tests**: YES (TDD for all P0 fixes)
- **Framework**: pytest
- **Coverage requirement**: ≥80% for modified files

### QA Policy
每个任务包含:
- 1 个 Happy Path 场景
- 1 个 Failure 场景
- 证据保存到 `.sisyphus/evidence/`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (foundation - 可并行):
├── T1: P0-6 创建 requirements.txt [quick]
├── T2: P0-1 凭证缺失报错 [quick]
└── T3: 预检 - 确认 P0-1 文件位置 [quick]

Wave 2 (after T3 - 串行依赖):
├── T4: P0-2 Cookie 过期检测 [quick]
└── T5: P0-3 独立 Context 修复 [unspecified-high]

Wave 3 (after T4+T5 - 可并行):
├── T6: P0-4 sync_pipeline.py 测试 [unspecified-high]
└── T7: P0-5 workflow.py 测试 [unspecified-high]

Wave FINAL (verification):
├── F1: Plan compliance audit
├── F2: Code quality review
├── F3: Real manual QA
└── F4: Scope fidelity check
```

### Critical Path

```
T3 (预检) → T1 (P0-6) → T2 (P0-1) → T4 (P0-2) → T5 (P0-3) → T6/T7 (测试)
```

---

## TODOs

- [ ] 1. **T1: 创建 requirements.txt** (P0-6)

  **What to do**:
  - 扫描所有 .py 文件中的 import 语句
  - 提取依赖版本（从 pip show 或 pyproject.toml）
  - 创建 requirements.txt，格式: `package==version`
  - 包含: playwright, pydantic, pytest, requests, python-dotenv

  **Must NOT do**:
  - 不添加未使用的依赖
  - 不修改现有代码

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 文件扫描和文本生成，复杂度低
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3)
  - **Blocks**: T6, T7 (测试依赖此文件)
  - **Blocked By**: None

  **References**:
  - `scripts/sync_pipeline.py:L1-20` - import 语句
  - `decision_system/pyproject.toml` - 决策系统依赖

  **Acceptance Criteria**:
  - [ ] requirements.txt 存在
  - [ ] pip install -r requirements.txt 成功
  - [ ] 无 ImportError 在主流程

  **QA Scenarios**:

  ```
  Scenario: Happy path - requirements.txt 安装成功
    Tool: Bash
    Preconditions: requirements.txt 已创建
    Steps:
      1. cd "C:\Users\Administrator\Documents\GitHub\ERP"
      2. python -m venv .venv_test
      3. .venv_test\Scripts\activate
      4. pip install -r requirements.txt
    Expected Result: 所有依赖安装成功，无错误
    Evidence: .sisyphus/evidence/t1-requirements-install.txt

  Scenario: Failure - 缺少依赖检测
    Tool: Bash
    Preconditions: requirements.txt 存在
    Steps:
      1. grep "import" scripts/sync_pipeline.py | head -20
      2. 对比 requirements.txt
    Expected Result: 所有 import 的包都在 requirements.txt 中
    Evidence: .sisyphus/evidence/t1-dependency-check.txt
  ```

  **Commit**: YES
  - Message: `feat(dependencies): create pinned requirements.txt`
  - Files: `requirements.txt`

---

- [ ] 2. **T2: P0-1 凭证缺失显式报错** (P0-1)

  **What to do**:
  - 读取 concurrent_batch_v2.py L183/295 检查硬编码位置
  - 将 `os.getenv("ERP_PASSWORD", "123qazwsx")` 改为:
    ```python
    import os
    ERP_PASSWORD = os.getenv("ERP_PASSWORD")
    if not ERP_PASSWORD:
        raise ValueError("ERP_PASSWORD environment variable is required")
    ```
  - 对所有凭证变量（YUPOO_PASSWORD, ERP_USERNAME 等）应用相同模式
  - 添加测试验证缺失时报 ValueError

  **Must NOT do**:
  - 不提供硬编码回退值
  - 不改变现有 .env 文件位置

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要先验证文件位置，修改需谨慎
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3)
  - **Blocks**: None
  - **Blocked By**: T3 (确认文件位置后可开始)

  **References**:
  - `scripts/concurrent_batch_v2.py:L183,295` - 硬编码位置
  - `scripts/sync_pipeline.py:L362` - ERP_PASSWORD 读取

  **Acceptance Criteria**:
  - [ ] 凭证变量缺失时抛出 ValueError
  - [ ] 错误信息包含变量名
  - [ ] pytest tests/test_credentials.py 存在并通过

  **QA Scenarios**:

  ```
  Scenario: Happy path - 有效凭证运行成功
    Tool: Bash
    Preconditions: .env 包含所有凭证
    Steps:
      1. python -c "from sync_pipeline import get_credentials; c = get_credentials(); print(c['ERP_PASSWORD'])"
    Expected Result: 输出凭证值（已脱敏显示）
    Evidence: .sisyphus/evidence/t2-creds-valid.txt

  Scenario: Failure - 缺失凭证报错
    Tool: Bash
    Preconditions: 删除或注释 ERP_PASSWORD
    Steps:
      1. python -c "from sync_pipeline import get_credentials; get_credentials()"
    Expected Result: ValueError: ERP_PASSWORD environment variable is required
    Evidence: .sisyphus/evidence/t2-creds-missing.txt
  ```

  **Commit**: YES
  - Message: `fix(creds): fail explicitly on missing env vars`
  - Files: `sync_pipeline.py`, `concurrent_batch_v2.py`

---

- [ ] 3. **T3: 预检 - 确认 P0-1 文件位置**

  **What to do**:
  - 检查 concurrent_batch_v2.py L183/295 确认硬编码位置
  - 检查 sync_pipeline.py L265 是否也有硬编码
  - 检查其他脚本文件是否有类似问题
  - 输出完整的问题位置清单

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 只需 grep 和读取文件
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Parallel Group**: Wave 1 (with T1, T2)
  - **Blocks**: T2
  - **Blocked By**: None

  **References**:
  - `scripts/` - 所有脚本文件

  **Acceptance Criteria**:
  - [ ] 输出所有硬编码凭证位置
  - [ ] 确认 P0-1 修复范围

  **QA Scenarios**:

  ```
  Scenario: 搜索硬编码凭证
    Tool: Bash
    Preconditions: 无
    Steps:
      1. grep -rn "os.getenv.*PASSWORD" scripts/
      2. grep -rn "123qazwsx" scripts/
    Expected Result: 所有凭证读取位置和硬编码回退
    Evidence: .sisyphus/evidence/t3-creds-locations.txt
  ```

  **Commit**: NO (信息收集)

---

- [ ] 4. **T4: P0-2 Cookie 过期检测**

  **What to do**:
  - 读取 sync_pipeline.py L366-375 的 cookie 加载逻辑
  - 添加 expiry 检查:
    ```python
    for cookie in cookies:
        if 'expiry' in cookie:
            import time
            if cookie['expiry'] < time.time():
                logger.warning(f"Cookie {cookie.get('name')} expired at {cookie['expiry']}")
                continue  # 跳过过期 cookie
    ```
  - 添加 pytest 测试验证过期和有效 cookie 处理

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 逻辑简单明确
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: T3 (确认文件后)

  **References**:
  - `sync_pipeline.py:L366-375` - cookie 加载逻辑
  - `logs/cookies.json` - cookie 存储格式

  **Acceptance Criteria**:
  - [ ] 过期 cookie 被跳过
  - [ ] logger.warning 输出过期信息
  - [ ] pytest test_cookie_expiry.py 存在并通过

  **QA Scenarios**:

  ```
  Scenario: Happy path - 有效 cookie 加载成功
    Tool: Bash
    Preconditions: cookies.json 有有效 cookie
    Steps:
      1. python -c "from sync_pipeline import load_cookies; c = load_cookies('logs/cookies.json'); print(f'Loaded {len(c)} cookies')"
    Expected Result: 加载成功，无 warning
    Evidence: .sisyphus/evidence/t4-cookie-valid.txt

  Scenario: Failure - 过期 cookie 被跳过
    Tool: Bash
    Preconditions: cookies.json 包含过期 cookie
    Steps:
      1. python -c "from sync_pipeline import load_cookies; c = load_cookies('logs/cookies.json')" 2>&1 | grep -i "expired"
    Expected Result: warning 日志包含 "expired"
    Evidence: .sisyphus/evidence/t4-cookie-expired.txt
  ```

  **Commit**: YES
  - Message: `fix(cookie): add expiry validation`
  - Files: `sync_pipeline.py`

---

- [ ] 5. **T5: P0-3 独立 Browser Context**

  **What to do**:
  - 读取 concurrent_batch_sync.py L391-398
  - 修改为每个 worker 创建独立 context:
    ```python
    # 错误 (当前):
    browser = await p.chromium.connect_over_cdp(...)
    context = browser.contexts[0]  # 所有 worker 共享
    
    # 正确 (修复后):
    browser = await p.chromium.connect_over_cdp(...)
    context = await browser.new_context()  # 每个 worker 独立
    ```
  - 添加测试验证 context 独立性

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 并发逻辑复杂，需谨慎
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: T3

  **References**:
  - `logs/CONCURRENT_DEBUG_20260408.md` - 并发失败模式
  - `concurrent_batch_sync.py:L391-398` - 共享 context 位置

  **Acceptance Criteria**:
  - [ ] 每个 worker 有独立 context
  - [ ] 多 worker 同时运行无 SPA 路由踩踏
  - [ ] pytest test_concurrent_isolation.py 存在并通过

  **QA Scenarios**:

  ```
  Scenario: Happy path - 独立 context 创建成功
    Tool: Bash
    Preconditions: CDP Chrome 运行中
    Steps:
      1. python -c "from concurrent_batch_sync import Worker; w = Worker(0); print(w.context_id)"
      2. python -c "from concurrent_batch_sync import Worker; w1 = Worker(1); w2 = Worker(2); print(w1.context_id != w2.context_id)"
    Expected Result: 两个 worker 的 context_id 不同
    Evidence: .sisyphus/evidence/t5-context-isolation.txt

  Scenario: Failure - 共享 context 被检测
    Tool: Bash
    Preconditions: 修复前代码
    Steps:
      1. pytest tests/test_concurrent_isolation.py -v
    Expected Result: 测试失败，检测到共享 context
    Evidence: .sisyphus/evidence/t5-context-shared.txt
  ```

  **Commit**: YES
  - Message: `fix(concurrent): isolate browser context per worker`
  - Files: `concurrent_batch_sync.py`

---

- [ ] 6. **T6: P0-4 sync_pipeline.py 测试**

  **What to do**:
  - 创建 `tests/test_sync_pipeline.py`
  - 为 6 个 Stage 各编写测试:
    - test_stage1_extract()
    - test_stage2_prepare()
    - test_stage3_login()
    - test_stage4_navigate()
    - test_stage5_upload()
    - test_stage6_verify()
  - 使用 pytest-mock 模拟 CDP 和网络调用
  - 目标: 5+ 测试用例，覆盖关键路径

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要设计测试架构
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T7)
  - **Blocks**: None
  - **Blocked By**: T1 (requirements.txt)

  **References**:
  - `decision_system/tests/` - 测试模式参考
  - `scripts/sync_pipeline.py` - 803 行代码

  **Acceptance Criteria**:
  - [ ] 至少 5 个测试用例
  - [ ] pytest 运行成功
  - [ ] 覆盖所有 6 个 Stage

  **QA Scenarios**:

  ```
  Scenario: Happy path - 所有测试通过
    Tool: Bash
    Preconditions: 测试文件已创建
    Steps:
      1. cd "C:\Users\Administrator\Documents\GitHub\ERP"
      2. pytest tests/test_sync_pipeline.py -v
    Expected Result: 5+ tests passed, 0 failures
    Evidence: .sisyphus/evidence/t6-tests-pass.txt

  Scenario: Failure - Stage 5 upload 失败被正确捕获
    Tool: Bash
    Preconditions: mock upload 失败
    Steps:
      1. pytest tests/test_sync_pipeline.py::test_stage5_upload_failure -v
    Expected Result: 测试通过，验证错误处理
    Evidence: .sisyphus/evidence/t6-upload-failure.txt
  ```

  **Commit**: YES
  - Message: `test(sync): add stage-level tests with mocks`
  - Files: `tests/test_sync_pipeline.py`

---

- [ ] 7. **T7: P0-5 workflow.py 测试**

  **What to do**:
  - 创建 `decision_system/tests/test_workflow_run.py`
  - 测试 run() 方法的两个分支:
    - test_run_roi_blocked() - ROI < 0 时直接返回
    - test_run_dispatch_agents() - 正常 ROI 时调度 Agent
  - 使用 pytest-mock 模拟 router 和 agent 调用
  - 目标: 5+ 测试用例，100% 分支覆盖

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要理解 workflow 逻辑
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T6)
  - **Blocks**: None
  - **Blocked By**: T1 (requirements.txt)

  **References**:
  - `decision_system/workflow.py:L75-102` - run() 方法
  - `decision_system/tests/test_router.py` - 测试模式参考

  **Acceptance Criteria**:
  - [ ] 至少 5 个测试用例
  - [ ] ROI blocked 和 dispatch 分支都覆盖
  - [ ] pytest 运行成功

  **QA Scenarios**:

  ```
  Scenario: Happy path - ROI blocked 分支
    Tool: Bash
    Preconditions: 测试文件已创建
    Steps:
      1. pytest decision_system/tests/test_workflow_run.py::test_run_roi_blocked -v
    Expected Result: test passed, blocked reason logged
    Evidence: .sisyphus/evidence/t7-roi-blocked.txt

  Scenario: Happy path - dispatch 分支
    Tool: Bash
    Preconditions: 测试文件已创建
    Steps:
      1. pytest decision_system/tests/test_workflow_run.py::test_run_dispatch -v
    Expected Result: test passed, agents dispatched
    Evidence: .sisyphus/evidence/t7-dispatch.txt
  ```

  **Commit**: YES
  - Message: `test(workflow): add run() method test coverage`
  - Files: `decision_system/tests/test_workflow_run.py`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — oracle
  验证所有 Must Have 已实现，所有 Must NOT Have 未引入

- [ ] F2. **Code Quality Review** — unspecified-high
  运行 tsc --noEmit (如有)、pytest、lint 检查

- [ ] F3. **Real Manual QA** — unspecified-high
  执行每个 QA scenario，保存证据

- [ ] F4. **Scope Fidelity Check** — deep
  确保无 scope creep，无未预期的文件修改

---

## Commit Strategy

| Wave | Commit | Message |
|------|--------|---------|
| 1 | `feat(dependencies): create pinned requirements.txt` | requirements.txt |
| 1 | `fix(creds): fail explicitly on missing env vars` | sync_pipeline.py |
| 2 | `fix(cookie): add expiry validation` | sync_pipeline.py |
| 3 | `fix(concurrent): isolate browser context per worker` | concurrent_batch_sync.py |
| 3 | `test(sync): add stage-level tests with mocks` | tests/test_sync_pipeline.py |
| 3 | `test(workflow): add run() method test coverage` | decision_system/tests/test_workflow_run.py |

---

## Success Criteria

```bash
# 所有测试通过
pytest -v

# Requirements 安装成功
pip install -r requirements.txt

# 代码质量
python -m py_compile scripts/sync_pipeline.py
python -m py_compile scripts/concurrent_batch_sync.py
```
