# 系统架构

**分析日期:** 2026-04-07

## 整体架构概述

**架构模式:** Pipeline Orchestration（流水线编排）+ 决策认知系统双层架构

**核心组件:**
- **同步流水线层**: Playwright 浏览器自动化，执行 Yupoo → MrShopPlus 图片同步
- **决策认知层**: 多 Agent 决策路由系统，支持 ROI 过滤和偏差扫描

## 核心架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                      ERP Yupoo-Sync                              │
├─────────────────────────────────────────────────────────────────┤
│  CLI / 定时任务触发                                              │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          SyncPipeline (编排器 - 6阶段流水线)              │    │
│  │  EXTRACT → PREPARE → LOGIN → NAVIGATE → UPLOAD → VERIFY │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  Playwright Browser Automation                                   │
│         ↓                                                        │
│  MrShopPlus ERP 上架                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Decision Cognition System                     │
├─────────────────────────────────────────────────────────────────┤
│  User Input                                                     │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              DecisionRouter (路由器)                      │    │
│  │  - ROI 红线检查 (META-01)                                │    │
│  │  - 场景分类 (CORE-01)                                    │    │
│  │  - 主要矛盾提取 (CORE-02)                                │    │
│  │  - Agent 推荐 (CORE-04)                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  Circuit Breaker (熔断器, max_hops=5)                           │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         DecisionWorkflow (工作流编排器)                   │    │
│  │  - 顺序 Agent 调度 (Phase 1 行为)                         │    │
│  │  - 仲裁逻辑 (Phase 3 扩展)                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│         ↓                                                        │
│  Agent Chain → [WiseDecider, BiasScanner, FirstPrinciple...]   │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline 流水线架构 (sync_pipeline.py)

### 阶段定义

| 阶段 | 枚举值 | 组件类 | 核心职责 |
|------|--------|--------|----------|
| EXTRACT | PipelineStage.EXTRACT (1) | `YupooExtractor` | 从 Yupoo 相册提取图片外链（9步提取逻辑） |
| PREPARE | PipelineStage.PREPARE (2) | `MetadataPreparer` | URL 格式化和元数据准备（隐含在 run() 中） |
| LOGIN | PipelineStage.LOGIN (3) | `MrShopLogin` | MrShopPlus ERP Cookie 认证 |
| NAVIGATE | PipelineStage.NAVIGATE (4) | 内联在 `SyncPipeline.run()` | 访问商品列表并定位模板商品 |
| UPLOAD | PipelineStage.UPLOAD (5) | `ImageUploader` + `DescriptionEditor` | 替换标题、上传图片（≤14张）、格式化描述 |
| VERIFY | PipelineStage.VERIFY (6) | `Verifier` | 截图存证 + 保存验证（URL 变化 = action=3） |

### 关键类设计

**YupooLogin** (`scripts/sync_pipeline.py:145-178`)
- 职责: Yupoo 登录认证与 Cookie 持久化
- 方法: `login(context: BrowserContext) -> bool`
- 流程: 检查 `logs/yupoo_cookies.json` → 存在则加载 → 否则登录并保存

**YupooExtractor** (`scripts/sync_pipeline.py:181-242`)
- 职责: 图片外链批量提取
- 方法: `extract(page: Page) -> List[str]`
- 核心逻辑: 直连相册 → 全选图片 → 批量外链按钮 → 预览/生成 → textarea 提取
- 限制: 强制 ≤14 张（第15位预留给尺码表）

**MrShopLogin** (`scripts/sync_pipeline.py:246-277`)
- 职责: MrShopPlus ERP 认证
- 方法: `login(context: BrowserContext) -> bool`
- Cookie 文件: `logs/cookies.json`

**ImageUploader** (`scripts/sync_pipeline.py:280-300`)
- 职责: URL 图片顺序上传
- 方法: `upload(page: Page)`
- 流程: 清理旧图 → 打开弹窗 → 切换URL上传标签 → 粘贴 URLs → 插入图片视频

**DescriptionEditor** (`scripts/sync_pipeline.py:319-384`)
- 职责: 商品描述首行格式化
- 方法: `format_description(page: Page)`
- 逻辑: 注入 JS 查找富文本编辑器，定位 `Name:` 段落并替换为首行 HTML

**Verifier** (`scripts/sync_pipeline.py:302-317`)
- 职责: 最终验证与保存
- 方法: `verify(page: Page)`
- 验证标志: URL 包含 `action=3`（唯一可靠的成功标志）

**SyncPipeline** (`scripts/sync_pipeline.py:391-438`)
- 职责: 主工业同步引擎，6阶段流水线编排
- 方法: `run()`
- 状态管理: `PipelineState` dataclass，支持断点续传

### 数据流

```
YupooAlbum (album_id)
    ↓ [YupooLogin.login()]
YupooExtractor.extract()
    ↓ [返回 image_urls List[str]]
SyncPipeline.run() 内联处理
    ↓ [MrShopLogin.login()]
商品列表页 → 点击"复制"模板
    ↓ [ImageUploader.upload()]
图片插入完成
    ↓ [DescriptionEditor.format_description()]
描述格式化完成
    ↓ [Verifier.verify()]
截图 + 保存 → action=3 验证
```

