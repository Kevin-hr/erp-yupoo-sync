# Coding Conventions

**Analysis Date:** 2026-04-07

## 命名模式 (Naming Patterns)

### 文件命名 (Files)

| 类型 | 模式 | 示例 |
|------|------|------|
| Python 模块 | `snake_case.py` | `sync_pipeline.py`, `circuit_breaker.py` |
| 测试文件 | `test_*.py` | `test_router.py`, `test_circuit_breaker.py` |
| 配置 | `snake_case.ini` | `pytest.ini` |

### 类命名 (Classes)

| 模式 | 示例 |
|------|------|
| PascalCase | `YupooLogin`, `SyncPipeline`, `DecisionRouter`, `CircuitBreaker` |
| 使用名词 | `ImageUploader`, `Verifier`, `DescriptionEditor` |

### 函数/方法命名 (Functions)

| 模式 | 示例 |
|------|------|
| snake_case | `safe_click`, `safe_fill`, `check_roi`, `async_retry` |
| 前缀 `safe_` 表示安全操作 | `safe_click`, `safe_fill` |
| 前缀 `_` 表示私有方法 | `_determine_scenario_type`, `_extract_main_conflict` |

### 变量命名 (Variables)

| 类型 | 模式 | 示例 |
|------|------|------|
| 实例变量 | snake_case | `album_id`, `image_urls`, `cookies_file` |
| 常量 | SCREAMING_SNAKE | `MAX_HOPS`, `LOG_FILE`, `NEGATIVE_ROI_KEYWORDS` |
| 类型别名 | PascalCase | `ROIStatus`, `SceneType` |
| 配置变量 | snake_case | `llm_timeout`, `llm_api_base` |

### 枚举成员 (Enum Members)

| 模式 | 示例 |
|------|------|
| UPPER_SNAKE_CASE | `TRIVIAL = "trivial"`, `POSITIVE = "positive"` |
| 值使用 lowercase | `SceneType.TRIVIAL.value == "trivial"` |

---

## 代码风格 (Code Style)

### 格式化 (Formatting)

- **工具**: 未检测到 Prettier/Black/ruff 配置
- **缩进**: 4 空格
- **行长度**: 未强制限制
- **编码**: UTF-8 (`# -*- coding: utf-8 -*-`)

### Linting

- 未检测到 `.eslintrc`, `ruff.toml`, `pylintrc` 等配置文件
- 无 pre-commit hooks

### Import 顺序 (Import Organization)

```python
# 1. 标准库
import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

# 2. 第三方库
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# 3. 本地模块
import decision_system.config as config
from decision_system.types import SceneType, ROIStatus, RouterResult
```

---

## 注释与文档 (Comments & Documentation)

### 模块级文档字符串 (Module-Level Docstrings)

```python
"""
Yupoo to MrShopPlus End-to-End Sync Pipeline (Yupoo 转 MrShopPlus 端到端同步流水线)

Architecture (架构):
    Stage 1: YupooExtractor    - Extract image URLs from Yupoo album (提取图片外链)
    Stage 2: MetadataPreparer  - Prepare image URLs and metadata (准备元数据)
    ...

Usage:
    python scripts/sync_pipeline.py --album-id 231019138
"""
```

### 分节注释 (Section Comments)

```python
# =============================================================================
# 1. Environment & Config (环境与配置)
# =============================================================================

# =============================================================================
# 2. Resiliency Helpers (弹性组件 - 包含重试与安全操作)
# =============================================================================

# =============================================================================
# 3. Pipeline Stages (流水线阶段定义)
# =============================================================================
```

### 函数文档字符串 (Function Docstrings)

```python
def async_retry(max_retries: int = 3, initial_backoff: float = 2.0):
    """Decorator for async retries with exponential backoff (异步重试装饰器)"""
    ...

async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False):
    """Safe click with wait and visibility check & dispatch fallback (安全点击)"""
    ...

async def login(self, context: BrowserContext) -> bool:
    """Handle Yupoo login with cookie persistence (处理登录与 Cookie 持久化)"""
    ...
```

### 行内注释 (Inline Comments)

