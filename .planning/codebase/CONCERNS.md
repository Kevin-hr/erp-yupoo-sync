# Codebase Concerns

**Analysis Date:** 2026-04-07

---

## 业务红线 (Business Critical Constraints)

### 1. 禁止项：终端驱动 Playwright 自动化

| 项目 | 说明 |
|------|------|
| **规则** | 严禁使用终端驱动的 Playwright 脚本操作浏览器 |
| **违规后果** | 触发风控拦截 / 验证码陷阱 |
| **当前状态** | `scripts/sync_pipeline.py` 第 401-438 行使用 `async_playwright()` 直接启动浏览器 |
| **冲突来源** | `BROWSER_SUBAGENT_SOP.md` 第 10-12 行明确规定必须使用原生 Subagent 工具链 |

**关键冲突:**
```python
# scripts/sync_pipeline.py:401-404
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)  # 终端驱动！
    context = await browser.new_context(...)
    page = await context.new_page()
```

**风险评估:** 高 - 当前实现直接与 SOP 要求冲突，平台可检测到自动化指纹。

---

### 2. 图片数量红线 (≤14 张)

| 项目 | 说明 |
|------|------|
| **规则** | 第 15 位留给尺码表，商品图片严格 ≤14 张 |
| **违规后果** | 商品无法上架 |
| **代码位置** | `scripts/sync_pipeline.py:242` |
| **实现** | `return list(urls[:14]) # Limit to 14 rule (强制 14 张红线)` |

**风险:** 当前硬编码截断 14 张，但未验证实际图片数量是否满足业务需求。若 Yupoo 相册 >14 张图片，可能丢失有效商品图片。

---

### 3. 并发限制 (≤3)

| 项目 | 说明 |
|------|------|
| **规则** | ERP 并发过高触发风控，账号封禁 |
| **当前实现** | `sync_pipeline.py` 单浏览器实例，未实现并发 worker |
| **mrshop_image_upload.py** | 支持 `headless` 和 `resume` 参数，但未验证并发控制 |

**风险:** 未来若扩展多并发 worker，需严格遵守 ≤3 限制。

---

### 4. 独立浏览器上下文

| 项目 | 说明 |
|------|------|
| **规则** | Yupoo/MrShopPlus 禁止共享 Cookie，必须维护独立浏览器上下文 |
| **代码位置** | `scripts/sync_pipeline.py:401-405` |
| **当前实现** | 使用单一 `context = await browser.new_context()` 同时处理两个平台 |

**风险:** 当前实现在同一浏览器上下文中操作 Yupoo 和 MrShopPlus，可能导致会话污染。

```python
# sync_pipeline.py:401-405 - 单一上下文问题
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(...)  # 一个上下文同时处理 Yupoo + MrShopPlus
    page = await context.new_page()
```

---

### 5. 登录故障检测

| 项目 | 说明 |
|------|------|
| **规则** | 遇到验证码、账号停用等登录阻碍即刻停报 |
| **SOP 要求** | `BROWSER_SUBAGENT_SOP.md:15-19` - 检测到 CAPTCHA 立即停止，严禁重试 |
| **当前实现** | `sync_pipeline.py:197-199` 仅检查 URL 是否包含 "login" |

**风险:** 当前仅检测重定向到登录页，无法识别 CAPTCHA 弹窗、滑块验证等中间状态。

---

### 6. 保存前截图

| 项目 | 说明 |
|------|------|
| **规则** | 每单必须留证，无法追溯"假同步" |
| **代码位置** | `scripts/sync_pipeline.py:302-309` (Verifier.verify) |
| **实现** | `await page.screenshot(path=str(shot_path))` |

**风险:** 截图保存在本地 `screenshots/` 目录，但未验证截图内容是否包含成功标志。若保存操作静默失败，无法追溯。

---

### 7. ASCII Only 脚本约束

| 项目 | 说明 |
|------|------|
| **规则** | .ps1/.bat 严禁中文字符，PowerShell 5.1 无法解析 |
| **影响** | 所有脚本注释和输出必须使用英文或中文标注 |

---

## 技术风险 (Technical Risks)

### 1. Cookie 过期与会话管理

| 风险 | 位置 | 描述 |
|------|------|------|
| Cookie 过期未检测 | `scripts/sync_pipeline.py:152-178` (YupooLogin) | 加载 Cookie 后未验证有效性，直接假设可用 |
| 过期后无法恢复 | `scripts/sync_pipeline.py:196-199` | 仅检查是否重定向到登录页，无法自动刷新 |
| MrShopPlus Cookie 结构 | `scripts/sync_pipeline.py:248-277` | 同上，未验证 Cookie 有效性 |

