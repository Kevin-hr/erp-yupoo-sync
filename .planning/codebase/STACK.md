# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.14.3 - Main scripting language for pipeline automation

## Runtime

**Environment:**
- Python 3.14.3 (Windows environment)
- Virtual environment: `.venv/` (local project venv)

**Package Manager:**
- pip 26.0.1 (bundled with Python)
- Lockfile: Not applicable (no requirements.txt)

## Frameworks

**Core:**
- **Playwright 1.58.0** - Browser automation framework
  - Module: `playwright.async_api`
  - Purpose: Headless browser control for Yupoo/MrShopPlus automation
  - Location: `scripts/sync_pipeline.py` lines 70

**Testing:**
- Not detected (no test framework configured)

**Build/Dev:**
- Not applicable (pure Python project)

## Key Dependencies

**Critical:**
- `playwright` 1.58.0 - Browser automation
  -驱动 Chromium/ Firefox/WebKit 浏览器
  - 异步 API: `async_playwright`, `Page`, `BrowserContext`, `Browser`
  - 文件: `scripts/sync_pipeline.py` line 70

**Internal Modules (Standard Library):**
| Module | Purpose | Usage Location |
|--------|---------|----------------|
| `asyncio` | 异步编程 | 整个 pipeline 的异步编排 |
| `json` | JSON 序列化 | Cookie 持久化、状态管理 |
| `logging` | 日志记录 | `scripts/sync_pipeline.py` lines 58-68 |
| `os` | 环境变量读取 | `scripts/sync_pipeline.py` line 36-47 |
| `sys` | 系统输出 | logging StreamHandler |
| `time` | 时间操作 | 休眠延迟 |
| `dataclasses` | 数据结构 | `PipelineState` 状态类 line 127-139 |
| `datetime` | 时间戳 | 日志文件名、截图命名 |
| `enum` | 枚举类型 | `PipelineStage` 枚举 line 118-125 |
| `pathlib` | 路径管理 | `ROOT_DIR`, `LOG_DIR`, `SCREENSHOT_DIR` |
| `typing` | 类型注解 | 函数参数和返回值类型提示 |

**Transitive Dependencies (via playwright):**
- `pyee` - 事件发射
- `greenlet` - 协程
- `urllib3` - HTTP 客户端
- `idna` - Unicode 支持

## Configuration

**Environment:**
- `.env` file with manual parser (lines 36-47)
- 优先级: `.env` > 环境变量 > 脚本硬编码默认值
- 凭证字段: `YUPOO_USERNAME`, `YUPOO_PASSWORD`, `ERP_USERNAME`, `ERP_PASSWORD`

**Key Configs:**
```python
# .env.example
YUPOO_USERNAME=lol2024
YUPOO_PASSWORD=9longt#3
YUPOO_BASE_URL=https://lol2024.x.yupoo.com/albums
ERP_USERNAME=zhiqiang
ERP_PASSWORD=123qazwsx
ERP_BASE_URL=https://www.mrshopplus.com
MAX_CONCURRENT_WORKERS=3
SAVE_SCREENSHOTS=True
DRY_RUN=False
```

**Logging Config (scripts/sync_pipeline.py lines 58-68):**
```python
LOG_FILE = LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
```

## Platform Requirements

**Development:**
- Python 3.14.3+
- Playwright (pip install playwright; python -m playwright install chromium)

**Production:**
- Windows 10 Pro 10.0.19045
- Chromium browser (via Playwright)
- Network access to Yupoo and MrShopPlus

## Architecture Patterns

**Pipeline Orchestration:**
- 6-stage sequential pipeline with state persistence
- Async/await pattern for browser operations
- Decorator-based retry with exponential backoff

**Key Classes:**
| Class | File | Lines | Purpose |
|-------|------|-------|---------|
| `SyncPipeline` | sync_pipeline.py | 391-438 | 主编排器 |
| `PipelineState` | sync_pipeline.py | 127-139 | 状态持久化 |
| `PipelineStage` | sync_pipeline.py | 118-125 | 阶段枚举 |
| `YupooLogin` | sync_pipeline.py | 145-178 | Yupoo 认证 |
| `YupooExtractor` | sync_pipeline.py | 181-242 | 图片 URL 提取 |
| `MrShopLogin` | sync_pipeline.py | 246-277 | ERP 认证 |
| `ImageUploader` | sync_pipeline.py | 280-300 | 图片上传 |
| `Verifier` | sync_pipeline.py | 302-317 | 截图验证 |
| `DescriptionEditor` | sync_pipeline.py | 319-384 | 描述格式化 |

---

*Stack analysis: 2026-04-07*