```python
# Check for login redirect (检查是否被重定向到登录页)
if "login" in page.url:

# Force 14 rule (强制 14 张红线)
return list(urls[:14])

# Stage 0: Yupoo Authentication (Yupoo 登录认证)
class YupooLogin:
```

---

## 类型注解 (Type Annotations)

### typing 模块使用

```python
from typing import List, Optional, Dict, Any, Callable, Tuple

# 函数参数和返回值
def async_retry(max_retries: int = 3, initial_backoff: float = 2.0) -> Callable:
async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False) -> None:
async def extract(self, page: Page) -> List[str]:
async def verify(self, page: Page) -> None:

# 类型别名
def check_roi(user_input: str, roi_value: Optional[float] = None) -> tuple[ROIStatus, str]:
```

### Pydantic 模型

```python
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

class MainConflict(BaseModel):
    """主要矛盾 — frozen to prevent mutation"""
    model_config = ConfigDict(frozen=True)

    conflict: str
    category: ConflictCategory

    @field_validator('conflict')
    @classmethod
    def conflict_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('矛盾描述不能为空')
        return v.strip()

class RouterResult(BaseModel):
    scenario_type: SceneType
    main_conflict: str
    complexity: str
    options_clear: bool
    recommended_agents: List[str]
    ...
```

### dataclass 使用

```python
from dataclasses import dataclass, field, asdict

@dataclass
class PipelineState:
    """Tracks state for resumability (状态追踪与断点续传)"""
    album_id: str
    current_step: int = 1
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_stages: List[str] = field(default_factory=list)
    error: Optional[str] = None
```

### Enum 使用

```python
from enum import Enum

class PipelineStage(Enum):
    """Execution stages (执行阶段)"""
    EXTRACT = 1
    PREPARE = 2
    LOGIN = 3
    NAVIGATE = 4
    UPLOAD = 5
    VERIFY = 6

class SceneType(str, Enum):
    TRIVIAL = "trivial"
    REVERSIBLE = "reversible"
    MAJOR = "major"
    INNOVATIVE = "innovative"
    EMOTIONAL = "emotional"
    BLOCKED = "blocked"
```

---

## 错误处理 (Error Handling)

### async_retry 装饰器

```python
def async_retry(max_retries: int = 3, initial_backoff: float = 2.0):
    """Decorator for async retries with exponential backoff (异步重试装饰器)"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries: raise e
                    logger.warning(f"[{func.__name__}] Attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
            return None
        return wrapper
    return decorator

@async_retry(max_retries=3)
async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False):
    ...
```

### safe_click 安全回退

```python
@async_retry(max_retries=3)
async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False):
    """Safe click with wait and visibility check & dispatch fallback (安全点击)"""
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await page.click(selector, timeout=timeout, force=force)
    except Exception as e:
        if "outside" in str(e).lower() or "timeout" in str(e).lower():
            logger.info(f"Falling back to dispatch_event for {selector}")
            await page.dispatch_event(selector, 'click')
        else:
            raise e
```

### try/except 模式

```python
# 静默忽略 + 继续
if self.cookies_file.exists():
    try:
        with open(self.cookies_file, 'r', encoding='utf-8') as f:
            await context.add_cookies(json.load(f))
        return True
    except: pass  # 静默忽略

# 捕获并记录错误
except Exception as e:
    logger.error(f"Yupoo login error: {e}")
    return False
finally:
    await page.close()

# 捕获特定条件
except Exception as e:
    if "outside" in str(e).lower() or "timeout" in str(e).lower():
        # 处理特定错误
    else:
        raise e
```

---

## 日志记录 (Logging)

### 日志配置

```python
import logging
from datetime import datetime

LOG_FILE = LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sync_pipeline')
```

### 日志级别使用

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `logger.info()` | 正常流程步骤 | `logger.info("Yupoo cookies loaded.")` |
| `logger.warning()` | 可恢复错误/重试 | `logger.warning(f"[{func.__name__}] Attempt {attempt+1} failed...")` |
| `logger.error()` | 不可恢复错误 | `logger.error(f"Pipeline Crash (流水线崩溃): {e}")` |

### 日志格式

```
2026-04-07 10:30:45 [INFO] sync_pipeline: Extracting album directly: https://x.yupoo.com/gallery/231019138
2026-04-07 10:30:48 [WARNING] sync_pipeline: [safe_click] Attempt 1 failed: timeout... Retrying in 2.0s...
```

