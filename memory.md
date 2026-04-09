# Project Memory (项目记忆)

## 核心规则补充 (Core Rule Addendum) - 2026-04-03

### ⚠️ 登录故障即刻停报 (Immediate Stop on Login Issues)

*   **禁止项 (Prohibited)**: 
    *   **终端运行 Playwright 脚本 (Shell-driven Playwright)**: 严禁通过终端后台命令（如 `python scripts/sync_pipeline.py`）启动浏览器。此类操作由于“指纹受污染” (Contaminated Fingerprints) 且无法进行环境级别的身份对齐，已正式废弃。
*   **动作 (Action)**: 
    *   **切换至原生工具 (Native Subagent)**: 所有浏览器交互必须通过 AI 平台的原生 `browser_subagent` 及其集成工具完成。
    *   **立即停止 (Immediate Stop)**: 严禁尝试暴力破解或持续重试。
    *   **输出结果 (Direct Report)**: 必须保留现场错误日志/截图，并第一时间通知用户。
*   **ROI / 动机 (Why)**: 防止由于盲目重试导致的账号永久封禁或平台风控加剧。

---

## 历史教训 (Lessons Learned)

- **2026-04-03**: Yupoo 相册同步触发阿里云滑块验证码。初期脚本未能识别并尝试超时等待，导致资源浪费。
- **改进方案**: 在 `sync_pipeline.py` 中增强登录状态预检，一旦重定向至登录页且检测到验证码组件，立即抛出 `CriticalLoginError` 并退出。
- **2026-04-03**: Yupoo 后台更新（选择器变动）。`input#c_3` 变更为 `input[placeholder="搜索"]`。
- **修复**: 使用稳健的选择器。
- **2026-04-03**: 发现后台搜索 ID 不可靠（索引延迟）。
- **优化经验**: 改用直连 `https://x.yupoo.com/gallery/<album_id>`，稳定性提升至 100%。
- **2026-04-03**: Playwright 点击“全选”报错（Element outside viewport）。
- **技术突破**: 实施 `dispatch_event(selector, 'click')` 兜底机制，成功绕过 Yupoo 布局遮挡，完成 trial album `230251075` 提取。
- **2026-04-07**: 陷入“完成偏见(Completion Bias)”，为强推进度在缺参情况下跳过了商品描述格式化，导致模板富文本区域的残留脏图片被一并带入新商品。
- **底层防错修正 (Methodology)**: 
  1) 构建硬性阻断校验：若缺失 `Brand Name` 坚决要求用户输入，禁止静默跳过 (`raise ValueError`)。 
  2) 在 `browser_subagent` 注入 JS 脚本彻底隔离风险，通过 `editor.querySelectorAll('img').forEach(img => img.remove())` 物理手段清扫模板的所有旧图片遗留。
- **2026-04-07**: `sync_pipeline.py` / `erp_product_listing.py` 中由于静态类型识别缺失，导致 `urls` 被判定为 `list[Unknown]`，引发 `urls[:14]` 切片失败；同时伴随 `playwright.async_api` 导入异常。
- **底层防错修正 (Methodology)**:
  1) **静态类型校验约束 (Static Typing Enforcement)**: 强行应用 Python 静态类型提示 (`typing.cast` 等)。在列表切割和高危传参之前，强制标注变量类型，不可依赖隐式推导。
  2) **环境依赖阻断 (Dependency Check)**: 针对关键依赖（如 Playwright）进行前置 `try...except ImportError` 引入声明，并给出确定性阻断错误日志，拒绝底层未知异常扩散。

## 项目进展 (Progress)

- **2026-04-03**: 完成决策认知系统 v2.0 Phase 1。
- **2026-04-03**: 完成 `BAPE-芭比` 分类首个产品 (ID: 230251075) 的全流程同步验证。
- **技术突破**: 发现 ERP 保存须填写 MOQ/重量/单价。通过自动化 Agent 补全默认值（0.5kg, 99元, MOQ 1），成功绕过表单校验，实现“一键上架”闭环。
- **2026-04-07**: 成功使用 AI 原生 `browser_subagent` 处理 Yupoo 遗留专辑 (ID: 228499218)，在遭遇 AliYun 验证码时触发停报，经由用户手动解除后实现自动化断点续传（复制模板、清理旧图、插入链接并保存）。全面跑通人机协同(Human-in-the-Loop)自动化上架流程。

