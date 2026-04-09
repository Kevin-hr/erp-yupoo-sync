# ERP 表单并行化方案 (ERP Form Parallelization)

> 解决"复制模板"串行瓶颈，实现 N 个 Tab 并行上传

---

## 1. 问题根因分析 (Root Cause)

### 串行瓶颈位置

```
当前流程（串行）:
Worker-1: [点击复制] → [等待表单加载] → [上传图片] → [保存] → 下一个
Worker-2:                                          [点击复制] → [等待] → ...
Worker-3:                                                           [点击复制] → ...
```

**瓶颈**: 点击"复制"按钮 → 浏览器渲染空白表单 → 上传图片 → 保存，这个流程中"点击复制"是关键串行点，因为 ERP 只能通过点击按钮触发，无法用 URL 直接打开商品表单。

### CDP / Playwright Tab 机制

| 机制 | 说明 | 并行能力 |
|------|------|----------|
| `context.new_page()` | 在同一 Context 创建新 Tab | ✅ 同一 Cookie，会话共享 |
| `browser_contexts[0].new_page()` | CDP 模式下新建 Tab | ✅ 复用登录态 |
| JavaScript `window.open()` | JS 打开新 Tab | ⚠️ 受浏览器弹窗拦截 |
| CDP `Target.createTarget` | 浏览器级创建 Tab | ✅ 最可靠，可批量创建 |

---

## 2. 并行化方案 (Parallelization Strategy)

### 方案选型：Pre-create N Tabs + Worker Pool

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser Context (共享登录态)                   │
│                                                                  │
│   Tab-0 (Navigator)     Tab-1       Tab-2       ...    Tab-N     │
│   [商品列表页]          [表单A]     [表单B]               [表单N] │
│      ↓批量点击复制       ↑            ↑                     ↑    │
│                      Worker-1    Worker-2              Worker-N │
│                      绑定Tab-1    绑定Tab-2             绑定Tab-N │
│                      [上传图片]   [上传图片]             [上传图片]│
│                      [保存]       [保存]                [保存]   │
└─────────────────────────────────────────────────────────────────┘
```

### 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Tab 创建方式 | `context.new_page()` 批量创建 | Playwright 原生，无需 CDP |
| 表单初始化 | JS 批量点击"复制"按钮 | 一次 DOM 操作打开 N 个表单 |
| Worker 绑定 | Tab Pool + Semaphore | 每个 Worker 绑定一个 Tab，互不干扰 |
| 同步机制 | `asyncio.gather()` + `asyncio.Semaphore(N)` | 控制并发数，防止 ERP 风控 |
| 登录态 | `cookies.json` 注入 + CDP Cookie 提取 | 复用已有登录 |

---

## 3. 执行流程 (Execution Flow)

### Phase 0: 预热 (Pre-warm)
```
1. 连接/启动浏览器 → 获取 Context
2. 注入登录 Cookie（CDP 提取 或 cookies.json）
3. 导航到商品列表页
```

### Phase 1: 预创建 N 个 Tab (Pre-create Tabs)
```
1. 在 Navigator Tab (Tab-0) 执行 JS：
   → 找到商品列表中前 N 个模板商品的"复制"按钮
   → 使用 dispatch_event 逐个触发 click（或批量）
   → 等待每个新 Tab 自动打开（ERP 打开商品表单在新 Tab）
2. 等待所有表单 Tab 完全加载
```

### Phase 2: 启动 Worker Pool (Start Workers)
```
1. 创建 N 个 Worker 任务
2. 每个 Worker:
   a. 从 Tab Pool 申请一个可用 Tab
   b. 等待 Tab 表单 ready（wait_for_selector）
   c. 填充品牌名 + 商品名
   d. 格式化描述（DescriptionEditor）
   e. 上传图片（ImageUploader）
   f. 保存并验证（Verifier）
   g. 将 Tab 标记为完成，释放回 Pool
