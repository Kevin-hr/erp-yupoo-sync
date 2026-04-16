# Deployment SOP: erp-yupoo-sync (v2.0)

> 本指南指导在未知系统环境下，从零构建并运行 `erp-yupoo-sync` 自动化同步项目。

---

## ⚠️ 当前状态（必读）

**双架构并行：架构A(Playwright流水线) + 架构B(Excel中转)**

| 架构 | 脚本 | 状态 | 适用场景 |
|------|------|------|----------|
| **A: Playwright流水线** | `sync_pipeline.py` | ✅ 生产可用 | 单商品全自动，约2分钟 |
| **B: Excel中转批量导入** | `generate_saint_excel*.py` | ✅ 生产验证 | DESCENTE/SAINT已验证 |

---

## 步骤一：前置环境与网络梳理

### 1.1 工具自检 (Env Check)

```bash
git --version
python --version  # 或 python3 --version
npm --version     # playwright-cli 需要
```

### 1.2 网络代理配置 (Proxy Setup)

若宿主机 VPN 运行在 `127.0.0.1:7890`：

**Windows (PowerShell):**
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
```

**Linux / macOS (Bash/Zsh):**
```bash
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
```

---

## 步骤二：安全克隆与环境隔离

### 2.1 仓库克隆

```bash
git clone https://github.com/Kevin-hr/erp-yupoo-sync.git
cd erp-yupoo-sync
```

### 2.2 虚拟环境初始化

**Windows (PowerShell):**
```powershell
# 解决执行权限问题
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 步骤三：强健的依赖构建

### 3.1 Python 依赖安装

```bash
pip install playwright pytest pydantic openpyxl requests
playwright install chromium
```

### 3.2 浏览器 CLI 工具安装（可选）

```bash
npm install -g @playwright/cli@latest
```

---

## 步骤四：业务配置注入 (.env)

在根目录创建 `.env` 文件：

```ini
# --- ERP 登录凭证 ---
ERP_USERNAME=zhiqiang
ERP_PASSWORD=123qazwsx

# --- Yupoo 登录凭证 ---
YUPOO_USERNAME=lol2024
YUPOO_PASSWORD=9longt#3

# --- 自动化策略 (Playwright) ---
HEADLESS=False
MAX_WORKERS=1  # 当前只支持单worker

# --- 路径配置 ---
COOKIE_PATH=logs/cookies.json
YUPOO_COOKIE_PATH=logs/yupoo_cookies.json
```

---

## 步骤五：执行方式选择

### 架构A: Playwright 6阶段流水线（全自动）

**前置：启动Chrome（CDP模式）**
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**执行命令**
```bash
cd C:\Users\Administrator\Documents\GitHub\ERP

# 单商品同步（约2分钟/个）
python scripts/sync_pipeline.py --album-id 231019138 \
  --brand-name "DESCENTE" --product-name "BS W ZIP JACKET" --use-cdp
```

**成功标志：**
1. 终端输出 `Pipeline Execution Success`
2. `screenshots/verify_*.png` 截图生成

---

### 架构B: Excel中转批量导入（批量）

**Step 1: 生成Excel填充数据**

```bash
# DESCENTE品牌
python scripts/generate_saint_excel_v2.py --brand DESCENTE --album-id 232338513

# SAINT品牌
python scripts/generate_saint_excel.py --album-id 527345264973337
```

**Step 2: ERP后台批量导入**

1. 打开 ERP 后台: https://www.mrshopplus.com
2. 导航到商品管理 → 批量导入
3. 上传生成的 Excel 文件
4. 确认导入

**验证文件：**
- `DESCENTE_232338513_商品导入模板.xlsx` ✅
- `logs/SAINT_商品导入模板_填充.xlsx` ✅

---

## 吞吐计算

| 架构 | 方式 | 每商品耗时 | 每小时产出 |
|------|------|-----------|-----------|
| A: Playwright | 全自动 | ~2分钟 | ~30款/小时 |
| B: Excel中转 | 批量 | 手动导入 | 取决于批量大小 |

---

## 关键约束（P0级）

| 规则 | 说明 |
|------|------|
| **强制下架** | I列=必须填写N，禁止自动上架 |
| **图片≤14张** | 单商品最多14张图片 |
| **独立浏览器** | Yupoo/MrShopPlus必须各自独立上下文 |
| **Cookie过期** | 会话Cookie需定期手动刷新 |

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| ERP Cookie失效 | 会话过期 | 重新登录获取Cookie |
| Yupoo验证码 | 阿里云拦截 | 手动验证后重试 |
| 图片404 | URL路径错误 | 使用XHR拦截获取完整path |

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `scripts/sync_pipeline.py` | ✅ 架构A主脚本 |
| `scripts/generate_saint_excel*.py` | ✅ 架构B Excel生成 |
| `logs/` | 凭证、日志、填充结果 |
| `screenshots/` | 截图留证 |
| `docs/pipeline_flowchart.html` | ✅ 流水线流程图 v8.0 |
| `docs/yupoo_to_erp_excel_flow.html` | ✅ Excel中转流程图 v2.0 |

---

> v2.0 | 2026-04-15 | 新增架构B(Excel中转)，验证DESCENTE/SAINT模板
