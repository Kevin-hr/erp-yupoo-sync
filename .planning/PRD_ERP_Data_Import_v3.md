# ERP 数据同步系统 PRD v4.0

> **文档版本**：v4.0（全面复盘更新）
> **作者**：雲帆 AI
> **日期**：2026-04-10
> **状态**：🚧 生产可用（基于 sync_pipeline.py v2.3.0 验证）

---

## 1. 项目概述与目标

### 1.1 业务背景

| 维度 | 现状 |
|------|------|
| **上游数据源** | Yupoo 相册（4000+款商品，图片+标题+描述） |
| **目标系统** | MrShopPlus ERP（批量导入模式） |
| **历史方案** | Playwright UI 自动化（约2分钟/单，SPA路由踩踏，无法并发） |
| **已验证方案** | Playwright 6阶段流水线 + CDP XHR拦截（生产可用） |
| **废弃方案** | 所有并发架构（共享CDP/Tab池/独立Browser+Cookie）均失败 |

### 1.2 核心指标（KPI）

| 指标 | 目标值 | 实际状态 | 说明 |
|------|--------|---------|------|
| **吞吐量** | 4000款/小时 | ❌ 未达成 | 当前单worker约2分钟/款 |
| **错误率** | < 0.5% | ⚠️ 待验证 | 结构化转换，无随机性 |
| **人工干预** | 仅最后一步点击"导入" | ⚠️ 部分达成 | 流水线已自动化，人工仅确认 |
| **业务红线遵守率** | 100% | ✅ 已验证 | 下架强制、14图截断、旧图清除 |
| **截图留证** | 每步截图 | ✅ 已验证 | screenshots/ 目录20+张PNG |

### 1.3 方案对比（全面复盘）

| 方案 | 速度 | 稳定性 | 结论 |
|------|------|--------|------|
| Playwright 单worker + CDP | ~2分钟/款 | ✅ **生产可用** | **唯一稳定方案** |
| 共享CDP + 多worker并发 | — | ❌ SPA踩踏失败 | 所有并发方案均废弃 |
| ETL + Excel批量导入 | 秒级/4000款 | 🔄 待开发 | PRD v3.0规划，未实现 |
| Tab池管理器 | — | ❌ ERP SPA无新Tab | 假设错误：复制=SPA路由跳转 |

---

## 2. 系统架构

### 2.1 数据流转图（已验证生产架构）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Yupoo-to-ERP 6阶段流水线 (v2.3.0)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Stage 1: EXTRACT       Stage 2: PREPARE        Stage 3: LOGIN          │
│  ┌──────────────┐       ┌──────────────────┐   ┌────────────────────┐  │
│  │ CDP XHR拦截  │       │ URL换行分隔      │   │ Cookie注入认证     │  │
│  │ /api/albums/ │  →    │ ≤14图片截断      │  → │ 26个Cookie完整     │  │
│  │ {id}/photos  │       │ 标题/描述清洗    │   │ 独立Browser Context│  │
│  └──────────────┘       └──────────────────┘   └────────────────────┘  │
│                                                                         │
│  Stage 4: NAVIGATE      Stage 5: UPLOAD          Stage 6: VERIFY        │
│  ┌──────────────┐       ┌──────────────────┐   ┌────────────────────┐  │
│  │ 访问商品列表  │       │ Fresh Navigation │   │ 截图留证           │  │
│  │ 定位模板商品  │  →    │ JS注入绕过       │  → │ URL含action=3     │  │
│  │ 点击"复制"   │       │ textarea maxlen  │   │ 验证保存成功       │  │
│  └──────────────┘       │ TinyMCE清理旧图  │   └────────────────────┘  │
│                         └──────────────────┘                            │
│                                                                         │
│  输出: raw_data.json     输出: 格式化数据         输出: screenshots/   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 职责 | 输入 | 输出 | 状态 |
|------|------|------|------|------|
| `sync_pipeline.py` | 主入口：6阶段编排器 | album_id | 商品上架+截图 | ✅ 生产可用 |
| `extract_category_albums_cdp.py` | 并发提取分类相册 | category | raw JSON | ⚠️ 并发废弃 |
| CDP XHR拦截 | 拦截完整path（含hash） | — | photos[] | ✅ 解决404 |

---

## 3. 核心防错机制（已验证）

### 3.1 业务红线（强制遵守）

| 红线规则 | 违反后果 | 验证状态 |
|---------|---------|---------|
| **禁止终端驱动浏览器** | 指纹污染触发风控 | ✅ 已验证 |
| **强制下架状态=N** | 误发风险 | ✅ 已验证 |
| **XHR拦截获取完整Path** | 404图片丢失 | ✅ 已验证 |
| **Fresh Navigation** | Vue组件未挂载 | ✅ 已验证 |
| **JS注入绕过maxlength** | URL截断上传失败 | ✅ 已验证 |
| **独立Browser Context** | SPA路由踩踏 | ⚠️ 并发失败 |