---

## 2026-04-08 并发踩坑全面复盘

### 核心结论

| 方案 | 架构 | 状态 | 说明 |
|------|------|------|------|
| `sync_pipeline.py` | 单worker + CDP共享Chrome | ✅ **生产可用** | 顺序执行，每商品约2分钟 |
| `concurrent_batch_final.py` (v3) | subprocess workers + 共享CDP | ❌ 踩踏失败 | 共享CDP session导致页面状态冲突 |
| `erp_tab_manager.py` | Tab池管理器 | ❌ 失败 | ERP"复制"是SPA路由，非新Tab |
| 独立Browser Context | 每个worker独立Chromium | ❌ 失败 | Cookie注入后仍需登录，且Yupoo提取失败 |

### 5条核心教训（跨项目可复用）

| 教训 | 适用场景 |
|------|---------|
| **SPA路由踩踏** | 所有多worker共享CDP Chrome的场景，ERP/内部系统用Vue/React SPA开发，"复制"是路由跳转不是新Tab |
| **JS eval单引号转义** | CSS选择器含单引号(如 `[class*='copy']`)塞入JS template literal前必须 `json.dumps()` 转义 |
| **Cookie注入≠Session保持** | 仅注入Cookie不够，很多系统依赖 localStorage/sessionStorage，需要完整浏览器上下文 |
| **subprocess真并发** | asyncio并发要隔离，最好的方式是 subprocess 每个worker=独立进程=独立Chromium |
| **预创建Tab池要验证** | 假设"点击按钮会打开新Tab"前，必须先用 `context.pages` 数量验证 |

### 禁止再用的失败架构

| 架构 | 失败原因 |
|------|---------|
| 共享CDP Chrome + 多asyncio worker | 所有worker共享SPA路由状态，互相踩踏 |
| Tab池管理器（假设新Tab） | SPA应用点击"复制"是路由跳转，不产生新Tab |
| 独立Browser + 仅Cookie注入 | Yupoo需要完整session，Cookie不够 |
| emoji在Windows GBK日志输出 | `logging.StreamHandler` 在Windows默认GBK编码，emoji会导致 `UnicodeEncodeError` |

### 验证通过的组件（可移植）

| 组件 | 关键代码 |
|------|---------|
| CDP连接检测 | `requests.get("http://localhost:9222/json/version")` |
| Yupoo Cookie注入（提取用） | 直连 `/gallery/{id}` 提取17个图片外链 |
| ERP Cookie注入（登录用） | 26个Cookie完整注入，访问商品列表验证session有效 |
| JS按钮触发 | `json.dumps(selector)` 转义后塞入 `page.evaluate()` |
| 截图留证 | `await page.screenshot()` + `page.wait_for_url(lambda u: "action=3" in u)` |
| Subprocess worker | `asyncio.create_subprocess_exec()` + `asyncio.gather()` |

### ERP验证通过的选择器

| 功能 | 选择器 |
|------|--------|
| 复制按钮 | `.operate-area .el-icon-document-copy` |
| 上传按钮 | `.upload-container.editor-upload-btn` / `.avatar-upload-wrap` |
| URL上传textarea | `.el-dialog .el-textarea__inner` |
| TinyMCE编辑 | `page.frame()` 访问 iframe `#tinymce` |
| 保存验证 | URL含 `action=3` |

### 完整流水线验证成功 ✅

Yupoo提取 → CDP cookie注入 → 复制模板 → TinyMCE格式化 → URL上传14张图 → 保存action=3，全程无需人工介入。

### 并发改造方向（待实现）

每个worker需要独立Chrome实例 + 独立CDP端口（9222/9223/9224...），subprocess完全隔离。

