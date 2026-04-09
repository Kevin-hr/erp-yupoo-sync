# 架构设计：ERP极限并发v2

> **问题根因**：10个worker共享1个CDP `browser_context` → 共享ERP `page` → 互相踩踏 → 一次只能成功1个

---

## 核心决策

| 维度 | 方案A | 方案B | 方案C | **推荐** |
|------|-------|-------|-------|---------|
| **架构模式** | 共享Browser+独立Context | 独立Browser进程池 | 预创建Form池+Worker取用 | **方案C** |
| **ERP隔离** | 共享Context各自new_page | 各自launch新Browser | 预开N个Form Tab，Worker导航 | **方案C** |
| **并发度** | 3-5（ERP风控） | 10（Yupoo独立） | 10（Form池隔离） | **方案C** |
| **复杂度** | 低 | 中 | 中 | - |
| **踩踏风险** | 高（共享资源） | 低（完全隔离） | 极低（Form池路由） | - |

### 方案C推荐理由
- **完全隔离**：每个worker = 独立Browser + 独立Context + 独立Page
- **串行破解**：预创建N个ERP Form Tab，Worker通过**Tab索引路由**取用而非点击"复制"
- **最大并发**：Yupoo提取与ERP上传分离，Yupoo提取可10并发，ERP上传限3防风控

---

## Worker隔离方案

### 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Master Orchestrator                             │
│                  (concurrent_batch_sync_v2.py)                     │
└──────────────┬──────────────────┬──────────────────┬──────────────────┘
               │                  │                  │
        ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │  Worker-1   │    │  Worker-2   │    │  Worker-N   │
        │─────────────│    │─────────────│    │─────────────│
        │ Browser#1   │    │ Browser#2   │    │ Browser#N   │
        │  Context#1  │    │  Context#2  │    │  Context#N  │
        │ Page_Yupoo  │    │ Page_Yupoo  │    │ Page_Yupoo  │
        │ Page_ERP    │    │ Page_ERP    │    │ Page_ERP    │
        └─────────────┘    └─────────────┘    └─────────────┘
               │                  │                  │
               ▼                  ▼                  ▼
        ┌─────────────────────────────────────────────────────────┐
        │              ERP Form Tab Pool (预创建)                  │
        │  Tab_1: /product/edit/xxx  Tab_2: /product/edit/yyy  ... │
        └─────────────────────────────────────────────────────────┘
```

### 关键约束

| 约束 | 说明 |
|------|------|
| **1 Worker = 1 Browser** | 绝对禁止共享Browser实例 |
| **1 Worker = 1 Context** | 绝对禁止共享BrowserContext |
| **ERP Page独立获取** | Worker启动时从Form池**导航**到目标Tab，不点击"复制" |
| **Yupoo Page独立** | 每个Worker直连`/gallery/{id}`，不共享 |

---

## CDP连接策略

### 方案：Multi-CDP连接池

```python
# 架构：每个Worker启动时创建自己的CDP连接
# 不共享同一个 CDP endpoint

class WorkerSession:
    """单个Worker的完全隔离会话"""
    def __init__(self, worker_id: int, cdp_port_start: int = 9222):
        self.worker_id = worker_id
        # 方式1: 独立Chrome实例（推荐，完整隔离）
        # 每个Worker启动独立Chrome进程
        # chrome.exe --remote-debugging-port=9{worker_id:03d}
        # 例如 Worker-1: 9222, Worker-2: 9223, ...

        # 方式2: 复用已有CDP，分配独立Context
        # browser.connect_over_cdp() → new_context() → new_page()

    async def launch(self):
        # Worker独立启动，不依赖共享资源
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.yupoo_page = await self.context.new_page()
            self.erp_page = await self.context.new_page()
```

### CDP连接选择

| 方案 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| **独立Chrome进程池** | 每个Worker启动独立Chrome，`--remote-debugging-port={port}` | 完全隔离，无任何共享资源 | 资源消耗大（内存/CPU） |
| **单Chrome多Context** | 1个Chrome，Worker分配不同Context | 资源轻量 | Context之间可能有隐式资源竞争 |
| **推荐：独立进程** | Worker-1用Port 9222，Worker-2用9223，... | 极简隔离，符合Playwright最佳实践 | 需预热N个Chrome进程 |

### 端口分配

| Worker | CDP Port | Browser启动命令 |
|--------|----------|----------------|
| 1 | 9222 | `chrome --remote-debugging-port=9222 ...` |
| 2 | 9223 | `chrome --remote-debugging-port=9223 ...` |
| N | 9221+N | `chrome --remote-debugging-port=9221+N ...` |

---

## ERP表单串行破解

### 问题根源

```
ERP "复制模板" = 点击按钮 → 后端创建新记录 → 返回表单页面
                              ↑
                        锁 + 唯一性约束 → 必须串行
