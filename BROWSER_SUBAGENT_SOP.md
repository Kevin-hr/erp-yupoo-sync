# Browser Subagent SOP: Native Operation & Safety Protocol
# (浏览器子代理标准作业程序：原生操作与安全协议)

> [!IMPORTANT]
> 此文档为 ERP Yupoo-Sync 项目关于浏览器操作的**第一性原理级标准**。所有涉及过滤、采集、同步的浏览器行为必须 100% 遵守。

## 1. 核心操作准则 (Core Operational Principles)

### 1.1 原生优先 (Native-Only)
*   **规则**: 禁止使用任何通过终端命令（python/scripts/sync_pipeline.py）启动的外部浏览器。
*   **理由**: 外部浏览器属于“受污染执行”，易被平台（如 Yupoo/AliCloud）由于缺少原生指纹与 Session 隔离而识别并拦截。
*   **动作**: 所有浏览器交互必须通过 AI 平台的 `browser_subagent` 工具链完成。

### 1.2 登录与验证码边界 (Auth & CAPTCHA Boundary)
*   **滑块/验证码**: 严禁尝试破解、绕过或模拟任何形式的验证码（Slider, Image, Puzzle）。
*   **动作**: 
    1.  一旦检测到验证码组件或 Proof-of-Humanity 校验，**立即停止**所有操作。
    2.  立即反馈至用户，并请求手动介入。
    3.  严禁重试，直至用户确认 Session 已刷新。

## 2. 交互模式 (Interaction Patterns)

- **分批处理 (Batching)**: 优先将 predictable 的操作（如填写多个表单字段）进行批量化，以降低操作延迟。
- **视觉反馈 (Visual Feedback)**: 每次操作必须录屏（WebP 自动执行）并在关键节点进行截图存证。
- **Strict Mode**: 对高风险 JavaScript 执行及 Artifact 修改采取“用户预审”机制。

## 3. ERP 同步应用 (ERP Sync Application)

*   **隔离性 (Isolation)**: 每一轮同步任务必须使用独立的浏览器上下文，严禁 Yupoo 账户与 ERP 账户在同一流程中共享残留 Cookie。
*   **防指纹追踪 (Anti-Fingerprinting)**: 使用子代理提供的原生指纹掩蔽，确保采集行为在平台视角下呈“低敏感”特征。

---

## 历史修正 (Revision History)
- **2026-04-03**: 初始化 SOP。废弃所有由 Python 驱动的 `scripts/sync_pipeline.py` 浏览器操作，全面拥抱原生 Subagent 模式。