### 状态管理

**PipelineState** (`scripts/sync_pipeline.py:127-139`)
```python
@dataclass
class PipelineState:
    album_id: str
    current_step: int = 1
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_stages: List[str] = field(default_factory=list)
    error: Optional[str] = None
```
- 持久化: JSON 序列化到 `logs/pipeline_state.json`
- 断点续传: `--step N --resume` 参数支持

## 决策认知系统架构 (decision_system/)

### 路由器 (DecisionRouter)

**文件:** `decision_system/router.py`

**核心方法:**
- `analyze(user_input: str, roi_value: Optional[float]) -> RouterResult`
- `_determine_scenario_type(user_input: str) -> SceneType`
- `_extract_main_conflict(user_input: str) -> Tuple[str, ConflictCategory]`
- `_recommend_agents(scene_type: SceneType) -> List[str]`

**场景分类 (SceneType):**
| 场景 | 关键词 | 推荐 Agents |
|------|--------|------------|
| TRIVIAL | 吃什么/几点/哪里买/天气 | [] (快速路径) |
| REVERSIBLE | 试试/测试/换一个/样品 | [] (快速路径) |
| MAJOR | 独立站/大批量/战略/千万 | wise-decider-001, bias-scanner-001 |
| INNOVATIVE | 全新类目 | wise-decider-001, first-principle-001 |
| EMOTIONAL | 担心/风险/害怕 | bias-scanner-001 |

**ROI 红线 (META-01):**
- 负 ROI → `scene_type = BLOCKED`，直接阻断决策
- 关键词检测: 免费/赠送/亏本/无条件等

### 工作流编排器 (DecisionWorkflow)

**文件:** `decision_system/workflow.py`

**方法:**
- `run(user_input: str, roi_value: Optional[float]) -> WorkflowResult`
- `dispatch_agents(user_input, agent_list, router_result) -> WorkflowResult`

**熔断器 (CircuitBreaker):**
- 最大跳数: `MAX_HOPS = 5`
- 防止 Agent 路由循环

### 数据结构

**RouterResult** (`decision_system/types.py:40-65`)
```python
class RouterResult(BaseModel):
    scenario_type: SceneType
    main_conflict: str
    complexity: str
    emotion_state: str
    options_clear: bool
    recommended_agents: List[str]
    reason: str
    key_questions: List[str]
    hop_count: int = 0
    roi_blocked: bool = False
```

**WorkflowResult** (`decision_system/workflow.py:9-17`)
```python
@dataclass
class WorkflowResult:
    router_result: Optional[Dict[str, Any]] = None
    agent_results: List[Dict[str, Any]] = field(default_factory=list)
    circuit_open: bool = False
    circuit_error: Optional[Dict[str, Any]] = None
    final_decision: Optional[str] = None
    final_action: Optional[str] = None
```

## 设计模式

### 1. Pipeline Orchestration (流水线编排)
- 用于: 图片同步流程
- 实现: `SyncPipeline` 类按顺序调用各阶段组件
- 优点: 清晰、可追踪、易于断点续传

### 2. Decorator + Retry (装饰器重试)
- 用于: `async_retry` 装饰器 (`scripts/sync_pipeline.py:76-91`)
- 实现: 指数退避 (initial_backoff * 2^attempt)
- 应用: `safe_click`, `safe_fill`

### 3. State Machine (状态机)
- 用于: `PipelineStage` 枚举定义阶段
- 实现: Enum + PipelineState dataclass

### 4. Factory Method (工厂方法)
- 用于: 各组件类自身处理初始化
- 示例: `YupooExtractor(album_id).extract(page)`

### 5. Strategy Pattern (策略模式)
- 用于: 场景分类和 Agent 推荐逻辑
- 实现: `_recommend_agents()` 根据场景类型返回不同 Agent 列表

## 关键设计约束

| 约束 | 来源 | 影响 |
|------|------|------|
| 图片 ≤14 张 | 业务红线 | `YupooExtractor.extract()` 强制 `list(urls[:14])` |
| 并发 ≤3 | 业务红线 | 未来可扩展 Worker 池 |
| 独立浏览器上下文 | BROWSER_SUBAGENT_SOP.md | Yupoo/MrShopPlus 禁止共享 Cookie |
| 截图存证 | 业务要求 | `Verifier.verify()` 每次保存前截图 |
| action=3 验证 | 唯一可靠标志 | `Verifier.verify()` 等待 URL 变化 |

## 跨-cutting concerns

**日志:** Python logging 模块，写入 `logs/sync_{date}.log` + `logs/decisions.jsonl`

**错误处理:** 指数退避重试 (max_retries=3)，异常仅在熔断时阻断流程

**认证:** Cookie 持久化到 JSON 文件，复用会话

---

*架构分析: 2026-04-07*
