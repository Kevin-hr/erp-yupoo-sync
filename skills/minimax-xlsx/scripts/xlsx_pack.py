import argparse
import os
import zipfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work_dir", type=str)
    ap.add_argument("output", type=str)
    args = ap.parse_args()

    work_dir = Path(args.work_dir)
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    if outp.exists():
        outp.unlink()

    with zipfile.ZipFile(outp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(work_dir):
            for fn in files:
                p = Path(root) / fn
                rel = p.relative_to(work_dir)
                z.write(p, str(rel).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