### 3.2 关键突破（2026-04-08验证）

| 突破点 | 技术方案 | 效果 |
|--------|---------|------|
| **XHR拦截提取图片** | CDP拦截`/api/albums/{id}/photos`获取含hash完整path | 解决404问题 |
| **Fresh Navigation** | 复制后强制跳转`pkValues`编辑页激活Vue组件 | 解决页面挂载失败 |
| **JS注入上传** | `evaluate`直接控制`ta.value`绕过maxlength=153 | 解决URL被截断 |
| **TinyMCE旧图清理** | `editor.querySelectorAll('img').forEach(img=>img.remove())` | 解决描述残留图片 |
| **state-save/load** | playwright-cli导出完整Cookie+localStorage | 比纯Cookie注入更完整 |

---

## 4. ERP已验证选择器

| 功能 | 选择器 | 说明 |
|------|--------|------|
| 商品列表"复制"按钮 | `.operate-area .el-icon-document-copy` | Element Plus图标，非FontAwesome |
| 图片上传入口 | `.upload-container.editor-upload-btn` | 编辑区上传按钮 |
| URL上传Tab | `.el-tabs__item:has-text('URL')` | Element Plus Tab |
| URL输入框 | `.el-dialog .el-textarea__inner` | textarea有maxlength=153限制 |
| 确认上传按钮 | `.el-dialog__footer button.el-button--primary` | 弹窗底部确认 |
| TinyMCE iframe | `iframe[id^='vue-tinymce']` | Vue tinymce编辑器iframe |
| TinyMCE可编辑body | `#tinymce` | iframe内可编辑区域 |
| 商品名称输入 | `input[placeholder='请输入商品名称']` | ERP表单标题字段 |
| 尺码输入 | `.size-chart-input input` | 尺码表输入框 |
| 保存按钮 | `button:has-text('保存')` | 触发action=3 |
| 下架开关 | `el-switch__core` | 探测并强制设为N |

---

## 5. 并发踩坑教训（已验证废弃）

### 5.1 禁止再用的失败架构

| 架构 | 失败原因 | 教训 |
|------|---------|------|
| 共享CDP Chrome + 多worker | SPA路由状态互相踩踏 | 所有worker共享单一CDP session |
| Tab池管理器 | ERP"复制"是SPA路由跳转，非新Tab | 假设新Tab是错的 |
| 独立Browser + 仅Cookie注入 | Yupoo/MrShopPlus依赖localStorage | Cookie注入≠Session保持 |
| emoji在Windows GBK日志 | `UnicodeEncodeError` | 日志输出严禁emoji |

### 5.2 唯一正确并发路径

```
每个worker = 独立Chrome实例 + 独立CDP端口(9222/9223/...) + subprocess进程隔离
```

**当前状态**：此方案未实现，单worker是唯一生产可用方案。

---

## 6. 已知问题清单（P0/P1/P2）

> 来自5Agent并发审查（2026-04-08）

### 6.1 P0问题（必须修复）

| # | 问题 | 位置 | 修复方案 |
|---|------|------|---------|
| P0-1 | 凭证硬编码默认值 | `sync_pipeline.py:265` | 移除默认值，强制.env读取 |
| P0-2 | Cookie无过期检测 | `sync_pipeline.py:L366-375` | 添加expiry字段检查 |
| P0-3 | concurrent_batch_sync.py共享context | `L391-398` | 废弃此文件，使用sync_pipeline.py |
| P0-4 | sync_pipeline.py零测试 | 全文803行无pytest | 补充Stage级集成测试 |
| P0-5 | workflow.py核心编排无测试 | `L75-102` | run()方法ROI guard分支测试 |
| P0-6 | 无requirements.txt | 项目根目录 | 创建依赖锁定文件 |

### 6.2 P1问题（应该修复）

| # | 问题 | 位置 |
|---|------|------|
| P1-1 | --resume/--step/--dry-run文档与代码不符 | argparse未实现 |
| P1-2 | Magic Number散落 | timeout值多处不一致 |
| P1-3 | bare except静默吞异常 | `except: pass`应改为logger.warning |
| P1-4 | 日志无trace_id | job_id/session_id缺失 |
| P1-5 | 凭证写入明文logs/cookies.json | JWT Token存在账户劫持风险 |

### 6.3 P2问题（可以修复）

| # | 问题 | 位置 |
|---|------|------|
| P2-1 | 缺少cast类型标注 | sync_pipeline.py无`from typing import cast` |
| P2-2 | TinyMCE L588-591死代码 | 未完成的pass空块 |
| P2-3 | 缺少captcha检测实现 | CLAUDE.md要求但代码无实现 |

---

## 7. 执行 SOP

