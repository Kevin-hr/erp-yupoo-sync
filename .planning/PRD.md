# ERP 项目需求文档 (PRD)

> **版本**: v1.1
> **日期**: 2026-04-08
> **作者**: Claude Code
> **状态**: 正式版
> **变更**: 相比 v1.0 更新并发架构状态（"并发待实现"非"完全失败"），更新CLAUDE.md已同步

---

## 1. 项目概述

### 1.1 项目背景与定位

本项目是**跨境电商独立站运营基础设施**，包含两个独立运行的子系统，共同服务于独立站（stockxshoesvip.net）图片上架与营销决策场景：

| 子系统                            | 定位                                                    | 技术栈                      | 状态            |
| --------------------------------- | ------------------------------------------------------- | --------------------------- | --------------- |
| **Yupoo-to-ERP 同步流水线** | 将 Yupoo 相册产品图片自动同步至 MrShopPlus ERP 完成上架 | Playwright + Python asyncio | ✅ 生产验证     |
| **决策认知系统 v2.0**       | 基于毛泽东思想四大方法论的 AI 决策支持系统              | Python Pydantic + LLM       | ✅ Phase 1 完成 |

**核心用户**：跨境电商运营团队（老板/创业者）
**目标市场**：独立站图片上架 + 网红合作 ROI 量化决策

### 1.2 核心业务流程

```
Yupoo 相册 (lol2024)
    → 提取图片外链 (≤14张)
    → MrShopPlus ERP 登录
    → 复制模板商品
    → 格式化标题/描述/图片
    → 保存验证 (action=3)
    → 截图留证
```

### 1.3 决策系统业务流程

```
用户输入 (决策问题 + ROI)
    → ROI 红线检查 (ROI < 0 → BLOCK)
    → 场景分类 (TRIVIAL / REVERSIBLE / MAJOR / INNOVATIVE / EMOTIONAL)
    → 主要矛盾提取
    → Agent 推荐
    → 顺序执行 + 熔断保护
    → 建议输出 + JSONL 审计日志
```

---

## 2. 系统架构

### 2.1 整体架构

```
C:\ERP (GitHub Repo)
│
├── scripts/                           # 同步流水线 (生产)
│   ├── sync_pipeline.py            ★ 主生产脚本 (~803行)
│   ├── concurrent_batch_final.py   # ❌ 并发待实现 (subprocess方案阻塞)
│   ├── concurrent_batch_v2.py      # ❌ 并发方案v2
│   ├── concurrent_batch_sync.py    # ❌ 并发方案sync
│   └── erp_tab_manager.py          # ❌ Tab池架构失效
│
├── decision_system/                   # 决策认知系统 v2.0
│   ├── __main__.py                 # python -m decision_system 入口
│   ├── cli.py                      # CLI参数解析
│   ├── router.py                   # 决策路由器 (ROI检查/场景分类/矛盾提取)
│   ├── workflow.py                 # Agent顺序编排
│   ├── circuit_breaker.py          # 熔断保护 (max_hops=5)
│   ├── config.py                   # 常量配置
│   ├── types.py                    # Pydantic数据模型
│   ├── logging_utils.py            # JSONL审计日志
│   └── tests/                      # 12个单元测试 (pytest)
│
├── logs/                             # 执行状态持久化
│   ├── cookies.json                # MrShopPlus Cookie (26个)
│   ├── yupoo_cookies.json          # Yupoo Cookie
│   ├── pipeline_state.json         # 断点状态 (save未实现load)
│   ├── decisions.jsonl             # 决策日志 (追加写)
│   ├── sync_YYYYMMDD.log           # 流水线每日日志
│   └── CONCURRENT_DEBUG_20260408.md # 并发踩坑复盘
│
├── screenshots/                      # 证据截图 (27张PNG)
│   └── verify_*.png / debug_*.png / diag_*.png
│
├── .env                              # 凭证 (gitignore)
├── CLAUDE.md                         # 开发指南 (已更新并发状态)
├── GEMINI.md                         # AI规则
├── memory.md                         # 项目历史
├── MVP_EXECUTION_GUIDE.md            # 运营手册
└── BROWSER_SUBAGENT_SOP.md          # 浏览器安全协议
```

