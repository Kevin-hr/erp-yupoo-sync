import os
from pathlib import Path

import PyInstaller.__main__


def build() -> None:
    root = Path(__file__).resolve().parent.parent
    script_path = root / "scripts" / "gucci_to_erp.py"
    templates_dir = root / "templates"

    PyInstaller.__main__.run(
        [
            str(script_path),
            "--onefile",
            "--name=GucciToErp",
            f"--add-data={templates_dir}{os.pathsep}templates",
            "--clean",
            "--noconfirm",
        ]
    )


if __name__ == "__main__":
    build()
