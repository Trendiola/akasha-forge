# Akasha Forge — Desktop Backend Freeze (AF-DESKTOP-005)

Freeze the FastAPI backend into a **standalone, one-dir** sidecar so the desktop
user needs **no Python, no pip, no MongoDB, and no terminal**. All mutable data
lives under `AKASHA_DATA_DIR` — the executable directory stays read-only-friendly.

> **PyInstaller does not cross-compile.** A Windows `AkashaForgeBackend.exe` must
> be built **on Windows**. Building on Linux/macOS produces a native binary for
> that OS (used here to validate the freeze pipeline).

---

## Windows build (produces `AkashaForgeBackend.exe`)

### 1. Prerequisites
- **Windows 10/11 (64-bit)**
- **Python 3.11.x** (matches the dev/runtime target — https://www.python.org/downloads/)
  - During install, tick **"Add python.exe to PATH"**.

### 2. Get the backend source
```powershell
cd C:\path\to\akasha-forge\backend
```

### 3. Create a clean virtual environment
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 4. Install dependencies
```powershell
# App dependencies
pip install -r requirements.txt

# emergentintegrations (custom index — optional Akasha Brain LLM features)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# PyInstaller
pip install pyinstaller
```

### 5. Build (one-dir)
```powershell
pyinstaller build.spec --noconfirm --clean
```

### 6. Expected output
```
backend\dist\AkashaForgeBackend\
    AkashaForgeBackend.exe        <-- the sidecar entry point
    _internal\                    <-- bundled Python runtime + all dependencies
```
The whole `AkashaForgeBackend\` folder is the deliverable — ship it intact
(the future Tauri shell in AF-DESKTOP-006 will launch `AkashaForgeBackend.exe`).

---

## Linux / macOS build (validation build used in this repo)
Identical, minus the platform:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
pip install pyinstaller
pyinstaller build.spec --noconfirm --clean
# -> backend/dist/AkashaForgeBackend/AkashaForgeBackend
```

---

## Runtime configuration (environment variables)
The frozen backend is configured **entirely via environment variables** — no
`.env` beside the executable is required (the launcher/Tauri shell sets these):

| Variable            | Purpose                                        | Desktop value (example)          |
|---------------------|------------------------------------------------|----------------------------------|
| `AKASHA_DB_BACKEND` | `local` = MontyDB (offline) · `remote` = Mongo | `local`                          |
| `STORAGE_BACKEND`   | `local` = filesystem · `remote` = Emergent     | `local`                          |
| `AKASHA_DATA_DIR`   | Root for all mutable data (see below)          | `%LOCALAPPDATA%\AkashaForge`     |
| `AKASHA_HOST`       | Bind host                                      | `127.0.0.1`                      |
| `AKASHA_PORT`       | Bind port                                      | `8001` (or any free port)        |
| `DB_NAME`           | Local database name                            | `akasha_forge`                   |
| `AKASHA_SECRET_KEY` | Fernet key for provider-key encryption         | *(per-install; AF-DESKTOP-007)*  |

`AKASHA_SECRET_KEY` must be a valid 32-byte url-safe base64 Fernet key. A secure
per-install keyring/DPAPI source is scoped for **AF-DESKTOP-007** (not this sprint).

### Data layout under `AKASHA_DATA_DIR`
```
<AKASHA_DATA_DIR>/
  database/   MontyDB (SQLite) files
  storage/    uploaded/generated files (images, videos, audio, ...)
  projects/
  cache/
  logs/       backend.log (startup diagnostics)
```
Nothing mutable is written next to the executable.

---

## Smoke-run the frozen backend (Windows)
```powershell
$env:AKASHA_DB_BACKEND="local"; $env:STORAGE_BACKEND="local"
$env:AKASHA_DATA_DIR="$env:LOCALAPPDATA\AkashaForge"
$env:AKASHA_HOST="127.0.0.1"; $env:AKASHA_PORT="8001"
$env:DB_NAME="akasha_forge"
$env:AKASHA_SECRET_KEY="<your-fernet-key>"
.\dist\AkashaForgeBackend\AkashaForgeBackend.exe
# then in a browser / another shell:
#   http://127.0.0.1:8001/api/health  ->  {"status":"ok",...}
```

---

## Notes
- **Why one-dir, not one-file:** this dependency graph (`pydantic_core`,
  `cryptography`, `uvicorn` protocol/loop plugins, `montydb`) is more reliable
  un-archived and avoids one-file's temp-extraction startup cost.
- **Excluded (confirmed unused at runtime):** `pandas`, `numpy`, `boto3`,
  `matplotlib`, dev/test tooling — trimmed for a leaner, more reliable freeze.
- **`emergentintegrations` / `litellm`** are bundled best-effort for the optional
  Akasha Brain LLM features; the backend boots and serves fully without them.