**影响:** 流水线运行中途 Cookie 过期将导致同步失败，且无自动恢复机制。

---

### 2. Playwright 选择器脆弱性

| 选择器 | 位置 | 风险 |
|--------|------|------|
| `label.Checkbox__main:visible, .Checkbox__main:visible` | `sync_pipeline.py:204` | CSS 类名易变， Yupoo UI 升级后失效 |
| `button:has-text('批量外链'), .toolbar__button:has-text('批量外链')` | `sync_pipeline.py:212` | 文本内容匹配依赖本地化，类名易变 |
| `span:has-text('预览'), button:has-text('生成外链')` | `sync_pipeline.py:219` | 多选择器回退逻辑，但预览按钮缺失时静默继续 |
| `textarea.Input__input` | `sync_pipeline.py:227` | 隐藏 textarea 可能导致提取失败 |
| `i.i-ep-copy-document, .action-btn:has-text('复制')` | `sync_pipeline.py:419` | 图标类名 `i-ep-copy-document` 依赖前端实现 |
| `.fa-trash-o` | `sync_pipeline.py:288` | FontAwesome 类名，删除按钮选择器脆弱 |

**缓解:** `safe_click` 函数 (第 93-104 行) 实现了 `dispatch_event` 回退机制。

---

### 3. 网络状态等待不确定性

| 风险 | 位置 | 描述 |
|------|------|------|
| `networkidle` 超时 | 多处使用 `await page.wait_for_load_state('networkidle')` | 网络慢时阻塞，图片加载延迟可能导致截断 |
| 固定等待时间 | `sync_pipeline.py:206, 215, 222, 299` | 使用 `asyncio.sleep(N)` 硬编码等待，不适应网络波动 |
| 缺乏重试机制 | `YupooExtractor.extract()` | 网络异常时直接抛出异常，无重试逻辑 |

---

### 4. 浏览器上下文隔离缺失

| 风险 | 位置 | 描述 |
|------|------|------|
| 单一上下文 | `sync_pipeline.py:404` | Yupoo 和 MrShopPlus 使用同一 context，Cookie 可能交叉污染 |
| 独立文件但同实例 | `scripts/mrshop_image_upload.py` | 若独立运行，Cookie 文件分离但浏览器实例可能共享配置文件 |

---

### 5. 状态持久化漏洞

| 风险 | 位置 | 描述 |
|------|------|------|
| 状态保存延迟 | `scripts/sync_pipeline.py:137-139` | `PipelineState.save()` 仅在手动调用时保存，异常时可能丢失 |
| 无原子性写入 | `PipelineState.save()` | JSON 直接覆盖，流水线崩溃时可能损坏 |
| 恢复后 Cookie 有效性 | 状态恢复后未验证 Cookie | resume 可能用过期 Cookie |

---

## 运营风险 (Operational Risks)

### 1. 手动 Cookie 刷新

| 风险 | 描述 |
|------|------|
| 定期刷新需求 | `CLAUDE.md:200` 明确说明会话 Cookie 需定期手动刷新 |
| 无自动检测 | 当前实现无法判断 Cookie 是否仍有效，需人工判断 |
| 刷新流程 | 需手动删除 `cookies.json` / `yupoo_cookies.json`，重新运行流水线 |

---

### 2. CAPTCHA 处理

| 风险 | 描述 |
|------|------|
| SOP 强制停止 | `BROWSER_SUBAGENT_SOP.md:15-19` - 检测到 CAPTCHA 即刻停止，请求人工介入 |
| 当前无检测 | `sync_pipeline.py` 无 CAPTCHA 检测逻辑 |
| 后果 | 若遇验证码，流水线将无限等待或失败 |

---

### 3. ERP 限流

| 风险 | 描述 |
|------|------|
| 并发限制 | `CLAUDE.md:16` - ERP 并发 >3 触发风控，账号封禁 |
| 当前状态 | 单实例无并发，未超出限制 |
| 扩展风险 | 未来若添加并发 worker，需严格控制 ≤3 |

---

### 4. 错误恢复与断点续传

| 风险 | 描述 |
|------|------|
| 状态保存时机 | `sync_pipeline.py:137-139` - 状态保存依赖手动调用 |
| crash 后恢复 | 需使用 `--resume` 参数重新运行，但 Cookie 可能已过期 |
| dry-run 限制 | `--dry-run` 仅模拟，不验证实际 Cookie 有效性 |

