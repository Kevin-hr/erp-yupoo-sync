# CLAUDE.md (项目开发协议)

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 业务红线 (Business Critical Constraints)

> ⚠️ 以下为强制执行规则，违反将导致业务失败或账号风控

| 规则                       | 说明                            | 违规后果               |
| -------------------------- | ------------------------------- | ---------------------- |
| **禁止项 (Prohibited)** | **操作受污染**：严禁使用终端驱动的 Playwright 脚本操作浏览器 (No Shell-driven Browser Automation) | 触发风控拦截/验证码陷阱 |
| **登录故障检测**     | 遇到验证码、账号停用等登录阻碍即刻停报 (Stop on Login issues) | 触发封控/无效重试 |
| **图片 ≤14 张**     | 第15位留给尺码表                | 商品无法上架           |
| **并发 ≤3**         | ERP并发过高触发风控             | 账号封禁               |
| **独立浏览器上下文** | Yupoo/MrShopPlus 禁止共享Cookie | 会话污染               |
| **保存前截图**       | 每单必须留证                    | 无法追溯"假同步"       |
| **ASCII Only**       | .ps1/.bat严禁中文               | PowerShell 5.1解析错误 |
| **描述禁图防沉余** | 商品描述(Rich Text)严禁包含任何图片，必须使用JS强杀 `<img>` 标签 | 页面排版崩溃/违反建站规范 |
| **强制双参校验**   | 必须提供真实 Brand & Product Name 进行第一行格式化。严禁空参跳过 | 信息残缺/劣质商品展示 |
| **严格静态类型校验**| 列表切片(如 `urls[:14]`)和关键变量必须含显式类型标注 (`cast`)| 引发 `list[Unknown]` 阻塞编译/运行截断 |
| **导入强隔离检测** | 对核心依赖(如Playwright)实施前置 `try/except ImportError` 断言 | 运行时挂掉/环境未对齐导致静默失败 |
| **审计汇报纯客观** | 所有审计与总结必须输出 `.html` 数据报告，严禁主观评价，必须呈递原始数字 | AI幻觉/主观判断掩盖异常真相 |

---

## 核心原则 (Core Principles)

1. **实事求是 (Truth-Based)**: 严禁基于假设编写路径。所有路径必须经过 `ls` 或 `dir` 验证。
2. **5W1H 计划法**: 复杂任务开始前，必须明确 Who/What/When/Where/Why/How。
3. **MECE 原则**: 逻辑拆解必须做到相互独立、完全穷尽。
4. **中文注释 (Chinese Annotations)**: 所有文档、注释、CLI输出必须包含中文翻译。
5. **ASCII-Only 脚本**: 所有 PS1/BAT 脚本严禁中文字符，确保Windows环境兼容性。

---

## Working Directory

**Path**: `C:\Users\Administrator\Documents\GitHub\ERP`

```bash
cd C:\Users\Administrator\Documents\GitHub\ERP
```

---

## 项目概述 (Project Overview)

**# ERP Yupoo-Sync Deployment & Operation Protocol (ERP 同步部署与操作协议)

