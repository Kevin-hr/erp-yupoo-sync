# PRD (产品需求文档) - Yupoo to ERP Auto-Sync System
**Version / 版本**: v1.0-DRAFT  
**Date / 日期**: 2026-04-02  
**Author / 作者**: Antigravity AI  

---

## 0. 核心架构 (Industrialized Architecture)
本项目遵循 **"Cloud-First & Pipeline-Based"** 工业化架构：
1. **SSOT (唯一事实来源)**: 采集的数据将通过 `product_batch.json` 并在未来对接 Feishu Bitable 进行审计。
2. **Decoupling (解耦)**: 浏览器上下文完全隔离，敏感信息仅存放于 `.env`。
3. **Resumability (可恢复性)**: 每个步骤均有状态持久化，支持断点续传。

---

## 1. Background & Problem (背景与问题)

当前上架流程为纯手工操作，需要人工：
1. 登录 Yupoo → 找到新品 → 手动切换后台 → 逐一复制图片外链
2. 登录 ERP (MrShopPlus) → 复制商品 → 删除旧图 → 粘贴新图 → 保存

**核心痛点**：操作分散于两个不同 URL 系统，有登录状态管理问题，且是流水线作业，可并发，但目前全靠人工重复执行。

---

## 2. Goal (目标)

> 构建一个全自动、低自由度的定时采集与上架系统，将 Yupoo 新品图片外链同步至 MrShopPlus，实现"零人工"上架。

### 成功指标 (Success Metrics / KPI)
| 指标 | 当前 (As-Is) | 目标 (To-Be) |
| :--- | :--- | :--- |
| 单品上架耗时 | ~15 分钟/人工 | < 2 分钟/自动 |
| 并发处理能力 | 1 人 × 1 品 | N 品同时处理 |
| 错误率 | 人为失误 ~5% | 自动验证 < 1% |
| 触发方式 | 人工手动 | 定时 + 手动 CLI |

---

## 3. Scope (范围) — [MECE]

### 3.1 Platform A: Yupoo (采集端)
- **URL**: `https://lol2024.x.yupoo.com/albums`
- **账号 / 密码**: `lol2024` / `9longt#3`
- **核心任务**: 采集图片外链列表（≤14张/品）+ 商品标题

### 3.2 Platform B: MrShopPlus ERP (上架端)
- **URL**: `https://www.mrshopplus.com/#/login?redirect=%2Fmain`
- **账号 / 密码**: `zhiqiang` / `123qazwsx`
- **核心任务**: 进入商品表单 → 替换图片 → 保存上架

> [!IMPORTANT]
> 两平台必须作为**独立进程/Agent**处理，不能混用同一浏览器上下文。

### 3.3 Out of Scope (本期不含)
- 价格自动计算
- 文字描述 AI 生成
- 多站点同步（当前仅 `stockxshoes` 站点）

---

## 4. Verified Operational Flow (已验证的实际操作流程)

### Stage 1: Yupoo 采集（9步法）

```
[登录 lol2024.x.yupoo.com/albums]
    ↓
1. 分类导航：全部分类 → 选择目标分类（如 BAPE-芭比）
2. 循环遍历：从左到右，从上到下
3. 详情下钻：点击进入目标商品
4. 复制 URL：保存当前商品页 URL（作为 SKU 锚点）
5. 进入后台：点击右上角"进入后台"
6. 搜索定位：粘贴产品名称到后台搜索框
7. 全选图片：筛选结果控制在 ≤ 14 款
8. 批量外链：批量外链 → 链接 → 复制
9. OUTPUT：获得图片 URL 列表（换行分隔）
```

### Stage 2: ERP 上架（6步法）

```
[登录 MrShopPlus ERP]
    ↓
1. 商品管理：进入商品管理列表
2. 复制：点击存量商品的"复制"图标 → 进入新品表单
3. 删除旧图：清空商品图片/视频区域的所有现有图片
4. URL 上传：点击 + → URL上传 → 粘贴外链列表（≤14 条）
5. 插入：点击"插入图片视频"
6. 保存：确认图片数量 (14张 + 1 留白) → 点击"保存"
```

### Stage 3: 字段映射 (Field Mapping)

| Yupoo 来源 | MrShopPlus 字段 | 处理逻辑 |
| :--- | :--- | :--- |
| 相册标题 | `商品名称` | 去除内部编号（如 H110），保留品牌+描述 |
| 相册描述（尺码行） | `商品描述` | 提取 M/XL/2XL 等尺码信息 |
| 图片外链列表 | `商品图片` | 批量 URL 上传，≤14 张，第 15 位留给尺码表 |
| 当前分类 | `类别` | 按分类名映射（如 BAPE → T-Shirt / Clothing） |

---

## 5. System Architecture (系统架构)

```
CLI 触发 / 定时任务
        ↓
  Orchestrator (编排器)
   ├── Yupoo Agent (采集端)
   │     └── 输出: product_batch.json
   └── ERP Agent (上架端)  ← 并发消费 product_batch.json
         └── 输出: 上架日志
```

### 关键约束 (Constraints)
- **并发**: ERP Agent 支持多 Worker 并发（默认 ≤3，防止账号风控）
- **图片上限**: 每品 ≤ 14 张（第 15 位预留给尺码表图片）
- **会话管理**: 两平台各自维护独立的登录 Cookie，定期刷新

### 5.2 技术红线 (Technical Red Lines)
1. **ASCII Only**: 所有生成的控制脚本 (.py除外, 主要是.ps1/.bat) 必须为纯英文字符。
2. **Concurrent ≤ 3**: 严禁突破并发上限，保障 MrShopPlus 账号安全。
3. **Screenshots Mandatory**: 每一单保存前必须截取 `Saving...` 状态及结果。

---

## 6. Skill / Agent / CLI Design (设计原则)

### 触发条件
| 触发词 | 动作 |
| :--- | :--- |
| "上架新品" / "同步 Yupoo" / "开始循环采集" | 启动全量采集 + 上架流程 |
| "同步 BAPE-芭比" (指定分类) | 仅处理该分类 |
| 定时器（可配置间隔） | 自动轮询，检测新品 |

### CLI 命令
```bash
python cli.py sync --category "BAPE-芭比"   # 指定分类
python cli.py sync --all                    # 全量同步
python cli.py watch --interval 30           # 定时监听（分钟）
python cli.py status                        # 查看任务状态
```

---

## 7. Open Questions (待决策)

> [!IMPORTANT]
> 以下问题在 PRD 审批前需要确认：

1. **尺码表图片**：第 15 张位置的尺码表图从哪里获取？是 ERP 内已有模板还是从 Yupoo 下载？
2. **新品检测逻辑**：如何判断一个 Yupoo 相册是"新"的？使用相册 ID 对比历史记录？
3. **商品标题翻译**：是 AI 自动翻译还是有固定中英对照表？
4. **失败重试**：上架失败（如图片加载超时）时，自动重试还是记录日志等待人工排查？

---

## 8. Acceptance Criteria (验收标准)

- [ ] 给定分类名，系统自动完成从 Yupoo 外链提取到 ERP 保存的全流程，无人工干预
- [ ] 每品处理时间 < 2 分钟
- [ ] 图片数量精确控制在 ≤ 14 张
- [ ] 会话中断后可自动重新登录并恢复任务

---
*基于实际操作截图及用户提供的真实凭证构建 — 实事求是*