---

## 安全风险 (Security Risks)

### 1. 反机器人检测

| 风险 | 描述 |
|------|------|
| 自动化指纹 | `BROWSER_SUBAGENT_SOP.md:11` - 终端驱动 Playwright 缺少原生指纹 |
| 平台检测 | Yupoo 和 MrShopPlus 可检测到自动化特征 (navigator.webdriver, Playwright 特有头) |
| 后果 | 触发验证码、账号限制或封禁 |

---

### 2. 凭证泄露风险

| 风险 | 位置 | 描述 |
|------|------|------|
| .env 文件依赖 | `scripts/sync_pipeline.py:36-49` | 凭证从 `.env` 读取，但脚本中仍有默认值硬编码 |
| 默认值暴露 | `sync_pipeline.py:149-151, 250-251` | Yupoo/MrShopPlus 凭证有默认值在代码中 |
| Cookie 文件 | `logs/cookies.json`, `logs/yupoo_cookies.json` | Cookie 文件包含敏感会话令牌 |

---

### 3. 截图证据可靠性

| 风险 | 描述 |
|------|------|
| 截图内容未验证 | `sync_pipeline.py:307-309` - 仅保存截图，不验证内容是否包含成功标志 |
| 保存失败静默 | 截图保存失败仅记录日志，流水线继续执行 |
| 覆盖问题 | 同名截图被覆盖，无法追溯历史状态 |

---

## 数据完整性风险 (Data Integrity Risks)

### 1. 图片截断与丢失

| 风险 | 描述 |
|------|------|
| 强制 14 张限制 | `sync_pipeline.py:242` - 超过 14 张图片直接截断 |
| 业务语义丢失 | 未告知用户哪些图片被丢弃 |
| 尺码表预留 | 第 15 位预留给尺码表，但代码未实现自动插入逻辑 |

---

### 2. 元数据提取失败

| 风险 | 位置 | 描述 |
|------|------|------|
| 相册描述解析 | `sync_pipeline.py` - 依赖特定 HTML 结构 |
| 尺码信息提取 | 数据映射逻辑 (`CLAUDE.md:169-170`) 未在代码中实现 |
| 标题格式化 | `DescriptionEditor.format_description()` 使用正则匹配，脆弱 |

---

### 3. 流水线崩溃数据丢失

| 风险 | 描述 |
|------|------|
| 状态未保存 | 异常发生前未保存 PipelineState |
| 临时数据丢失 | 已提取的 image_urls 未持久化 |
| 重复提取 | resume 后需重新执行 EXTRACT 阶段 |

---

## 测试覆盖缺口 (Test Coverage Gaps)

### 1. 无自动化测试套件

| 风险 | 描述 |
|------|------|
| 当前状态 | `CLAUDE.md:203` 明确说明"无测试套件" |
| 影响 | 任何代码修改需手动验证，风险高 |
| 回归风险 | 新增功能或重构可能破坏现有逻辑 |

---

### 2. 选择器变更无告警

| 风险 | 描述 |
|------|------|
| CSS 类名依赖 | Yupoo/MrShopPlus UI 升级后选择器失效 |
| 无监控 | 选择器变更无自动告警，需人工发现 |

---

### 3. 网络异常无模拟测试

| 风险 | 描述 |
|------|------|
| 硬编码等待 | `asyncio.sleep()` 无法模拟网络延迟 |
| 超时值固定 | 无动态超时调整机制 |

---

## 关键修复优先级 (Remediation Priority)

| 优先级 | 风险 | 修复方案 |
|--------|------|----------|
| **P0 - 立即修复** | 终端驱动 Playwright 与 SOP 冲突 | 迁移到 browser_subagent 工具链 |
| **P0 - 立即修复** | 单一浏览器上下文混合 Yupoo/MrShopPlus | 实现独立 BrowserContext 隔离 |
| **P1 - 高优先级** | Cookie 过期无检测 | 添加 Cookie 有效性预检 |
| **P1 - 高优先级** | CAPTCHA 无检测机制 | 添加 CAPTCHA 弹窗检测，触发停止 |
| **P2 - 中优先级** | 无自动化测试 | 补充单元测试和集成测试 |
| **P2 - 中优先级** | 选择器脆弱性 | 添加选择器回退链和告警 |
| **P3 - 低优先级** | 图片截断无提示 | 添加日志警告和用户通知 |

---

*Concerns audit: 2026-04-07*
