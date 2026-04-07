# 代码库结构

**分析日期:** 2026-04-07

## 目录布局

```
ERP/                                    # 项目根目录
├── scripts/                          # 核心同步脚本
│   └── sync_pipeline.py              # 主入口 - E2E 编排器 (448行)
├── decision_system/                   # 决策认知系统
│   ├── router.py                     # 决策路由器
│   ├── workflow.py                   # 工作流编排器
│   ├── circuit_breaker.py            # 熔断器
│   ├── config.py                     # 配置常量
│   ├── types.py                      # Pydantic 数据结构
│   ├── cli.py                        # CLI 入口
│   ├── logging_utils.py              # 日志工具
│   ├── __main__.py                   # 包入口
│   └── tests/                        # 测试套件
├── .agents/                          # Agent 定义 (git submodule)
│   └── workflows/
│       └── yupoo-to-mrshop-sync.md   # 工作流定义
├── .planning/                        # 项目规划
│   ├── codebase/                    # 本文档目录
│   │   ├── ARCHITECTURE.md           # 架构文档
│   │   └── STRUCTURE.md              # 结构文档
│   ├── research/                     # 研究文档
│   ├── phases/                       # 分阶段计划
│   ├── ROADMAP.md                    # 项目路线图
│   ├── PROJECT.md                    # 项目定义
│   ├── REQUIREMENTS.md               # 需求文档
│   ├── STATE.md                      # 状态追踪
│   └── config.json                  # 规划配置
├── logs/                             # 日志目录
│   ├── sync_YYYYMMDD.log             # 流水线日志
│   ├── cookies.json                  # MrShopPlus Cookie
│   ├── yupoo_cookies.json            # Yupoo Cookie
│   ├── pipeline_state.json           # 断点续传状态
│   └── decisions.jsonl               # 决策日志
├── screenshots/                      # 截图存证目录
├── .venv/                            # Python 虚拟环境
├── .env                              # 环境变量 (含凭证)
├── .env.example                      # 环境变量模板
├── CLAUDE.md                         # 项目协议
├── GEMINI.md                         # AI 规则手册
├── BROWSER_SUBAGENT_SOP.md           # 浏览器操作 SOP
└── PRD_yupoo_to_erp_sync.md         # 产品需求文档
```

## 目录用途详解

### scripts/ - 核心同步脚本

| 文件 | 用途 | 关键函数/类 |
|------|------|------------|
| `sync_pipeline.py` | 主入口 - E2E 编排器 | `SyncPipeline.run()`, `PipelineStage`, `PipelineState` |

**关键组件类:**
- `YupooLogin` - Yupoo 登录认证
- `YupooExtractor` - 图片外链提取（9步逻辑）
- `MrShopLogin` - MrShopPlus 登录认证
- `ImageUploader` - 图片上传器
- `DescriptionEditor` - 商品描述格式化
- `Verifier` - 最终验证
- `safe_click`, `safe_fill` - 安全操作装饰器

### decision_system/ - 决策认知系统

| 文件 | 用途 | 关键函数/类 |
|------|------|------------|
| `router.py` | 决策路由器 | `DecisionRouter.analyze()`, `SceneType`, `ROIStatus` |
| `workflow.py` | 工作流编排 | `DecisionWorkflow.run()`, `WorkflowResult` |
| `circuit_breaker.py` | 熔断器 | `CircuitBreaker.check()`, `record_hop()` |
| `types.py` | 数据结构 | `RouterResult`, `SceneType`, `ConflictCategory` |
| `config.py` | 配置常量 | `MAX_HOPS`, `LLM_TIMEOUT`, `NEGATIVE_ROI_KEYWORDS` |
| `cli.py` | CLI 入口 | - |
| `logging_utils.py` | 日志工具 | - |

**tests/ 子目录:**
| 文件 | 用途 |
|------|------|
| `test_router.py` | 路由器单元测试 |
| `test_circuit_breaker.py` | 熔断器测试 |
| `test_config.py` | 配置测试 |
| `test_types.py` | 类型测试 |
| `conftest.py` | pytest 配置 |

### .agents/ - Agent 定义

** workflows/yupoo-to-mrshop-sync.md**
- 定义: 浏览器自动化 SOP
- 内容: 6步同步流程定义

### logs/ - 日志与状态

| 文件 | 用途 | 格式 |
|------|------|------|
| `sync_YYYYMMDD.log` | 流水线执行日志 | Text |
| `cookies.json` | MrShopPlus 登录 Cookie | JSON |
| `yupoo_cookies.json` | Yupoo 登录 Cookie | JSON |
| `pipeline_state.json` | 断点续传状态 | JSON |
| `decisions.jsonl` | 决策日志 | JSONL |

