"""AF-DESKTOP-005 — PyInstaller runtime hook (executes before the frozen app).

Keeps startup diagnosable in desktop/local mode and makes the Windows bundle
robust against PyInstaller missing lazily-imported database packages.
"""
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

# The Windows build deliberately stages a private `_vendor` directory beside
# AkashaForgeBackend.exe containing the desktop DB stack (montydb/pymongo/motor
# and their transitive Python dependencies). Put it first on sys.path before any
# application import occurs. This is intentionally independent of PyInstaller's
# hidden-import analysis, which has proven unreliable for these lazy imports.
try:
    _exe_dir = Path(sys.executable).resolve().parent
    _vendor = _exe_dir / "_vendor"
    if _vendor.is_dir():
        sys.path.insert(0, str(_vendor))
except Exception:
    pass

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
