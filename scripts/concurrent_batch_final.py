#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP极限并发批量同步 - FINAL v3 (Subprocess Worker Architecture)
每个Worker通过subprocess调用已验证通过的sync_pipeline.py，实现真并发。

架构：
    asyncio.gather -> N个 subprocess workers 同时跑 sync_pipeline.py
    每个worker = 独立进程 = 独立Chromium = 完全隔离

用法:
    python scripts/concurrent_batch_final.py --batch batch_example.json --workers 3
    python scripts/concurrent_batch_final.py --batch batch_example.json --workers 10  # 极限并发
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# =============================================================================
# Environment
# =============================================================================

def load_env(env_path=".env"):
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

load_env()

ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
SCRIPT_DIR = ROOT_DIR / "scripts"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"concurrent_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('concurrent_v3')

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ProductTask:
    album_id: str
    brand_name: str
    product_name: str
    status: str = "pending"
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None

@dataclass
class BatchResult:
    total: int = 0
    success: int = 0
    failed: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    results: List = field(default_factory=list)

# =============================================================================
# Subprocess Worker
# =============================================================================

async def worker_subprocess(task: ProductTask, semaphore: asyncio.Semaphore) -> ProductTask:
    """
    每个worker作为独立subprocess运行sync_pipeline.py。
    subprocess = 独立进程 = 独立Chromium = 完全隔离。
    """
    async with semaphore:
        task.status = "running"
        task.start_time = time.time()

        album_short = task.album_id[-6:]
        logger.info(f"[{album_short}] Worker starting: {task.brand_name} {task.product_name}")

        # 构建sync_pipeline.py命令
        # 使用--use-cdp连接已有Chrome（Chrome需已启动并登录）
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "sync_pipeline.py"),
            "--album-id", task.album_id,
            "--brand-name", task.brand_name,
            "--product-name", task.product_name,
            "--use-cdp",
        ]

        try:
            # 运行subprocess（同步阻塞，在asyncio中用run_in_executor避免阻塞event loop）
            loop = asyncio.get_event_loop()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(ROOT_DIR)
            )

            stdout, _ = await proc.communicate()
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""

            # 检查退出码
            if proc.returncode == 0:
                task.status = "success"
                logger.info(f"[{album_short}] [OK] Done in {task.duration:.1f}s")
            else:
                task.status = "failed"
                task.error = f"exit_code={proc.returncode}"
                # 保存错误日志
                err_file = LOG_DIR / f"worker_error_{album_short}_{datetime.now().strftime('%H%M%S')}.log"
                with open(err_file, "w", encoding="utf-8") as f:
                    f.write(stdout_text)
                logger.error(f"[{album_short}] [FAIL] exit={proc.returncode}, log={err_file}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"[{album_short}] [FAIL] {e}")

        task.end_time = time.time()
        task.duration = round(task.end_time - task.start_time, 1)
        return task

# =============================================================================
# Batch Orchestrator
# =============================================================================

async def run_batch(tasks: List[ProductTask], max_workers: int = 3) -> BatchResult:
    """用asyncio.gather + subprocess实现真并发。"""
    result = BatchResult(total=len(tasks), start_time=time.time())
    semaphore = asyncio.Semaphore(max_workers)

    logger.info(f"[BATCH] Starting: {len(tasks)} products x {max_workers} concurrent workers")
    logger.info(f"[BATCH] Using subprocess workers -> each = independent Chromium process")
    logger.info(f"[BATCH] Chrome must be running with: chrome.exe --remote-debugging-port=9222")

    # 检查Chrome是否运行
    try:
        import requests
        r = requests.get("http://localhost:9222/json/version", timeout=3)
        if r.status_code == 200:
            logger.info(f"[BATCH] Chrome CDP detected: {r.json().get('Browser', 'OK')}")
        else:
            logger.warning(f"[BATCH] Chrome CDP returned: {r.status_code}")
    except Exception:
        logger.warning(f"[BATCH] Chrome CDP not responding on port 9222 - login may fail")
        logger.warning(f"[BATCH] Start Chrome first: chrome.exe --remote-debugging-port=9222")

    # 并发启动所有worker！
    completed = await asyncio.gather(
        *[worker_subprocess(task, semaphore) for task in tasks],
        return_exceptions=True
    )

    for item in completed:
        if isinstance(item, ProductTask):
            result.results.append({
                "album_id": item.album_id,
                "brand": f"{item.brand_name} {item.product_name}",
                "status": item.status,
                "duration": item.duration,
                "error": item.error
            })
            if item.status == "success":
                result.success += 1
            else:
                result.failed += 1
        else:
            # Exception returned
            result.failed += 1
            result.results.append({"album_id": "unknown", "status": "failed", "error": str(item)})

    result.end_time = time.time()

    # 保存结果
    result_path = LOG_DIR / f"batch_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)

    total_time = result.end_time - result.start_time
    rate = result.success / (total_time / 3600) if total_time > 0 else 0

    logger.info("=" * 60)
    logger.info(f"[BATCH] Done! Total={result.total}, Success={result.success}, Failed={result.failed}")
    logger.info(f"[BATCH] Wall time: {total_time:.1f}s")
    logger.info(f"[BATCH] Avg per product: {total_time / max(result.total, 1):.1f}s")
    logger.info(f"[BATCH] Throughput: ~{rate:.0f} products/hour @ {max_workers} workers")
    logger.info(f"[BATCH] Result: {result_path}")
    logger.info("=" * 60)

    return result

def load_batch(json_path: str) -> List[ProductTask]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    tasks = []
    for item in data:
        t = ProductTask(
            album_id=str(item["album_id"]),
            brand_name=item.get("brand_name", ""),
            product_name=item.get("product_name", "")
        )
        if t.album_id and t.brand_name and t.product_name:
            tasks.append(t)
    logger.info(f"Loaded {len(tasks)} tasks from {json_path}")
    return tasks

# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ERP Concurrent Batch - Subprocess Worker v3")
    parser.add_argument("--batch", required=True, help="Batch JSON file path")
    parser.add_argument("--workers", type=int, default=3, help="Max concurrent workers (default: 3)")
    args = parser.parse_args()

    tasks = load_batch(args.batch)
    if not tasks:
        logger.error("No valid tasks loaded. Exiting.")
        sys.exit(1)

    asyncio.run(run_batch(tasks, args.workers))

if __name__ == "__main__":
    main()
