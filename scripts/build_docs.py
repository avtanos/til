#!/usr/bin/env python3
"""Build static site for GitHub Pages (docs/)."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FRONTEND = ROOT / "frontend"


def main():
    DOCS.mkdir(exist_ok=True)

    # Copy frontend
    for f in FRONTEND.iterdir():
        if f.name.startswith("."):
            continue
        dst = DOCS / f.name
        if f.is_dir():
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(f, dst)
        else:
            shutil.copy2(f, dst)

    # Export tasks.json
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.tasks_data import TASKS
    (DOCS / "tasks.json").write_text(
        json.dumps(TASKS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # .nojekyll (GitHub Pages: don't process with Jekyll)
    (DOCS / ".nojekyll").touch()

    print("Built docs/ for GitHub Pages.")


if __name__ == "__main__":
    main()