### 2.2 同步流水线 6阶段架构

```
CLI: python scripts/sync_pipeline.py --album-id 231019138
        │
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 1: EXTRACT — YupooExtractor                          │
│ 入口: /gallery/{album_id} 直连                              │
│ 动作: page.evaluate() HTML解析                              │
│ 正则: photo\.yupoo\.com/([^/]+)/([^/]+)/small\.jpg        │
│ 输出: pic.yupoo.com/{user}/{photo_id}/{hash}.jpg (≤14)    │
│ 阻塞: 阿里云滑块验证码 → 立即停止                           │
└────────────────────────────────────────────────────────────┘
        │ image_urls: List[str]
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 2: PREPARE — MetadataPreparer                         │
│ 动作: URL换行分隔 + 提取尺码信息                            │
│ 输出: metadata {title, description, sizes, category}        │
└────────────────────────────────────────────────────────────┘
        │ metadata: Dict
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 3: LOGIN — MrShopLogin                               │
│ 优先: logs/cookies.json (26 Cookie注入)                    │
│ 验证: 访问商品列表页确认无login跳转                         │
│ 回退: 表单填充 (username + password + #login-btn)          │
│ 凭证: zhiqiang / 123qazwsx (from .env)                    │
└────────────────────────────────────────────────────────────┘
        │ authenticated_context
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 4: NAVIGATE — FormNavigator                         │
│ 入口: /#/product/list_DTB_proProduct                      │
│ 选择: .operate-area .el-icon-document-copy                 │
│ 路由: 点击"复制" → URL变为 action=4 (SPA路由，非新Tab)       │
│ 等待: asyncio.sleep(5) 让TinyMCE初始化                    │
│ 约束: 严禁从0创建，必须复制模板商品                        │
└────────────────────────────────────────────────────────────┘
        │ form_page
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 5: UPLOAD — ImageUploader + DescriptionEditor        │
│                                                            │
│ [ImageUploader]                                            │
│  - 点击 .upload-container.editor-upload-btn                 │
│  - 切换URL标签 .el-tabs__item:has-text('URL')              │
│  - 填充 .el-dialog .el-textarea__inner (≤14 URL换行)      │
│  - 确认插入 .el-dialog__footer button.el-button--primary    │
│                                                            │
│ [DescriptionEditor]                                        │
│  - 校验 brand_name + product_name 非空 (ValueError)        │
│  - TinyMCE iframe: page.frame() 遍历找 #tinymce           │
│  - JS移除所有 <img> 标签 (业务红线)                        │
│  - 首行格式化: Name: <a href="...">{brand}</a> {product}  │
└────────────────────────────────────────────────────────────┘
        │ uploaded_page
        ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 6: VERIFY — Verifier                                │
│ 截图: screenshots/verify_{timestamp}.png (保存前必须)     │
│ 保存: 点击 button:has-text('保存')                         │
│ 验证: 轮询URL含 action=3 (唯一可靠成功标志)                │
│ 超时: 20次 × 1s = 20s                                     │
└────────────────────────────────────────────────────────────┘
```

### 2.3 决策系统架构

```
用户输入: "要不要给这个100万粉网红送价值5000的货" --roi -500
        │
        ▼
┌────────────────────────────────────────────────────────────┐
│ DecisionRouter.analyze()                                   │
│                                                            │
│ ① ROI红线检查 (META-01)                                   │
│    ROI < 0 → BLOCK ("止亏")                               │
│    关键词: 免费/赠送/倒贴/亏本/无条件/白送                  │
│                                                            │
│ ② 场景分类 (CORE-01)                                      │
│    TRIVIAL: 吃什么/几点/哪里买/天气                       │
│    REVERSIBLE: 试试/测试/换一个/样品                       │
│    INNOVATIVE: 独立站/全新类目/大批量/战略                │
│    MAJOR: (默认) 重大决策                                 │
│    EMOTIONAL: 情绪化表达                                  │
│                                                            │
│ ③ 主要矛盾提取 (CORE-02)                                  │
│    RESOURCE: 钱/资金/预算/成本/贵                         │
│    RISK: 担心/风险/害怕/封号                              │
│    CHOICE: 还是/或者/两难                                  │
│    GROWTH: 第一次/新人/首次合作                           │
│                                                            │
│ ④ Agent推荐 (CORE-04)                                     │
│    TRIVIAL/REVERSIBLE → [] (快通道)                       │
│    MAJOR → [wise-decider-001, bias-scanner-001]           │
│    INNOVATIVE → [wise-decider-001, first-principle-001]  │
│    EMOTIONAL → [bias-scanner-001]                         │
└────────────────────────────────────────────────────────────┘
        │ RouterResult
        ▼
┌────────────────────────────────────────────────────────────┐
│ DecisionWorkflow.run()                                     │
│  1. ROI < 0 → return "不做任何资源投入"                   │
│  2. CircuitBreaker (max_hops=5) 熔断保护                 │
│  3. 顺序执行推荐Agent                                     │
│  4. 最终裁决: 取最后一个Agent结论                        │
└────────────────────────────────────────────────────────────┘
        │ 决策建议 + logs/decisions.jsonl
```

