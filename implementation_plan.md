# Implementation Plan (实施计划) - Multi-Platform Login Automation

## 5W1H Decision Planning (5W1H 决策计划)

- **Who (主体)**: 
    - **Lead (负责人)**: Antigravity AI
    - **Target (目标对象)**: Yupoo (lol2024), MrShopPlus
- **What (目标)**: 
    - **Goal (核心目标)**: 实现两个平台的自动化登录并保持会话持久化，为后续爬虫/同步任务提供权限。
    - **Deliverables (核心交付物)**: `login_manager.py` 脚本、SOP 教程、持久化 Cookie 存储。
- **Where (场景)**: 
    - **Context (系统环境)**: 本地 Playwright 环境。
- **When (时效)**: 
    - **Priority (优先级)**: Critical (P0)
- **Why (价值)**: 
    - **ROI (预期回报)**: 登录是所有后续数据抓取的前提，绕过滑块验证码是该阶段的主要矛盾。
- **How (方法)**: 
    - **Tech Stack (技术栈)**: Playwright, Python, JSON (Cookie Storage).

## Proposed Login Schemes (拟议登录方案)

### Scheme A: Cookie Persistence (推荐：Cookie 持久化)
- **Method (方法)**: 通过浏览器工具手动登录一次，脚本导出 `cookies.json`。后续脚本启动时直接 `context.add_cookies()`。
- **Pros (优点)**: 100% 绕过 Yupoo 滑块验证码和 MFA。
- **Cons (缺点)**: 需要人工每隔 X 天手动更新一次 Session。

### Scheme B: Headless Stealth (无头隐身自动化)
- **Method (方法)**: 使用 `playwright-stealth` 配合账号密码自动填充。
- **Pros (优点)**: 全自动化。
- **Cons (缺点)**: 极易触发 Yupoo 的二次验证或滑块。

### Scheme C: Semi-Auto / Human-in-the-loop (半自动互动)
- **Method (方法)**: 程序自动填表，遇到验证码时通过 `notify_user` 截图并请求人工操作。
- **Pros (优点)**: 兼顾效率与成功率。

### Scheme D: CLI-Anything Framework (框架化 CLI 方案) [NEW]
- **Method (方法)**: 利用 `cli-anything` 框架安装或开发针对性的 Agent Harness。
    - 安装元技能：`pip install git+https://github.com/HKUDS/CLI-Anything.git`
    - 调用专用工具（如存在）或封装 Python 为 CLI 供 AI 发现。
- **Pros (优点)**: 标准化、解耦、易于在 AI Agent 体系内复用。
- **Cons (缺点)**: 初期配置成本较高。

### Scheme E: Lark Skill / /lark-skill-maker (飞书 Skill 闭环方案) [NEW]
- **Method (方法)**: 基于 `lark-cli` 构建飞书 Skill。
    - **输入**: 飞书群消息或多维表新增记录（包含 URL）。
    - **内核**: 唤起本地 `login_manager` 执行。
    - **输出**: 直接在飞书内反馈登录成功状态或数据预览。
- **Pros (优点)**: 无缝集成到移动端/团队协作流，真正的“工业化”交付。

## Data Sync Strategy (数据同步策略) - [NEW]

将 Yupoo 相册数据精准映射到 MrShopPlus 上架表单。

| Yupoo Source (源) | MrShopPlus Field (目标字段) | Mapping Logic (映射逻辑) |
| :--- | :--- | :--- |
| Album Title | `商品名称` | 去除编号（如 h310），保留关键描述，翻译为英文。 |
| Album Description | `商品描述` | 提取尺码信息（xs, s, m），格式化为 HTML 列表。 |
| Album Images | `商品图片` | 下载高清原图并批量上传至 MrShopPlus。 |
| Category/Price | `类别 / 售价` | 预设为默认分类，价格参考历史数据或预设系数。 |

## User Review Required

- [IMPORTANT] **Google Account**: 主登录账号已确认为 `heatherstew44@gmail.com`。
- [NEW FLOW] **Yupoo Extraction**: 弃用传统前台抓取，转为使用“后台批量外链”模式（9步法）。

## Proposed Changes (拟议变更)

### [Data Engine (数据引擎组件)]

#### [MODIFY] [yupoo_crawler.py](file:///c:/Users/Administrator/Documents/GitHub/ERP/scripts/yupoo_crawler.py)
利用 `browser_subagent` 模拟 9 步后台操作法：
- **Action**: 导航至 `BAPE-芭比`，进入详情，切换至后台，执行 `批量外链` 并捕获剪贴板或输出文本。

#### [NEW] [mrshop_publisher.py](file:///c:/Users/Administrator/Documents/GitHub/ERP/scripts/mrshop_publisher.py)
基于方案 F (Subagent) 实现产品上架自动化。
- **Action**: 
    1. 点击“复制”进入表单页。
    2. 全自动填入从 Yupoo 获取的数据。
    3. 触发“上架/保存”动作。

## Verification Plan (验证计划)

### Automated Tests (自动化测试)
- `pytest tests/test_yupoo_extraction.py`: 验证 Yupoo 标题与图片下载逻辑。
- `python scripts/mrshop_publisher.py --dry-run`: 模拟填表但不提交。

### Manual Verification (手动验证)
1. **执行 (Action)**: 运行 `python scripts/sync_pipeline.py --id 231019138`。
2. **确认 (Confirmation)**: 登录 MrShopPlus 查看最新上架的“ANCELLM 25ss Jeans”产品，检查图片是否完整，描述是否清晰。