```

### Phase 3: 清理 (Cleanup)
```
1. 关闭所有表单 Tab
2. 保留 Navigator Tab（可选关闭）
3. 导出执行结果
```

---

## 4. 并行度设计 (Concurrency Design)

### 并发参数

| 参数 | 值 | 理由 |
|------|------|------|
| `MAX_TABS` | 5 | ERP 并发限制 ≤ 3，保留 2 个余量 |
| `TAB_CREATION_BATCH` | 3 | 每批创建 3 个 Tab，避免瞬时请求过多 |
| `TAB_CREATION_DELAY` | 2s | 相邻 Tab 创建间隔 2s（ERP 渲染需要时间）|
| `WINDOW_OPEN_TIMEOUT` | 15s | 等待新 Tab 打开的超时 |

### Tab 状态机

```
      ┌─────────────┐
      │   CREATED   │ ← context.new_page()
      └──────┬──────┘
             │ wait_for_load_state
      ┌──────▼──────┐
      │  LOADING    │
      └──────┬──────┘
             │ form rendered
      ┌──────▼──────┐
      │  AVAILABLE  │ ← Worker 可以开始
      └──────┬──────┘
             │ worker.acquire()
      ┌──────▼──────┐
      │   WORKING   │
      └──────┬──────┘
             │ done
      ┌──────▼──────┐
      │   CLOSED   │ ← Tab 关闭或释放
      └─────────────┘
```

---

## 5. 实现架构 (Implementation)

### 文件结构

```
scripts/
├── erp_tab_manager.py      ← 核心：Tab 预创建 + Worker Pool 管理
├── sync_pipeline.py        ← 现有主流水线（Stage 4/5 改为调用 Tab Manager）
└── concurrent_batch_sync.py ← 批量并发（改造为使用 Tab Manager）

核心类：
  ERPFormTabManager          - 主管理器：预创建 Tab、管理 Pool
  TabSlot                    - 单个 Tab 的状态封装
  FormWorker                 - Worker：绑定 Tab，执行上传
```

### TabManager API

```python
class ERPFormTabManager:
    async def precreate_tabs(context, browser, n=5)
        # 在 Navigator Tab 中批量触发"复制"按钮
        # 等待 N 个表单 Tab 全部打开并加载完成

    async def get_available_tab(context) -> Page
        # Worker 获取可用 Tab（从 Pool 取出）
        # 无可用 Tab 时等待（await）

    async def wait_all_ready(context, n)
        # 等待所有 N 个预创建的 Tab 状态变为 AVAILABLE
```

### Worker 执行单元

```python
class FormWorker:
    # 每个 Worker 独立执行：
    # 1. await tab_manager.get_available_tab()  → 获取一个 Tab
    # 2. await self.fill_form(tab, product)    → 填充表单
    # 3. await self.upload_images(tab, urls)   → 上传图片
    # 4. await self.verify_and_save(tab)       → 保存验证
    # 5. await tab_manager.release_tab(tab)     → 释放 Tab
```

---

## 6. 风险与缓解 (Risks & Mitigations)

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| ERP 检测并发行为 | 🔴 高 | 并发数 ≤ 3，Tab 创建间隔 2s |
| Tab 打开失败（弹窗拦截）| 🟡 中 | 使用 `dispatch_event` 代替直接 click；添加超时重试 |
| 表单加载不一致 | 🟡 中 | `wait_for_selector` 确认表单元素出现 |
| Cookie 失效 | 🟡 中 | CDP 优先提取最新 Cookie；fallback 到 cookies.json |
| 批量创建 Tab 过多 | 🔴 高 | Semaphore 控制并发上限；分批创建 |

---

## 7. 性能对比 (Performance Comparison)

| 指标 | 串行（当前）| 并行（目标）| 提升 |
|------|------------|-------------|------|
| 10 个商品总耗时 | ~10 × 120s = 1200s | ~3 × 40s + overhead = 150s | **8x** |
| Tab 创建开销 | 0 | ~10s (3批×2s + 加载) | - |
| Worker 阻塞等待 | 每个任务等上一个完成 | 无（Pool 机制）| - |

> 注：实际提升受 ERP 服务器响应时间和风控策略影响

---

## 8. 下一步行动 (Next Steps)

- [ ] **P0**: 实现 `erp_tab_manager.py` 核心逻辑
- [ ] **P1**: 改造 `concurrent_batch_sync.py` 使用 Tab Manager
- [ ] **P2**: 改造 `sync_pipeline.py` Stage 4/5 调用 Tab Manager
- [ ] **P3**: 添加 Tab 健康检查 + 自动重建机制
- [ ] **P4**: 集成到飞书 Base 任务看板（tblM6A0Cpzz6gFEi）