### 2.4 并发架构 (待实现)

**现状**: 单 worker 顺序执行是唯一稳定方案 (已验证)
**阻塞原因**: ERP 是 Vue SPA，"复制"按钮触发内部路由跳转，非新 Tab；多 worker 共享 CDP Chrome 导致 SPA 路由踩踏

**解决路径**: 独立 Chrome 实例 + 多 CDP 端口

```
CHROME-1 (port 9222) → Worker-1 (独立 CDP session)
CHROME-2 (port 9223) → Worker-2 (独立 CDP session)
CHROME-3 (port 9224) → Worker-3 (独立 CDP session)
```

---

## 3. 业务规则与约束

### 3.1 业务红线 (CLAUDE.md 强制执行)

| 规则                         | 说明                                           | 违规后果                    |
| ---------------------------- | ---------------------------------------------- | --------------------------- |
| **禁止终端驱动浏览器** | 严禁使用终端脚本启动 Playwright 操作浏览器     | 指纹污染 → 触发风控/验证码 |
| **登录故障检测**       | 遇到验证码/账号停用即刻停止                    | 触发封控/无效重试           |
| **图片 ≤14 张**       | 第15位留给尺码表                               | 商品无法上架                |
| **并发待实现**         | 多CDP端口独立Chrome正在实现中                  | 当前❌无法并发              |
| **独立浏览器上下文**   | Yupoo/MrShopPlus 禁止共享Cookie                | 会话污染                    |
| **保存前截图**         | 每单必须留证                                   | 无法追溯"假同步"            |
| **ASCII Only**         | .ps1/.bat严禁中文                              | PowerShell 5.1解析错误      |
| **描述禁图**           | 必须移除所有 `<img>` 标签                    | 排版崩溃/违反规范           |
| **强制双参校验**       | Brand & Product Name 必填                      | 空参 ValueError             |
| **严格静态类型校验**   | 列表切片必须显式 `cast`                      | 避免 `list[Unknown]` 截断 |
| **导入强隔离检测**     | Playwright 必须前置 `try/except ImportError` | 环境静默失败                |
| **审计汇报纯客观**     | 输出 `.html` 数据报告，禁止主观评价          | AI幻觉掩盖异常真相          |

### 3.2 决策系统业务规则

| 规则         | 动作                             |
| ------------ | -------------------------------- |
| ROI < 0      | BLOCK — "止亏"                  |
| 首次网红合作 | 推荐 Model B 压测 ($10/15videos) |
| 流量门槛     | ≥1000播放才符合合作资格         |

---

## 4. 数据模型

### 4.1 PipelineState (断点状态)

```python
# scripts/sync_pipeline.py lines 242-254
@dataclass
class PipelineState:
    album_id: str
    current_step: int = 1                    # 1-6
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_stages: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def save(self):  # → logs/pipeline_state.json
        ...
    # ⚠️ 问题: save() 存在但 load()/apply() 未实现
    #    --step 和 --resume 声明了但未生效
```

### 4.2 Cookie 数据

