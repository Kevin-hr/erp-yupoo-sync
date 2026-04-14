import PyInstaller.__main__
import os
import shutil
from pathlib import Path

# =============================================================================
:: Build Script for standalone .exe (生成独立可执行文件脚本)
:: Uses PyInstaller to bundle sync_pipeline.py
# =============================================================================

ROOT_DIR = Path(__file__).parent.parent
SCRIPT_PATH = ROOT_DIR / "scripts" / "sync_pipeline.py"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"

def build():
    print(f"[INFO] Building standalone executable for {SCRIPT_PATH}...")
    
    # Run PyInstaller
    # --onefile: bundle everything into a single .exe
    # --name: output filename
    # --add-data: include .env (as template) and folders
    # --hidden-import: ensure playwright and requests are captured
    PyInstaller.__main__.run([
        str(SCRIPT_PATH),
        '--onefile',
        '--name=YupooSyncIndustrial',
        f'--add-data=.env{os.pathsep}.',
        f'--add-data=logs{os.pathsep}logs',
        f'--add-data=screenshots{os.pathsep}screenshots',
        '--clean',
        '--noconfirm'
    ])

    print("[SUCCESS] Build complete! Check the 'dist' folder for YupooSyncIndustrial.exe")
    print("[注意] 运行 .exe 前由于 Playwright 限制，仍需在目标机器安装浏览器环境（或手动拷贝浏览器库）。")

if __name__ == "__main__":
    build()