> [!NOTE]
> 本协议定义了项目执行的硬性业务红线与操作标准。所有自动化行为必须遵守 [BROWSER_SUBAGENT_SOP.md](file:///C:/Users/Administrator/Documents/GitHub/ERP/BROWSER_SUBAGENT_SOP.md)。
将 Yupoo 相册产品图片同步至 MrShopPlus ERP 完成上架。使用 Playwright 浏览器自动化，pipeline/orchestrator 架构。

**核心流程**：Yupoo 9步提取外链 → ERP 6步上传图片 → 自动保存验证

---

## 凭证管理 (Credentials)

> ⚠️ **唯一可信来源**: `.env` 文件。CLAUDE.md/PRD 中的凭证仅供参考对比。

```bash
# Yupoo
YUPOO_USERNAME=lol2024
YUPOO_PASSWORD=9longt#3
YUPOO_BASE_URL=https://lol2024.x.yupoo.com/albums

# MrShopPlus ERP
ERP_USERNAME=zhiqiang
ERP_PASSWORD=123qazwsx
ERP_BASE_URL=https://www.mrshopplus.com
```

凭证以 `os.getenv()` 方式读取，优先级：`.env` > 环境变量 > 脚本硬编码默认值。

---

## 架构 (Architecture)

```
CLI 触发 / 定时任务
        ↓
SyncPipeline (6-stage orchestrator)
├── Stage 1: YupooExtractor    → 相册导航，批量外链提取
├── Stage 2: MetadataPreparer  → URL格式化，批次准备
├── Stage 3: MrShopLogin       → Cookie会话持久化
├── Stage 4: FormNavigator     → 商品表单导航
├── Stage 5: ImageUploader     → URL图片插入
└── Stage 6: Verifier          → 截图验证，保存确认
```

**关键约束**: Yupoo 和 MrShopPlus 各自维护**独立浏览器上下文**，绝不共享Cookie或浏览器状态。

---

## 项目结构 (Project Structure)

**扁平化设计**：业务文件在根目录和 `scripts/` 子目录。

```
ERP/
├── scripts/
│   ├── sync_pipeline.py       # 主入口 - E2E编排器
│   ├── mrshop_image_upload.py # MrShopPlus上传器
│   └── erp_image_uploader.py  # 独立ERP上传器
├── logs/                      # 执行日志
├── screenshots/              # 截图留证
├── cookies.json              # MrShopPlus Cookie
├── yupoo_cookies.json        # Yupoo Cookie
├── PRD_yupoo_to_erp_sync.md  # 产品需求文档
├── GEMINI.md                 # Gemini配置
├── implementation_plan.md    # 实施计划
├── CLAUDE.md                 # 本文件
├── .env / .env.example       # 环境变量（凭证）
├── .planning/                # 项目规划（phase分阶段）
├── .agents/                  # Agent定义（git submodule）
└── .venv/                    # Python虚拟环境
```

---

## 脚本说明 (Scripts)

| 脚本                       | 职责                         | 关键特性                                 |
| -------------------------- | ---------------------------- | ---------------------------------------- |
| `sync_pipeline.py`       | **主入口** - E2E编排器 | 6阶段pipeline，断点续resume，dry-run模式 |
| `mrshop_image_upload.py` | MrShopPlus专用上传器         | 指数退避重试，状态持久化，多选择器回退   |
| `erp_image_uploader.py`  | 独立ERP上传器                | 简化工作流                               |

### 常用命令

```bash
# 全量同步（指定相册）
python scripts/sync_pipeline.py --album-id 231019138

# 模拟运行（不实际修改）
python scripts/sync_pipeline.py --album-id 231019138 --dry-run

# 从第3阶段开始（跳过提取和准备）
python scripts/sync_pipeline.py --album-id 231019138 --step 3 --resume

# 独立MrShopPlus上传器
python scripts/mrshop_image_upload.py --dry-run --headless --resume

# 清除状态重新开始
python scripts/mrshop_image_upload.py --clear-state
```

---

## Pipeline 6阶段详解

| Stage | 名称               | 核心动作                               | 关键约束                                    |
| ----- | ------------------ | -------------------------------------- | ------------------------------------------- |
| 1     | **EXTRACT**  | 直连 `/gallery/{id}` → `dispatch_event` 全选 → 提取 | 优先直连，禁止盲目搜索；使用事件触发点击 |
| 2     | **PREPARE**  | URL换行分隔，格式化元数据              | 提取尺码信息                                |

| 3     | **LOGIN**    | MrShopPlus Cookie认证                  | 优先加载 `cookies.json`                   |
| 4     | **NAVIGATE** | 访问商品列表并定位模板商品             | **严禁从0创建**；必须点击“复制”           |
| 5     | **UPLOAD**   | 替换标题、首行超链接 & 图片 (≤14张)    | 强制物理剔除描述图；必填品牌与品名        |
| 6     | **VERIFY**   | 截图 → 保存 → 观察 URL 变为 `action=3` | 必须有截图，URL 变化是唯一可靠的标志       |



---

## 数据映射 (Data Flow)

| Yupoo来源        | MrShopPlus字段 | 处理逻辑                    |
| ---------------- | -------------- | --------------------------- |
| 相册标题         | `商品名称`   | 去除内部编号（如H110）      |
| 相册描述         | `商品描述`   | 提取尺码行（M/XL/2XL）      |
| 图片外链（≤14） | `商品图片`   | 第15位预留给尺码表          |
| 分类             | `类别`       | 分类名映射（BAPE→T-Shirt） |

---

## 状态管理 (State Management)

| 文件                   | 用途                           |
| ---------------------- | ------------------------------ |
| `cookies.json`       | MrShopPlus登录Cookie（可复用） |
| `yupoo_cookies.json` | Yupoo登录Cookie                |
| `check_album.png`    | 相册截图                       |
| `yupoo_login.png`    | 登录截图                       |

---

## 规划目录 (.planning/)

项目执行蓝图，采用phase分阶段管理：

| 目录                                       | 内容                         |
| ------------------------------------------ | ---------------------------- |
| `.planning/phases/01-foundation-router/` | 第1阶段：Foundation + Router |
| `.planning/research/`                    | 研究文档：架构、技术栈、坑点 |
| `.planning/ROADMAP.md`                   | 项目总路线图                 |

---

## 约束与限制 (Constraints)

- **Cookie刷新**: 会话Cookie需定期手动刷新
- **并发限制**: ERP上传支持≤3并发worker，防止限流
- **重试机制**: `mrshop_image_upload.py` 内置指数退避重试
- **无测试套件**: 当前项目无 `tests/` 目录，需手动验证
