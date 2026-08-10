<#
.SYNOPSIS
    AF-DESKTOP-008 — reproducible Windows release build for Akasha Forge.

.DESCRIPTION
    Developer/build-runner script (NOT for end users). Runs the existing,
    already-implemented pipeline end to end on a Windows x64 machine:

        React production build
        -> PyInstaller one-dir backend (backend/build.spec)  => AkashaForgeBackend.exe + _internal/
        -> stage the COMPLETE one-dir output into the Tauri resources
        -> Tauri 2 build  => "Akasha Forge.exe"
        -> NSIS installer  => *-setup.exe

    Fails fast. Does not sign, publish, or deploy. Does not touch AKASHA_DATA_DIR.

.NOTES
    Prerequisites (see frontend/src-tauri/BUILD_DESKTOP_TAURI.md):
      Node 20 + Yarn, Python 3.11, Rust (MSVC) + C++ Build Tools, WebView2 runtime.
#>

[CmdletBinding()]
param(
    [switch]$SkipBackend,   # reuse an existing backend/dist build
    [switch]$NoInstaller    # build the app only (tauri build --no-bundle)
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# --- Resolve repo paths relative to this script (repo/scripts/build_windows.ps1) ---
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendDir  = Join-Path $RepoRoot "backend"
$TauriDir    = Join-Path $FrontendDir "src-tauri"
$FrozenDir   = Join-Path $BackendDir "dist\AkashaForgeBackend"
$StageDir    = Join-Path $TauriDir "resources\backend\AkashaForgeBackend"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Assert-Exists($path, $what) {
    if (-not (Test-Path $path)) { throw "Missing $what : $path" }
}

# --- 1. Validate required build tools ---
Step "1/10 Validate build tools"
foreach ($tool in @("node", "yarn", "python", "cargo", "rustc")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required tool '$tool' not found on PATH. See BUILD_DESKTOP_TAURI.md."
    }
}
Write-Host ("node   : " + (node --version))
Write-Host ("yarn   : " + (yarn --version))
Write-Host ("python : " + (python --version))
Write-Host ("cargo  : " + (cargo --version))

# --- 2. Frontend dependencies ---
Step "2/10 Install frontend dependencies"
Push-Location $FrontendDir
yarn install --frozen-lockfile
Pop-Location

# --- 3. React production build (also runs via tauri beforeBuildCommand; explicit for clarity) ---
Step "3/10 Build React frontend"
Push-Location $FrontendDir
yarn build
Assert-Exists (Join-Path $FrontendDir "build\index.html") "React build output"
Pop-Location

if (-not $SkipBackend) {
    # --- 4. Backend dependencies (isolated venv) ---
    Step "4/10 Install backend dependencies"
    Push-Location $BackendDir
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\pip.exe install -r requirements.txt
    & .\.venv\Scripts\pip.exe install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
    & .\.venv\Scripts\pip.exe install pyinstaller

    # --- 5. Freeze backend with the EXISTING build.spec (one-dir) ---
    Step "5/10 Build frozen backend (PyInstaller one-dir)"
    if (Test-Path (Join-Path $BackendDir "build")) { Remove-Item -Recurse -Force (Join-Path $BackendDir "build") }
    if (Test-Path (Join-Path $BackendDir "dist"))  { Remove-Item -Recurse -Force (Join-Path $BackendDir "dist") }
    & .\.venv\Scripts\pyinstaller.exe build.spec --noconfirm --clean
    Pop-Location
} else {
    Step "4-5/10 Skipping backend build (-SkipBackend)"
}

# --- 6/7. Verify the COMPLETE one-dir output (exe + _internal) ---
Step "6/10 Verify frozen backend output"
Assert-Exists (Join-Path $FrozenDir "AkashaForgeBackend.exe") "AkashaForgeBackend.exe"
Assert-Exists (Join-Path $FrozenDir "_internal") "_internal directory (one-dir dependencies)"

# --- 8. Stage the COMPLETE one-dir output into Tauri resources ---
Step "8/10 Stage backend one-dir into Tauri resources"
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StageDir) | Out-Null
Copy-Item -Recurse -Force $FrozenDir $StageDir
Assert-Exists (Join-Path $StageDir "AkashaForgeBackend.exe") "staged AkashaForgeBackend.exe"
Assert-Exists (Join-Path $StageDir "_internal") "staged _internal directory"

# --- 9/10. Build the Tauri app + NSIS installer ---
Step "9/10 Build Tauri desktop app (+ NSIS installer)"
Push-Location $FrontendDir
if ($NoInstaller) {
    yarn tauri build --no-bundle
} else {
    yarn tauri build
}
Pop-Location

# --- Final artifact locations ---
Step "10/10 Done — expected artifacts"
$ReleaseDir = Join-Path $TauriDir "target\release"
Write-Host ("App executable : " + (Join-Path $ReleaseDir "Akasha Forge.exe"))
Write-Host ("NSIS installer : " + (Join-Path $ReleaseDir "bundle\nsis\*-setup.exe"))
Write-Host ("Backend sidecar staged at : $StageDir (bundled as a Tauri resource)")
Write-Host "`nBuild complete." -ForegroundColor Green
