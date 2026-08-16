# -*- mode: python ; coding: utf-8 -*-
"""AF-DESKTOP-005 — Reproducible PyInstaller build for the Akasha Forge backend.

The Windows build deliberately keeps the desktop DB stack (MontyDB/PyMongo/
Motor) in a private `_vendor` directory beside the frozen executable. The
runtime hook adds that directory to sys.path before application imports. This
avoids PyInstaller trying to discover packages installed only in the vendor
tree and makes the packaged backend deterministic.
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

datas = []
binaries = []
hiddenimports = []


def _add(pkg, metadata=False):
    """Best-effort collect a package installed in the PyInstaller venv."""
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
        if metadata:
            datas.extend(copy_metadata(pkg))
        print(f"[build.spec] collected: {pkg}")
    except Exception as exc:  # noqa: BLE001
        print(f"[build.spec] WARN could not collect {pkg}: {exc}")


# --- Core runtime ---
# DB drivers are intentionally NOT collected here. build_windows.ps1 creates
# backend/_vendor_runtime and later copies it beside AkashaForgeBackend.exe as
# `_vendor`; pyinstaller_runtime_hook.py prepends that directory to sys.path.
for _pkg in (
    "fastapi",
    "starlette",
    "uvicorn",
    "anyio",
    "sniffio",
    "h11",
    "pydantic",
    "pydantic_core",
    "email_validator",
    # Distribution is named python-multipart, but its import package is
    # `multipart`. FastAPI verifies the distribution metadata at route startup,
    # so both package code and dist-info metadata must be frozen.
    "multipart",
    "cryptography",
    "dotenv",
    "requests",
    "certifi",
    "urllib3",
    "charset_normalizer",
    "idna",
    "imageio_ffmpeg",
):
    _add(_pkg)

# FastAPI's ensure_multipart_is_installed() uses importlib.metadata against the
# distribution name `python-multipart`; collect_all("multipart") alone does not
# guarantee that metadata is present in the frozen application.
try:
    datas += copy_metadata("python-multipart")
    print("[build.spec] collected metadata: python-multipart")
except Exception as exc:  # noqa: BLE001
    raise RuntimeError(f"python-multipart metadata is required by FastAPI: {exc}")
hiddenimports += collect_submodules("multipart")

# uvicorn loads its protocol/loop implementations dynamically.
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("anyio")
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

# --- Application modules ---
hiddenimports += collect_submodules("routes")
hiddenimports += collect_submodules("services")
hiddenimports += ["core", "mongo_compat", "video_adapters", "secret_vault", "services.video_execution"]

# --- Optional LLM stack ---
for _pkg in ("emergentintegrations", "litellm"):
    _add(_pkg, metadata=True)

# --- Secret vault ---
for _pkg in ("keyring", "jaraco"):
    _add(_pkg, metadata=True)
hiddenimports += collect_submodules("keyring")
hiddenimports += [
    "keyring.backends",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.macOS",
    "keyring.backends.fail",
    "keyring.backends.chainer",
]
try:
    datas += copy_metadata("importlib_metadata")
except Exception:
    pass

a = Analysis(
    ["server.py"],
    pathex=[SPEC_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_runtime_hook.py"],
    excludes=[
        "pandas", "numpy", "boto3", "botocore", "matplotlib", "scipy",
        "PIL", "tkinter", "pytest", "_pytest", "black", "mypy", "flake8",
        "isort", "IPython", "notebook",
        # These are supplied by the external `_vendor` runtime tree.
        "montydb", "pymongo", "bson", "motor", "dns",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AkashaForgeBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AkashaForgeBackend",
)