### 7.1 准备阶段

```
□ Step 1: 确认 CDP Chrome 已启动
  → "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

□ Step 2: 确认 Yupoo Cookie 有效
  → playwright-cli state-save yupoo_session.json
  → 访问 https://lol2024.x.yupoo.com 若需登录则重新获取

□ Step 3: 确认 ERP Cookie 有效
  → playwright-cli state-save erp_session.json
  → 访问 MrShopPlus 商品列表验证

□ Step 4: 安装依赖
  → pip install playwright pytest pydantic
  → playwright install chromium
```

### 7.2 执行阶段

```
□ Step 1: 运行同步流水线
  → python scripts/sync_pipeline.py --album-id 231019138 --use-cdp

□ Step 2: 监控执行日志
  → tail -f logs/sync_YYYYMMDD.log

□ Step 3: 验证截图
  → 检查 screenshots/ 目录，确认 action=3 URL 截图存在
```

### 7.3 断点续跑

```
□ 使用 --resume 参数（如已实现）
  → python scripts/sync_pipeline.py --resume --job-id <previous_job_id>

□ 手动断点续跑
  → 编辑 logs/pipeline_state.json 设置 start_stage
```

---

## 8. playwright-cli 工具链

> 终端原生浏览器 CLI，无需写 Python 脚本

| 命令 | 用途 | 场景 |
|------|------|------|
| `playwright-cli state-save session.json` | 导出完整会话状态 | **绕过登录首选** |
| `playwright-cli state-load session.json` | 导入完整会话状态 | 恢复登录状态 |
| `playwright-cli screenshot [target]` | 截图 | 截图留证 |
| `playwright-cli tab-list/new/close` | Tab管理 | 多Tab操作 |
| `playwright-cli cookie-list/set/delete` | Cookie管理 | Session调试 |
| `playwright-cli localstorage-set/get/clear` | localStorage管理 | 认证持久化 |
| `playwright-cli network` | 查看网络请求 | XHR拦截调试 |

---

## 9. 决策认知系统 v2.0（Phase 1完成）

### 9.1 架构

```
用户输入 → ROI检查 → 场景分类 → Agent推荐 → CircuitBreaker → 顺序执行
```

### 9.2 组件

| 组件 | 文件 | 状态 |
|------|------|------|
| 路由器 | `decision_system/router.py` | ✅ 完成 |
| 熔断器 | `decision_system/circuit_breaker.py` | ✅ 完成 |
| 日志 | `decision_system/logging_utils.py` | ✅ 完成 |
| CLI | `decision_system/cli.py` | ✅ 完成 |
| 单元测试 | `decision_system/tests/` (12个) | ✅ 完成 |

### 9.3 业务规则

| 规则 | 动作 |
|------|------|
| ROI为负 | 立即BLOCK，输出"止亏" |
| 首次网红合作 | 推荐"Model B压测"，$10/15videos |
| 流量门槛 | ≥1000播放才符合合作资格 |

---

## 10. 项目结构

```
ERP/
├── scripts/
│   ├── sync_pipeline.py              # ✅ 主入口：6阶段流水线（生产可用）
│   ├── concurrent_batch_v2.py        # ❌ 废弃：共享CDP Bug
│   ├── concurrent_batch_sync.py      # ❌ 废弃：共享context Bug
│   ├── erp_tab_manager.py            # ❌ 废弃：Tab池假设失败
│   ├── batch_sync_we11done.py        # 独立脚本：we11done品牌
│   ├── listing_only.py               # 独立脚本：仅同步Listing
│   └── test_form_upload.py           # 开发调试：表单上传
├── decision_system/                  # 决策认知系统 v2.0
│   ├── router.py / circuit_breaker.py / logging_utils.py / cli.py
│   └── tests/                        # 12个单元测试
├── logs/
│   ├── sync_YYYYMMDD.log             # 流水线日志
│   ├── decisions.jsonl               # 决策日志
│   ├── cookies.json                  # ERP Cookie
│   └── yupoo_cookies.json           # Yupoo Cookie
├── screenshots/                      # 上架前截图留证
├── .planning/                         # 项目规划文档
├── BROWSER_SUBAGENT_SOP.md          # 浏览器操作安全协议
├── GEMINI.md                        # AI规则与决策原则
├── memory.md                        # 项目经验教训
└── CLAUDE.md                       # 本文件
```

---

## 11. Release 流程（必须遵守）

```bash
# 1. 提交代码
git add . ; git commit -m "feat: ..."

# 2. 创建并推送标签（关键！）
git tag v<x.y.z>
git push origin v<x.y.z>

# 3. 验证标签存在
gh release list

# 4. 创建 Release
gh release create v<x.y.z> --title "..." --notes "..."
```

**违规后果**：`gh release create` 在标签未推送到远程时会卡顿/超时。

---

**文档结束**
