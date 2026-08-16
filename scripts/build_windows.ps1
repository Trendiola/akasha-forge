<#
.SYNOPSIS
    AF-DESKTOP-008 — reproducible Windows release build for Akasha Forge.

.DESCRIPTION
    Developer/build-runner script (NOT for end users). Runs the release pipeline
    end to end on Windows x64 and refuses to create the installer unless the
    frozen backend actually boots in desktop/local mode.
#>

[CmdletBinding()]
param(
    [switch]$SkipBackend,
    [switch]$NoInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendDir  = Join-Path $RepoRoot "backend"
$TauriDir    = Join-Path $FrontendDir "src-tauri"
$FrozenDir   = Join-Path $BackendDir "dist\AkashaForgeBackend"
$StageDir    = Join-Path $TauriDir "resources\backend\AkashaForgeBackend"
$VendorBuild = Join-Path $BackendDir "_vendor_runtime"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Assert-Exists($path, $what) {
    if (-not (Test-Path $path)) { throw "Missing $what : $path" }
}

Step "1/11 Validate build tools"
foreach ($tool in @("node", "yarn", "python", "cargo", "rustc")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required tool '$tool' not found on PATH. See BUILD_DESKTOP_TAURI.md."
    }
}
Write-Host ("node   : " + (node --version))
Write-Host ("yarn   : " + (yarn --version))
Write-Host ("python : " + (python --version))
Write-Host ("cargo  : " + (cargo --version))

Step "2/11 Install frontend dependencies"
Push-Location $FrontendDir
yarn install --frozen-lockfile
Pop-Location

Step "3/11 Build React frontend"
Push-Location $FrontendDir
yarn build
Assert-Exists (Join-Path $FrontendDir "build\index.html") "React build output"
Pop-Location