```json
// logs/cookies.json — 26个 MrShopPlus Cookie (~6.7KB)
// logs/yupoo_cookies.json — Yupoo Cookie
[
  {
    "name": "PHPSESSID",
    "value": "...",
    "domain": ".mrshopplus.com",
    "path": "/",
    "secure": true,
    "httponly": true,
    "sameSite": "Lax",
    "expiry": 1758153600
  }
]
// ⚠️ 问题: 无过期检查，当前Cookie已6+天，有过期风险
```

### 4.3 决策日志格式

```json
// logs/decisions.jsonl (追加写)
{
  "timestamp": "2026-04-08T10:00:00",
  "user_input": "要不要给这个100万粉网红送价值5000的货",
  "roi_value": -500,
  "router_result": {
    "scene_type": "MARKETING",
    "main_conflict": "...",
    "agent_recommendations": ["..."]
  },
  "dispatch_result": null,
  "error": null,
  "version": "1.0"
}
```

### 4.4 数据映射

| Yupoo             | MrShopPlus | 处理逻辑                   |
| ----------------- | ---------- | -------------------------- |
| 相册标题          | 商品名称   | 去除内部编号 (如 H110)     |
| 相册描述 (尺码行) | 商品描述   | 仅文本，移除所有图片       |
| 图片外链 (≤14)   | 商品图片   | 第15位预留给尺码表         |
| 分类              | 类别       | 分类名映射 (BAPE→T-Shirt) |

---

## 5. CLI 接口

### 5.1 同步流水线

```bash
# 标准执行
python scripts/sync_pipeline.py --album-id 231019138 \
  --brand-name "BAPE" --product-name "Shark Hoodie"

# CDP模式 (复用已登录Chrome提取Cookie)
python scripts/sync_pipeline.py --album-id 231019138 --use-cdp

# 干跑 (不实际修改)
python scripts/sync_pipeline.py --album-id 231019138 --dry-run

# ❌ --step 和 --resume (声明但未实现)
python scripts/sync_pipeline.py --album-id 231019138 --step 3 --resume
```

### 5.2 决策系统

```bash
# 文本输出
python -m decision_system "要不要给这个100万粉网红送价值5000的货" --roi -500

# JSON输出
python -m decision_system "要不要免费送鞋给这个网红" --output json
```

### 5.3 并发批量 (待实现)

```bash
# ❌ 当前阻塞，共享CDP导致SPA踩踏
python scripts/concurrent_batch_final.py --batch batch_example.json --workers 3
```

---

## 6. ERP SPA 导航

### 6.1 URL 模式

| 页面       | URL                                              | 验证方式            |
| ---------- | ------------------------------------------------ | ------------------- |
| 登录页     | `/#/login`                                     | 重定向到login即失效 |
| 商品列表   | `/#/product/list_DTB_proProduct`               | 需含"product"       |
| 复制表单   | `/#/product/form_DTB_proProduct/0?action=4`    | action=4=新建       |
| 已保存商品 | `/#/product/form_DTB_proProduct/{id}?action=3` | action=3=成功       |

**核心验证**: `action=3` 是唯一可靠的保存成功标志

### 6.2 关键 CSS 选择器

| 功能           | 选择器                                           | 备注             |
| -------------- | ------------------------------------------------ | ---------------- |
| 复制按钮       | `.operate-area .el-icon-document-copy`         | Element Plus图标 |
| 上传按钮       | `.upload-container.editor-upload-btn`          | 描述区上传       |
| 主图上传       | `.avatar-upload-wrap`                          | 头像/主图区      |
| URL标签页      | `.el-tabs__item:has-text('URL')`               | 切换Tab          |
| URL textarea   | `.el-dialog .el-textarea__inner`               | 弹窗内           |
| 确认按钮       | `.el-dialog__footer button.el-button--primary` | 弹窗底部         |
| 保存按钮       | `button:has-text('保存')`                      | 表单内           |
| TinyMCE iframe | `iframe[id^='vue-tinymce']`                    | 需page.frame()   |
| TinyMCE编辑区  | `#tinymce` 或 `.mce-content-body`            | iframe内         |

### 6.3 TinyMCE Iframe 操作