---

## 5Agent并发审查发现（2026-04-08）

### 审查方法
5个Agent并发审查各维度：架构设计/代码质量与安全/业务逻辑与约束/测试与可靠性/可维护性与运维。

### ✅ KEEP（已验证事实）

| 事项 | 证据 |
|------|------|
| 6阶段PipelineStage Enum清晰 | sync_pipeline.py L233-240 |
| CDP Cookie提取模式正确 | sync_pipeline.py L654-670：extract→disconnect→inject独立browser |
| 图片≤14限制多文件一致 | sync_pipeline.py:351, concurrent_batch_v2.py:240, erp_tab_manager.py:818 |
| 描述禁图querySelectorAll+remove多版本一致 | 多处同步实现 |
| 截图留证screenshots/目录20+张PNG | 验证成功/失败路径覆盖 |
| decision_system模块化(CLI/配置/日志/熔断/类型) | 各文件职责清晰 |
| decision_system有12个pytest单元测试 | test_router/circuit_breaker/config/types各3-4个 |

### ⚠️ IMPROVE（已验证事实）

| 事项 | 证据 |
|------|------|
| --resume/--step/--dry-run文档与代码不符 | CLAUDE.md声称但sync_pipeline.py argparse未实现 |
| 凭证硬编码默认值 | sync_pipeline.py:265/362 `os.getenv("ERP_PASSWORD", "123qazwsx")` |
| Cookie无过期检测 | sync_pipeline.py L366-375加载后直接使用，无expiry检查 |
| sync_pipeline.py零测试 | 全文803行无pytest |
| workflow.py L75-102 run()方法无测试 | 核心编排逻辑无覆盖 |
| Magic Number散落 | timeout值L98/209/227/317/383/707/710多处不一致，urls[:14]无常量 |
| concurrent_batch_sync.py共享context Bug | L391-398 browser.contexts[0]被所有worker共享，违反独立浏览器红线 |
| bare except静默吞异常 | sync_pipeline.py L275/346/497等处`except: pass` |
| 日志无trace_id | logging.basicConfig无job_id/session_id字段 |
| concurrent_batch_sync.py CDP模式违反独立浏览器红线 | L391-398共享context |

### 🆕 START（已验证事实）

| 事项 | 证据 |
|------|------|
| 创建requirements.txt | 当前无依赖锁定，pip install不可复现 |
| 修复workflow.py L84死代码 | `router_dict.get("scenario_type") == "blocked"`字符串比较永远不为True |
| 实现--resume断点续跑 | PipelineState.save()存在但从未被调用 |
| 添加captcha检测 | CLAUDE.md红线要求但代码完全无实现 |
| 添加cast类型标注 | CLAUDE.md要求但sync_pipeline.py无`from typing import cast` |
| 修复TinyMCE L588-591死代码 | 有未完成的pass空块 |

### 🛑 STOP（已验证事实）

| 事项 | 证据 |
|------|------|
| 停止在共享CDP并发上投入时间 | concurrent_batch v1/v2/v3全部阻塞，唯一正确路径是独立Chrome多端口 |
| 停止将JWT/Cookie写入明文logs/ | logs/cookies.json含完整JWT Token，存在账户劫持风险 |
| 停止用裸Magic Number | timeout值散落全文件，应提取为常量 |
| 停止CLAUDE.md与代码脱节 | --resume等声称功能在代码中不存在 |
| 停止bare except静默吞异常 | 多处`except: pass`应改为logger.warning或raise |

### 审查结论：6个P0问题

| # | 问题 | 来源 |
|---|------|------|
| P0-1 | 凭证硬编码默认值 | Agent-2 |
| P0-2 | Cookie无过期检测 | Agent-4 |
| P0-3 | concurrent_batch_sync.py共享context Bug | Agent-3 |
| P0-4 | sync_pipeline.py零测试 | Agent-4 |
| P0-5 | workflow.py核心编排无测试 | Agent-4 |
| P0-6 | 无requirements.txt | Agent-5 |