if (-not $SkipBackend) {
    Step "4/11 Install backend dependencies"
    Push-Location $BackendDir
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\pip.exe install -r requirements.txt
    & .\.venv\Scripts\pip.exe install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
    & .\.venv\Scripts\pip.exe install pyinstaller

    # Build a deterministic private vendor tree for the DB packages that are
    # imported lazily at runtime. This is copied beside the frozen exe and added
    # to sys.path by pyinstaller_runtime_hook.py before core.py is imported.
    Step "5/11 Prepare vendored desktop DB runtime"
    if (Test-Path $VendorBuild) { Remove-Item -Recurse -Force $VendorBuild }
    New-Item -ItemType Directory -Force -Path $VendorBuild | Out-Null
    & .\.venv\Scripts\python.exe -m pip install --no-compile --target $VendorBuild `
        "montydb==2.5.6" "pymongo==4.6.3" "motor==3.3.1"
    Assert-Exists (Join-Path $VendorBuild "montydb") "vendored montydb package"
    Assert-Exists (Join-Path $VendorBuild "pymongo") "vendored pymongo package"

    Step "6/11 Build frozen backend (PyInstaller one-dir)"
    if (Test-Path (Join-Path $BackendDir "build")) { Remove-Item -Recurse -Force (Join-Path $BackendDir "build") }
    if (Test-Path (Join-Path $BackendDir "dist"))  { Remove-Item -Recurse -Force (Join-Path $BackendDir "dist") }
    & .\.venv\Scripts\pyinstaller.exe build.spec --noconfirm --clean
    Pop-Location

    # Copy the private vendor runtime beside the executable. This avoids relying
    # on hidden-import discovery for lazy database imports.
    $FrozenVendor = Join-Path $FrozenDir "_vendor"
    if (Test-Path $FrozenVendor) { Remove-Item -Recurse -Force $FrozenVendor }
    Copy-Item -Recurse -Force $VendorBuild $FrozenVendor
} else {
    Step "4-6/11 Skipping backend build (-SkipBackend)"
}

Step "7/11 Verify frozen backend output"
$FrozenExe = Join-Path $FrozenDir "AkashaForgeBackend.exe"
Assert-Exists $FrozenExe "AkashaForgeBackend.exe"
Assert-Exists (Join-Path $FrozenDir "_internal") "_internal directory"
Assert-Exists (Join-Path $FrozenDir "_vendor\montydb") "vendored montydb runtime"
Assert-Exists (Join-Path $FrozenDir "_vendor\pymongo") "vendored pymongo runtime"

# Critical release gate: start the exact frozen exe in the same local mode the
# Tauri shell uses. The installer is NOT built unless /api/health returns ok.
Step "8/11 Smoke-test frozen backend in desktop/local mode"
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$SmokePort = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$SmokeData = Join-Path $env:TEMP ("akasha-forge-smoke-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $SmokeData | Out-Null
$SmokeOut = Join-Path $SmokeData "stdout.log"
$SmokeErr = Join-Path $SmokeData "stderr.log"

$oldDb = $env:AKASHA_DB_BACKEND
$oldStorage = $env:STORAGE_BACKEND
$oldData = $env:AKASHA_DATA_DIR
$oldName = $env:DB_NAME
$oldHost = $env:AKASHA_HOST
$oldPort = $env:AKASHA_PORT
try {
    $env:AKASHA_DB_BACKEND = "local"
    $env:STORAGE_BACKEND = "local"
    $env:AKASHA_DATA_DIR = $SmokeData
    $env:DB_NAME = "akasha_forge_smoke"
    $env:AKASHA_HOST = "127.0.0.1"
    $env:AKASHA_PORT = $SmokePort.ToString()

    $proc = Start-Process -FilePath $FrozenExe -PassThru -NoNewWindow `
        -RedirectStandardOutput $SmokeOut -RedirectStandardError $SmokeErr

    $healthy = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) { break }
        try {
            $resp = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/health" -f $SmokePort) -TimeoutSec 2
            if ($resp.status -eq "ok") { $healthy = $true; break }
        } catch { }
    }

    if (-not $healthy) {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        Write-Host "--- frozen backend stdout ---"
        if (Test-Path $SmokeOut) { Get-Content $SmokeOut }
        Write-Host "--- frozen backend stderr ---"
        if (Test-Path $SmokeErr) { Get-Content $SmokeErr }
        throw "Frozen Akasha Forge backend failed desktop/local smoke test. Installer build aborted."
    }

    Write-Host "Frozen backend health check PASS" -ForegroundColor Green
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
} finally {
    $env:AKASHA_DB_BACKEND = $oldDb
    $env:STORAGE_BACKEND = $oldStorage
    $env:AKASHA_DATA_DIR = $oldData
    $env:DB_NAME = $oldName
    $env:AKASHA_HOST = $oldHost
    $env:AKASHA_PORT = $oldPort
    Remove-Item -Recurse -Force $SmokeData -ErrorAction SilentlyContinue
}

Step "9/11 Stage backend one-dir into Tauri resources"
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StageDir) | Out-Null
Copy-Item -Recurse -Force $FrozenDir $StageDir
Assert-Exists (Join-Path $StageDir "AkashaForgeBackend.exe") "staged AkashaForgeBackend.exe"
Assert-Exists (Join-Path $StageDir "_internal") "staged _internal directory"
Assert-Exists (Join-Path $StageDir "_vendor\montydb") "staged vendored montydb"

Step "10/11 Build Tauri desktop app (+ NSIS installer)"
Push-Location $FrontendDir
if ($NoInstaller) {
    yarn tauri build --no-bundle
} else {
    yarn tauri build
}
Pop-Location

Step "11/11 Done — expected artifacts"
$ReleaseDir = Join-Path $TauriDir "target\release"
Write-Host ("App executable : " + (Join-Path $ReleaseDir "Akasha Forge.exe"))
Write-Host ("NSIS installer : " + (Join-Path $ReleaseDir "bundle\nsis\*-setup.exe"))
Write-Host ("Backend sidecar staged at : $StageDir")
Write-Host "`nBuild complete." -ForegroundColor Green