```python
# scripts/sync_pipeline.py lines 544-624
# 策略1: page.frame() 遍历
for frame in page.frames:
    has_tinymce = await frame.evaluate("""() => {
        return !!(document.querySelector('#tinymce') ||
                  document.querySelector('.mce-content-body'));
    }""")
    if has_tinymce:
        mce_frame = frame
        break

# 策略2: contentDocument 回退
# 在主page.evaluate()中通过 contentDocument 访问iframe

# ⚠️ 注意: 复制后需等待5秒让TinyMCE初始化 (asyncio.sleep(5))
```

---

## 7. 已验证功能清单

### 7.1 生产验证 (2026-04-08)

| 功能                            | 状态            | 证据                          |
| ------------------------------- | --------------- | ----------------------------- |
| Yupoo 直连提取 (HTML解析)       | ✅ 验证通过     | logs/sync_20260408.log (91KB) |
| CDP Cookie 提取 → 新浏览器注入 | ✅ 验证通过     | 26个Cookie完整传递            |
| ERP Cookie 会话保持             | ✅ 验证通过     | 登录后访问商品列表成功        |
| SPA 路由导航 (复制→action=4)   | ✅ 验证通过     | URL从list变action=4           |
| TinyMCE iframe 内容操作         | ✅ 验证通过     | page.frame()找到#tinymce      |
| 移除描述中所有 `<img>` 标签   | ✅ 验证通过     | JS evaluate执行成功           |
| URL上传14张图片                 | ✅ 验证通过     | textarea换行分隔              |
| 保存验证 (action=3 URL轮询)     | ✅ 验证通过     | 20次×1s轮询命中              |
| 截图留证                        | ✅ 验证通过     | screenshots/目录27张PNG       |
| 单worker顺序执行                | ✅ 唯一稳定方案 | MVP_EXECUTION_GUIDE.md        |

### 7.2 并发重构状态 (2026-04-08)

| 方案                       | 文件                          | 状态                | 失败原因                                         |
| -------------------------- | ----------------------------- | ------------------- | ------------------------------------------------ |
| Subprocess workers         | `concurrent_batch_final.py` | ❌ 阻塞             | 共享CDP Chrome → SPA路由踩踏                    |
| 共享CDP session            | `concurrent_batch_sync.py`  | ❌ 阻塞             | 同上                                             |
| 独立Browser Context        | `concurrent_batch_v2.py`    | ❌ 阻塞             | Cookie注入≠完整session， Yupoo需要localStorage  |
| Tab池管理器                | `erp_tab_manager.py`        | ❌ 失效             | ERP"复制"是SPA路由不产生新Tab，context.pages不长 |
| **独立Chrome多端口** | **待实现**              | **🔜 进行中** | **每worker独立Chrome实例+不同CDP端口**     |

---

## 8. 安全分析

### 8.1 凭证安全

| 问题                             | 风险  | 缓解                |
| -------------------------------- | ----- | ------------------- |
| `.env` 明文存储密码            | 🔴 高 | `.gitignore` 保护 |
| `logs/cookies.json` 明文Cookie | 🔴 高 | 同上                |
| Cookie 无过期检查                | 🟡 中 | 人工定期刷新        |
| JS eval 字符串注入               | 🟡 中 | 仅在ERP页面内，可控 |

* [ ] 8.2 凭证一致性
* [ ] 来源ERP用户名ERP密码`.envzhiqiang``123qazwsxsync_pipeline.py` 默认值`zhiqiang123qazwsx`CLAUDE.md 凭证表`zhiqiang123qazwsx`

**⚠️ 不一致**: 代码默认值与 `.env` 不同。`os.getenv()` 读取失败时才用默认值，但需统一。

---

## 9. 测试覆盖

### 9.1 决策系统 (12个单元测试)

| 测试文件                    | 测试数 | 覆盖内容                         |
| --------------------------- | ------ | -------------------------------- |
| `test_router.py`          | 4      | 场景分类/矛盾提取/ROI拦截/快通道 |
| `test_circuit_breaker.py` | 2      | 5跳上限/错误消息                 |
| `test_config.py`          | 3      | MAX_HOPS/LLM_TIMEOUT/负ROI关键词 |
| `test_types.py`           | 3      | 枚举/冻结模型/to_json            |

### 9.2 同步流水线

