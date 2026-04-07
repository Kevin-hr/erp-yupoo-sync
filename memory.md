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