### screenshots/ - 截图存证

- 命名格式: `verify_HHMMSS.png`
- 用途: 每单必须留证，保存前截图

## 关键文件位置

### 入口点

| 入口 | 文件路径 | 触发方式 |
|------|----------|----------|
| 全量同步 | `scripts/sync_pipeline.py --album-id <id>` | CLI |
| 模拟运行 | `scripts/sync_pipeline.py --album-id <id> --dry-run` | CLI |
| 断点续传 | `scripts/sync_pipeline.py --album-id <id> --step 3 --resume` | CLI |
| 决策系统 CLI | `python -m decision_system` | CLI |

### 配置文件

| 配置 | 文件路径 | 说明 |
|------|----------|------|
| 环境变量 | `.env` | 凭证存储（不提交 git） |
| 环境变量模板 | `.env.example` | 参考格式 |
| 规划配置 | `.planning/config.json` | 项目配置 |
| Python 配置 | `decision_system/config.py` | MAX_HOPS, LLM_TIMEOUT |

### 核心逻辑

| 逻辑 | 文件路径 | 说明 |
|------|----------|------|
| Pipeline 编排 | `scripts/sync_pipeline.py` | 6阶段流水线 |
| 决策路由 | `decision_system/router.py` | ROI检查、场景分类 |
| 工作流编排 | `decision_system/workflow.py` | Agent 调度 |
| 熔断器 | `decision_system/circuit_breaker.py` | 防止循环 |

### 测试

| 测试 | 文件路径 |
|------|----------|
| 路由器测试 | `decision_system/tests/test_router.py` |
| 熔断器测试 | `decision_system/tests/test_circuit_breaker.py` |
| 配置测试 | `decision_system/tests/test_config.py` |
| 类型测试 | `decision_system/tests/test_types.py` |

## 命名约定

### 文件命名

| 类型 | 约定 | 示例 |
|------|------|------|
| Python 脚本 | snake_case.py | `sync_pipeline.py` |
| 测试文件 | test_<module>.py | `test_router.py` |
| Markdown 文档 | kebab-case.md | `yupoo-to-mrshop-sync.md` |
| 日志文件 | sync_YYYYMMDD.log | `sync_20260407.log` |

### 类命名

| 类型 | 约定 | 示例 |
|------|------|------|
| Pipeline 组件 | PascalCase | `YupooExtractor`, `ImageUploader` |
| 决策系统类 | PascalCase | `DecisionRouter`, `DecisionWorkflow` |
| 数据类 | PascalCase | `PipelineState`, `RouterResult` |

### 函数/方法命名

| 类型 | 约定 | 示例 |
|------|------|------|
| 异步函数 | snake_case | `safe_click`, `extract` |
| 同步函数 | snake_case | `check_roi`, `analyze` |
| 内部方法 | _snake_case | `_call_agent`, `_recommend_agents` |

## 新增代码位置指引

### 新增同步阶段组件

**位置:** `scripts/sync_pipeline.py`
**模式:** 创建新类继承流水线阶段逻辑
```python
class NewStage:
    def __init__(self, params):
        ...

    async def execute(self, page: Page, state: PipelineState):
        ...
```

### 新增 Agent

**位置:** `decision_system/`
**模式:** 在对应文件中添加函数/类
```python
# decision_system/new_agent.py
async def new_agent(input: str, context: dict) -> dict:
    ...
```

### 新增决策路由器场景

**位置:** `decision_system/router.py`
**方法:** `_determine_scenario_type()`, `_recommend_agents()`
**模式:** 添加场景类型和 Agent 映射

### 新增测试

**位置:** `decision_system/tests/test_<module>.py`
**框架:** pytest
**模式:**
```python
def test_new_feature():
    ...
```

## 特殊目录说明

### .venv/ (Python 虚拟环境)

- 用途: 隔离的项目依赖
- 管理: `python -m venv .venv`
- 激活: `source .venv/bin/activate` (Linux) 或 `.venv\Scripts\activate` (Windows)

### .playwright-cli/ (Playwright CLI 日志)

- 用途: 浏览器自动化调试日志
- 内容: console 日志和 page YAML
- 清理: 可安全删除，不影响主流程

### .dumate/ (Dumate 框架)

- 用途: 可能是内部框架残留
- 状态: 包含 `inbox/RELEASE_v2.0.0.md`
- 处理: 不影响主流程

---

*结构分析: 2026-04-07*