| 类型     | 状态                |
| -------- | ------------------- |
| 单元测试 | ❌ 无               |
| 集成测试 | ❌ 无               |
| E2E验证  | ✅ 手动 (截图+日志) |

---

## 10. 已知问题 (分级)

### P0 — 阻塞发布

| #    | 问题                | 影响                   | 修复方向                            |
| ---- | ------------------- | ---------------------- | ----------------------------------- |
| P0-1 | 凭证不一致          | Cookie可能来自错误账户 | 统一.env值，删除代码硬编码默认值    |
| P0-2 | --resume 功能未实现 | 流水线中断后无法续跑   | 实现 PipelineState.load() + apply() |
| P0-3 | 并发架构阻塞        | 无法并行提速           | 独立Chrome实例 + 多CDP端口          |

### P1 — 影响效率

| #    | 问题             | 影响               | 修复方向                 |
| ---- | ---------------- | ------------------ | ------------------------ |
| P1-1 | Cookie无过期检查 | 过期Cookie静默失败 | 添加expiry验证，过期告警 |
| P1-2 | 相册描述解析脆弱 | UI更新后正则失效   | 改用DOM遍历替代正则      |
| P1-3 | CSS选择器硬编码  | ERP UI更新后踩空   | 抽取到配置文件           |
| P1-4 | 无统一CLI入口    | 子系统各自为政     | 根目录添加 main.py       |

### P2 — 体验/质量

| #    | 问题              | 影响                 | 修复方向               |
| ---- | ----------------- | -------------------- | ---------------------- |
| P2-1 | 同步流水线零测试  | 无法回归测试         | 补充Playwright集成测试 |
| P2-2 | 日志无trace_id    | 难以关联查询         | 统一JSON格式           |
| P2-3 | Stage级重试不分离 | 不同阶段重试策略相同 | 分离Stage级重试配置    |

---

## 11. 依赖清单

### 11.1 Python依赖 (无版本约束)

```bash
pip install playwright pytest pydantic
playwright install chromium
```

**⚠️ 隐患**: 无 `requirements.txt`，无版本锁定

### 11.2 系统依赖

| 依赖            | 版本         | 用途          |
| --------------- | ------------ | ------------- |
| Python          | 3.10+ (推测) | 运行环境      |
| Chrome/Chromium | 最新         | 浏览器自动化  |
| Windows 10 Pro  | 10.0.19045   | 开发/生产环境 |

---

## 12. 文件清单

```
C:\Users\Administrator\Documents\GitHub\ERP\
├── scripts/
│   ├── sync_pipeline.py              ★ 主生产脚本 (~803行)
│   ├── concurrent_batch_v2.py       # 并发方案v2 (阻塞)
│   ├── concurrent_batch_sync.py     # 并发方案sync (阻塞)
│   ├── concurrent_batch_final.py     # 并发方案final (阻塞)
│   └── erp_tab_manager.py            # Tab池 (失效)
├── decision_system/
│   ├── __init__.py
│   ├── __main__.py                   # CLI入口
│   ├── cli.py                        # 参数解析
│   ├── config.py                     # 常量
│   ├── router.py                     # 决策路由
│   ├── workflow.py                   # Agent编排
│   ├── circuit_breaker.py            # 熔断
│   ├── types.py                      # Pydantic模型
│   ├── logging_utils.py              # JSONL日志
│   └── tests/                        # 12个单元测试
│       ├── conftest.py
│       ├── pytest.ini
│       ├── test_router.py
│       ├── test_circuit_breaker.py
│       ├── test_types.py
│       └── test_config.py
├── logs/
│   ├── cookies.json                  # 26个ERP Cookie (~6.7KB)
│   ├── yupoo_cookies.json
│   ├── pipeline_state.json
│   ├── decisions.jsonl
│   ├── sync_20260408.log            # 91KB
│   └── CONCURRENT_DEBUG_20260408.md
├── screenshots/                      # 27张PNG证据
├── .env                              # 凭证 (gitignore)
├── CLAUDE.md                         # 355行开发指南
├── GEMINI.md                         # AI规则
├── memory.md                         # 项目历史
├── MVP_EXECUTION_GUIDE.md            # 运营手册
├── BROWSER_SUBAGENT_SOP.md          # 浏览器安全协议
└── .planning/
    ├── PRD.md                       ★ 本文档
    ├── ROADMAP.md
    ├── PROJECT.md
    ├── REQUIREMENTS.md
    └── phases/01-foundation-router/
        ├── 01-SUMMARY.md
        └── 01-REVIEWS.md
```

