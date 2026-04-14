# Deployment SOP: erp-yupoo-sync (v1.0)

本指南旨在指导 DevOps 工程师在未知系统环境下，从零构建并运行 `erp-yupoo-sync` 自动化同步项目。

## 步骤一：前置环境与网络梳理

在执行任何操作前，需确认基础工具可用性并配置代理以通过 VPN。

### 1.1 工具自检 (Env Check)
```bash
git --version
python --version  # 或 python3 --version
```

### 1.2 网络代理配置 (Proxy Setup)
若宿主机 VPN 运行在 `127.0.0.1:7890`，请在当前终端执行：

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

使用国内镜像源加速安装，并初始化 Playwright 内核。

### 3.1 Python 依赖安装
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3.2 浏览器内核安装
```bash
# 防超时建议：确保代理已生效
playwright install chromium
```

---

## 步骤四：业务配置注入 (.env)

在根目录创建 `.env` 文件，模板如下：

```ini
# --- ERP 登录凭证 ---
ERP_USERNAME=zhiqiang
ERP_PASSWORD=your_password_here

# --- Yupoo 登录凭证 ---
YUPOO_USERNAME=lol2024
YUPOO_PASSWORD=your_password_here

# --- 自动化策略 (Playwright) ---
# 是否使用无头模式 (RPA 调试建议设为 False)
HEADLESS=False
# 最大并发同步数量
MAX_WORKERS=3
# 默认 CDP 调试端口
DEFAULT_PORT=9222

# --- 路径配置 ---
COOKIE_PATH=logs/cookies.json
YUPOO_COOKIE_PATH=logs/yupoo_cookies.json
```

---

## 步骤五：最小闭环验证 (Smoke Test)

执行单品同步冒烟测试，验证全链路（提取->复制->上传->保存）是否打通。

```bash
# 使用内置的测试批次文件进行单 worker 验证
python scripts/concurrent_batch_v2.py --batch smoke_test.json --workers 1
```

**成功标志：**
1. 终端输出 `[231967755] ✓ 同步成功`。
2. `screenshots/` 目录下生成带有 `v2_verify_` 前缀的保存确认截图。