```

### 破解方案：Form Pool（表单池）

```
┌────────────────────────────────────────────────────────────┐
│  预创建阶段（串行，1次）                                     │
│  ─────────────────────────────────────────────────────────  │
│  Master打开ERP → 循环点击"复制" N次 → 生成N个Form Tab         │
│  每个TabURL: /product/edit/{unique_id}                      │
│  Tab Pool: ["Tab_1_URL", "Tab_2_URL", ..., "Tab_N_URL"]     │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  Worker执行阶段（并行，无竞争）                              │
│  ─────────────────────────────────────────────────────────  │
│  Worker_i 从池取 Tab_i_URL → erp_page.goto(Tab_i_URL)      │
│  执行: 填充品牌/品名 → 上传图片 → 格式化描述 → 保存           │
│  ✅ 无点击"复制"操作，✅ 无竞争，✅ 真正并行                  │
└────────────────────────────────────────────────────────────┘
```

### 实现代码框架

```python
class FormPoolManager:
    """Form池管理器 - 只在初始化时串行执行"""
    def __init__(self, pool_size: int, base_url: str):
        self.pool_size = pool_size
        self.base_url = base_url
        self.tab_urls: List[str] = []
        self.lock = asyncio.Lock()

    async def create_pool(self, context: BrowserContext) -> List[str]:
        """预创建N个Form Tab（串行，仅执行1次）"""
        page = await context.new_page()
        await page.goto(f"{self.base_url}/#/product/list_DTB_proProduct")

        for i in range(self.pool_size):
            # 点击复制（串行，但只执行N次，不是每次worker都执行）
            await page.click("i.i-ep-copy-document")
            await page.wait_for_load_state("networkidle")
            self.tab_urls.append(page.url)
            logger.info(f"[Pool] Created form #{i+1}: {page.url}")

        await page.close()
        return self.tab_urls

    async def acquire(self) -> str:
        """Worker获取一个Form URL（原子操作）"""
        async with self.lock:
            return self.tab_urls.pop(0)

class WorkerSession:
    """独立Worker会话"""
    async def run(self, task: ProductTask, form_url: str):
        # 1. Yupoo提取（独立Browser，完全并行）
        yupoo_page = await self.context.new_page()
        extractor = YupooExtractor(task.album_id)
        urls = await extractor.extract(yupoo_page)
        await yupoo_page.close()

        # 2. ERP上传（从池中取专用Form URL，goto而非点击复制）
        erp_page = await self.context.new_page()
        await erp_page.goto(form_url)  # ✅ 直接导航，不点击复制
        await erp_page.wait_for_load_state("networkidle")

        # 3. 填充+上传+保存
        uploader = MrShopPlusUploader(task)
        await uploader.upload_images(erp_page, urls)
        await uploader.format_description(erp_page)
        await uploader.verify_and_save(erp_page)

        await erp_page.close()
```

---

## 执行流程图

```
concurrent_batch_sync_v2.py
        │
        ├─[阶段1] Master: 启动N个Chrome实例 (Port 9222+N)
        │             └─ 每个Chrome = 1个Worker专属Browser
        │
        ├─[阶段2] Master: 创建Form Pool
        │             ├─ 打开ERP商品列表
        │             ├─ 循环"复制" N次
        │             └─ 收集N个Form Tab URL → form_pool.json
        │
        ├─[阶段3] Master: 分发任务
        │             ├─ 读取 batch_products.json
        │             ├─ 平均分配: Worker_i → tasks[i::N]
        │             └─ Worker_i 携带: tasks[] + CDP port + Form URLs
        │
        ├─[阶段4] Worker并行执行 (N workers)
        │   ├─ Worker_i: CDP连接到 localhost:9222+i
        │   ├─ Worker_i: new_context() → new_page()
        │   ├─ for each task:
        │   │   ├─ Yupoo提取: goto /gallery/{id} → parse HTML → urls[]
        │   │   ├─ ERP导航: goto form_pool[local_index] (无竞争!)
        │   │   ├─ 填充品牌+品名
        │   │   ├─ 上传图片 (urls)
        │   │   ├─ 格式化描述
        │   │   └─ 保存 → 截图 → action=3
        │   └─ Worker_i: close browser
        │
        └─[阶段5] Master: 汇总结果
                  ├─ 收集所有 Worker 结果
                  ├─ 生成 batch_result_{timestamp}.json
                  └─ 输出统计: total/success/failed/duration
```

---

## 实施步骤

### Phase 1: FormPoolManager (1-2天)
- [ ] 实现 `FormPoolManager.create_pool()` - 预创建N个Form Tab
- [ ] 实现 `acquire()` 原子URL分发
- [ ] 保存 `form_pool.json` 持久化

### Phase 2: Worker隔离 (1天)
- [ ] 重构 `WorkerSession` - 每个Worker独立Browser
- [ ] CDP多端口连接支持
- [ ] Yupoo提取与ERP上传分离

### Phase 3: 并发编排 (1天)
- [ ] 重写 `run_batch_concurrent()` - 任务分发逻辑
- [ ] Worker健康检查 + 自动重启
- [ ] 结果汇总 + JSON输出

### Phase 4: 风控加固 (1天)
- [ ] ERP上传限流: `Semaphore(3)` (并发≤3防风控)
- [ ] Yupoo提取可全速: `Semaphore(10)`
- [ ] 失败重试 + 断点续传

---

## 关键代码变更清单

| 文件 | 变更 |
|------|------|
| `concurrent_batch_sync_v2.py` | 重写：Multi-CDP + FormPool + Worker隔离 |
| `form_pool_manager.py` | 新增：Form池创建与URL分发 |
| `worker_session.py` | 新增：独立Worker执行单元 |
| `form_pool.json` | 新增：持久化Form URL池 |

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| ERP风控封号 | 中 | 高 | 并发≤3，每日批次限制 |
| Chrome进程耗尽 | 低 | 中 | 最多同时开10个Chrome |
| Form URL过期 | 低 | 高 | 每个Worker用前验证URL有效性 |
| 内存溢出 | 中 | 低 | Worker执行完立即关闭Browser |