---

## 13. 非功能需求

| 指标               | 当前                   | 目标             |
| ------------------ | ---------------------- | ---------------- |
| 单商品上架时间     | ~2分钟                 | <1分钟           |
| 每小时产出 (顺序)  | ~30商品                | ~60商品 (并发后) |
| 决策系统响应       | <5s                    | <3s              |
| 上架成功率         | ~90% (Yupoo验证码阻断) | >95%             |
| 同步流水线测试覆盖 | 0%                     | >60%             |
| 决策系统测试覆盖   | ~70%                   | >80%             |

---

## 14. 路线图

### Phase 1: Foundation + Router ✅ 已完成

| 交付物                        | 状态 |
| ----------------------------- | ---- |
| 核心路由器 (ROI拦截/场景分类) | ✅   |
| 熔断机制 (max_hops=5)         | ✅   |
| JSONL审计日志                 | ✅   |
| CLI接口                       | ✅   |
| 12个单元测试                  | ✅   |

### Phase 2: 并发重构 🔜 进行中 (P0-3)

| 任务                           | 依赖       | 优先级 |
| ------------------------------ | ---------- | ------ |
| 独立Chrome实例架构             | -          | P0     |
| 多CDP端口分配 (9222/9223/9224) | -          | P0     |
| Worker隔离Cookie方案           | 独立Chrome | P1     |
| 并发数配置化 (--workers)       | -          | P1     |

### Phase 3: 断点续跑 (P0-2)

| 任务                       | 依赖       | 优先级 |
| -------------------------- | ---------- | ------ |
| PipelineState.load() 实现  | -          | P0     |
| PipelineState.apply() 实现 | -          | P0     |
| --resume 参数生效          | load+apply | P0     |
| Stage级重试配置分离        | -          | P1     |

### Phase 4: 测试与质量

| 任务                       | 依赖        | 优先级 |
| -------------------------- | ----------- | ------ |
| 同步流水线集成测试         | Playwright  | P1     |
| CSS选择器配置化            | Phase 1稳定 | P2     |
| 日志结构化 (JSON+trace_id) | -           | P2     |
| 统一CLI入口                | -           | P2     |

---

## 15. 附录

### A. 凭证来源对照

| 位置                        | Yupoo用户 | ERP用户                  | ERP密码      |
| --------------------------- | --------- | ------------------------ | ------------ |
| `.env`                    | lol2024   | zhiqiang                 | 123qazwsx    |
| `sync_pipeline.py` 默认值 | lol2024   | litzyjames5976@gmail.com | RX3jesthYF7d |
| CLAUDE.md 凭证表            | lol2024   | litzyjames5976@gmail.com | RX3jesthYF7d |

### B. 关键超时配置

| 操作                     | 超时               |
| ------------------------ | ------------------ |
| page.wait_for_load_state | 30s                |
| Vue渲染等待              | 8s (asyncio.sleep) |
| TinyMCE初始化等待        | 5s (asyncio.sleep) |
| action=3 URL轮询         | 20次×1s=20s       |
| LLM调用                  | 120s               |

### C. 项目文档索引

| 文档                                  | 用途                   |
| ------------------------------------- | ---------------------- |
| `CLAUDE.md`                         | 完整开发指南           |
| `memory.md`                         | 项目历史变更与经验教训 |
| `MVP_EXECUTION_GUIDE.md`            | 运营执行手册           |
| `BROWSER_SUBAGENT_SOP.md`           | 浏览器操作安全协议     |
| `GEMINI.md`                         | AI规则与决策原则       |
| `logs/CONCURRENT_DEBUG_20260408.md` | 并发踩坑详细复盘       |

---

*本文档由 Claude Code 自动生成，基于 2026-04-08 代码审查*
*v1.1 更新: 并发架构状态由"完全失败"修订为"并发待实现"，反映 CLAUDE.md Row 16 变更*
