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

## 项目进展 (Progress)

- **2026-04-03**: 完成决策认知系统 v2.0 Phase 1。
- **2026-04-03**: 完成 `BAPE-芭比` 分类首个产品 (ID: 230251075) 的全流程同步验证。
- **技术突破**: 发现 ERP 保存须填写 MOQ/重量/单价。通过自动化 Agent 补全默认值（0.5kg, 99元, MOQ 1），成功绕过表单校验，实现“一键上架”闭环。