---

## 异步编程 (Async/Await)

### 装饰器模式

```python
def async_retry(max_retries: int = 3, initial_backoff: float = 2.0):
    """Decorator for async retries with exponential backoff"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            ...
        return wrapper
    return decorator

@async_retry(max_retries=3)
async def safe_click(...):
    ...
```

### Playwright 异步 API

```python
from playwright.async_api import async_playwright, Page, BrowserContext, Browser

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1280, 'height': 800})
    page = await context.new_page()
    
    await page.goto("https://x.yupoo.com/login")
    await page.wait_for_load_state('networkidle')
    await page.click(".login__button")
    
    cookies = await context.cookies()
```

### asyncio.sleep 使用

```python
await asyncio.sleep(3)    # 固定等待
await asyncio.sleep(0.5)   # 短延迟
await asyncio.sleep(backoff)  # 指数退避
```

---

## 代码组织 (Code Organization)

### 模块结构

```
ERP/
├── scripts/
│   └── sync_pipeline.py       # 主入口 (448 行)
├── decision_system/
│   ├── __init__.py
│   ├── __main__.py
│   ├── router.py              # 决策路由 (105 行)
│   ├── types.py               # Pydantic 类型定义 (71 行)
│   ├── config.py              # 配置常量 (28 行)
│   ├── circuit_breaker.py      # 熔断器 (25 行)
│   ├── logging_utils.py        # 日志工具 (30 行)
│   ├── cli.py                 # CLI 入口 (75 行)
│   ├── workflow.py            # 工作流 (120 行)
│   └── tests/
│       ├── pytest.ini
│       ├── conftest.py
│       ├── test_router.py
│       ├── test_types.py
│       ├── test_config.py
│       └── test_circuit_breaker.py
```

### 分节结构 (sync_pipeline.py)

```python
# =============================================================================
# 1. Environment & Config (环境与配置)
# =============================================================================
# - load_env_manual()
# - 路径定义
# - 日志配置
# - Playwright 导入

# =============================================================================
# 2. Resiliency Helpers (弹性组件 - 包含重试与安全操作)
# =============================================================================
# - async_retry 装饰器
# - safe_click()
# - safe_fill()

# =============================================================================
# 3. Pipeline Stages (流水线阶段定义)
# =============================================================================
# - PipelineStage 枚举
# - PipelineState dataclass

# =============================================================================
# 4. Functional Components (功能组件)
# =============================================================================
# - YupooLogin
# - YupooExtractor
# - MrShopLogin
# - ImageUploader
# - Verifier
# - DescriptionEditor

# =============================================================================
# 5. Orchestrator (编排器)
# =============================================================================
# - SyncPipeline 类

if __name__ == "__main__":
    # CLI 入口
```

---

## 最佳实践观察 (Observed Best Practices)

### 1. 状态持久化

```python
@dataclass
class PipelineState:
    album_id: str
    current_step: int = 1
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
```

### 2. Cookie 持久化

```python
async def login(self, context: BrowserContext) -> bool:
    if self.cookies_file.exists():
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                await context.add_cookies(json.load(f))
            return True
        except: pass
    
    # 正常登录流程
    cookies = await context.cookies()
    with open(self.cookies_file, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
```

### 3. 环境变量读取

```python
def load_env_manual(env_path=".env"):
    """Manually parse .env file (手动解析 .env 文件)"""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# 使用带默认值的.getenv
self.username = os.getenv("YUPOO_USERNAME", "lol2024")
```

### 4. 安全操作带超时

```python
await page.wait_for_selector(selector, state="visible", timeout=timeout)
await page.click(selector, timeout=timeout, force=force)
```

---

## 缺失配置 (Missing Configuration)

| 配置项 | 状态 |
|--------|------|
| pyproject.toml | 未检测到 |
| setup.cfg | 未检测到 |
| ruff.toml | 未检测到 |
| .prettierrc | 未检测到 |
| ESLint 配置 | 不适用 (Python 项目) |
| pre-commit hooks | 未检测到 |
| mypy/pyright 配置 | 未检测到 |

---

*Convention analysis: 2026-04-07*
