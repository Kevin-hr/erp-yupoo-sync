import argparse
import shutil
import zipfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=str)
    ap.add_argument("out_dir", type=str)
    args = ap.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(inp, "r") as z:
        z.extractall(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
