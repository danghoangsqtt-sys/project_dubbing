from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")
for source_root in (REPO_ROOT / "app", REPO_ROOT / "ui" / "views"):
    value = str(source_root)
    if value in sys.path:
        sys.path.remove(value)
    sys.path.insert(0, value)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from launcher import LauncherWindow  # noqa: E402


def render(output: Path, wait_ms: int = 1400) -> None:
    app = QApplication.instance() or QApplication([])
    window = LauncherWindow()
    window.resize(1440, 900)
    window.show()

    def capture() -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(output), "PNG"):
            raise RuntimeError(f"Could not save launcher screenshot: {output}")
        window.close()
        app.quit()

    QTimer.singleShot(max(100, wait_ms), capture)
    app.exec()
    if not output.is_file() or output.stat().st_size <= 0:
        raise RuntimeError(f"Launcher screenshot is missing or empty: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the production Launcher for visual QA.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wait-ms", type=int, default=1400)
    args = parser.parse_args()
    render(args.output.resolve(), args.wait_ms)
    print(f"Launcher screenshot: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
