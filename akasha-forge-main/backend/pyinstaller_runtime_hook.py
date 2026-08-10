"""AF-DESKTOP-005 — PyInstaller runtime hook (executes before the frozen app).

Keeps startup diagnosable in desktop/local mode without redesigning logging:
console output is preserved, and a rotating-free file target is added under
<AKASHA_DATA_DIR>/logs/backend.log so a packaged backend that fails to boot
leaves a trace the Tauri shell (or user) can inspect. Best-effort: never blocks
startup if the path is not writable.
"""
import logging
import os
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

_data_dir = os.environ.get("AKASHA_DATA_DIR")
if _data_dir:
    try:
        _logs = Path(_data_dir) / "logs"
        _logs.mkdir(parents=True, exist_ok=True)
        _fh = logging.FileHandler(str(_logs / "backend.log"), encoding="utf-8")
        _fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        _root = logging.getLogger()
        _root.addHandler(_fh)
        if _root.level > logging.INFO or _root.level == logging.NOTSET:
            _root.setLevel(logging.INFO)
    except Exception:
        # Diagnostics are best-effort; console logging still applies.
        pass
