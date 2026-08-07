# -*- mode: python ; coding: utf-8 -*-
"""AF-DESKTOP-005 — Reproducible PyInstaller build for the Akasha Forge backend.

One-dir freeze of the FastAPI backend into a standalone sidecar. Produces:
  dist/AkashaForgeBackend/AkashaForgeBackend      (Linux/macOS)
  dist/AkashaForgeBackend/AkashaForgeBackend.exe  (Windows)

Windows-ready: run `pyinstaller build.spec` from a Windows shell (see
BUILD_DESKTOP.md) to emit AkashaForgeBackend.exe. PyInstaller does NOT
cross-compile, so the target .exe must be built on Windows.

One-dir (not one-file) is chosen deliberately: this dependency graph
(pydantic_core, cryptography, uvicorn protocol/loop plugins, montydb) is far
more reliable un-archived, avoids the one-file temp-extraction startup cost,
and keeps the executable directory read-only-friendly (all mutable data lives
under AKASHA_DATA_DIR, never beside the binary).
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

datas = []
binaries = []
hiddenimports = []


def _add(pkg, metadata=False):
    """Best-effort collect a package's submodules, data and binaries."""
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


# --- Core runtime (must be present for the backend to run) ---
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
    "multipart",          # python-multipart (form/file uploads)
    "cryptography",       # Fernet encryption for provider keys
    "montydb",            # local SQLite-backed DB (desktop offline mode)
    "pymongo",
    "bson",
    "motor",              # remote MongoDB mode (dev/preview parity)
    "dotenv",
    "requests",
    "certifi",
    "urllib3",
    "charset_normalizer",
    "idna",
):
    _add(_pkg)

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

# --- Application modules (routes are imported dynamically via `from routes import ...`) ---
hiddenimports += collect_submodules("routes")
hiddenimports += collect_submodules("services")
hiddenimports += ["core", "mongo_compat", "video_adapters", "secret_vault", "services.video_execution"]

# --- Optional LLM stack (Akasha Brain optimise/assist — lazily imported) ---
# Included for a complete desktop build; not required by the smoke tests. Wrapped
# best-effort so a heavy/edge litellm dependency never hard-fails the freeze.
for _pkg in ("emergentintegrations", "litellm"):
    _add(_pkg, metadata=True)

# --- Secret vault (AF-DESKTOP-007) ---
# keyring + its OS backends load dynamically; bundle them so the frozen backend
# can reach Windows Credential Manager (DPAPI) at runtime. Non-Windows backends
# are harmless extras. copy_metadata is required for keyring's entry-point
# backend discovery.
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
        # Confirmed unused at runtime — trimmed for a leaner, more reliable freeze.
        "pandas",
        "numpy",
        "boto3",
        "botocore",
        "matplotlib",
        "scipy",
        "PIL",
        "tkinter",
        "pytest",
        "_pytest",
        "black",
        "mypy",
        "flake8",
        "isort",
        "IPython",
        "notebook",
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
