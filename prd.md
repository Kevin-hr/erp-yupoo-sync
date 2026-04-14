# Product Requirements Document (PRD): Industrialized ERP Sync System (v2.1)

## 0. 最高红线 (Highest Rule)
> [!IMPORTANT]
> **全量下架**: 所有同步同步至 ERP 的商品，必须初始设定为 **"商品下架" (OFF/灰色)** 状态。
> **人工审核**: 严禁脚本直接上架商品，必须由人工进行外观、价格、链接复核后手动上架。

## 1. 目标 (Goal)

构建一个**工业级、高并发、去共享化**的 Yupoo 瀑布流图片同步至 MrShopPlus ERP 的自动化系统。解决原有同步脚本在并发场景下的 Cookie 冲突、浏览器上下文污染及稳定性问题，实现 100% 确定性的商品刊登。

## 2. 核心功能 (Core Features)

### 2.1 去共享化并发架构 (De-shared Concurrent Architecture)

- **独立进程/上下文**：每个同步任务（Worker）拥有完全独立的 `Playwright Browser` 实例。
- **防止污染**：禁止共享 Cookie 或缓存，确保多品牌并发请求时互不干扰。
- **并发控制**：通过 `asyncio.Semaphore` 严格限制最大并发数（默认为 3），平衡系统负载与执行效率。

### 2.2 强化型品牌描述格式化 (Premium Brand Formatting)

- **品牌超链接注入**：自动识别描述首行，将 brandName 封装为指向 `stockxshoesvip.net` 的 SEO 友好型超链接。
- **Slug 自动转换**：将品牌名（如 "BAPE"）转换为 URL Slug（如 "bape-shoes"）。
- **禁图策略**：严格移除描述富文本中的所有 `<img>` 标签，防止描述冗余。

### 2.3 工业级提取与上传 (Industrial Extraction & Upload)

- **Yupoo 静态直解**：通过解析 Yupoo 相册 HTML 直接提取 Photo ID，拼接 `pic.yupoo.com` 外链，绕过复杂的 DOM 点击操作。
- **URL 批量上传**：利用 ERP 的“URL上传”功能实现图片秒传，支持最大 14 张图限制。
- **自动保存验证**：监控 `action=3` URL 跳转，确保保存动作真正完成。

## 3. 验收标准 (Acceptance Criteria)

- [x] **稳定性**：单日处理 100+ 商品，错误率 < 1%。
- [x] **合规性**：所有商品描述首行包含格式正确的品牌超链接。
- [x] **性能**：单任务处理时间 < 60s（包含浏览器启动与资源加载）。
- [x] **可视化**：每个任务执行完成后自动记录成功/失败状态，并保留异常截图。

## 4. 运维/环境性协同 (Operational & Environmental Requirements)

为了维持目前的工业化标准并确保后续系统的高并发扩展，系统运行需满足以下配合要点：

- **多端口环境支持**：若需将并发数提升至 3+，需确保本地有对应数量的 Chrome 实例运行在不同的 CDP 端口（如 9222, 9223, 9224），或授权脚本使用自动化子进程管理这些实例。
- **凭证隔离性**：必须保持 `.env` 文件的唯一可信性，严禁在代码或其它非环境配置文件中硬编码凭证。
- **审计反馈循环**：人工需定期查看 `logs/` 下生成的 `.html` 审计报告。若发现页面字段不匹配或 UI 变动，需及时反馈以更新 `memory.md` 中的定位器 (Selectors) 记忆。
- **无干预执行**：在 Worker 自动化运行时，人工严禁手动操作对应的浏览器窗口，防止 SPA (Single Page Application) 路由踩踏导致任务崩溃。

## 5. 待解决问题 (User Review Required)

> [!IMPORTANT]
>
> - [ ] **验证码预警**：目前脚本未包含 OCR 识别，若频繁触发 Yupoo/ERP 验证码，系统将自动挂起并报错。
> - [ ] **IP 封禁风险**：并发过高可能导致 Yupoo 端的 IP 访问受限，建议生产环境使用代理或保持并发数 ≤ 3。
