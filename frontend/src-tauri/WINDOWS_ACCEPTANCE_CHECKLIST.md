# Akasha Forge — Windows Native Acceptance Checklist (AF-DESKTOP-008)

Run on a **Windows 10/11 x64** machine after `scripts/build_windows.ps1`. This
verifies the packaged desktop app + NSIS installer. Items marked **(Emergent-verified)**
were already validated in the Linux dev environment via the harnesses; re-confirm
them natively.

## Build & sidecar
1. [ ] PyInstaller backend build succeeds (`scripts/build_windows.ps1`).
2. [ ] `backend\dist\AkashaForgeBackend\AkashaForgeBackend.exe` exists.
3. [ ] Complete `_internal\` directory is present (one-dir, NOT one-file).
4. [ ] Frozen backend starts without system Python (run the exe directly). *(Emergent-verified on Linux binary)*
5. [ ] Tauri Rust build succeeds (`cargo`/`tauri build`).

## App launch & lifecycle
6. [ ] `Akasha Forge.exe` launches (from `src-tauri\target\release\`).
7. [ ] No external browser window opens (renders in WebView2).
8. [ ] Backend sidecar starts automatically. *(lifecycle harness PASS on Linux)*
9. [ ] Backend binds only to `127.0.0.1`. *(harness PASS)*
10. [ ] Dynamic backend port is used (not fixed 8001). *(harness PASS)*
11. [ ] `GET /api/health` returns `{"status":"ok"}`. *(harness PASS)*
12. [ ] React UI loads (Akasha Core dashboard).
13. [ ] Existing Forge routes/modules open (HashRouter deep links work).

## Local data (under AppData, never Program Files)
14. [ ] Local database initializes under `%APPDATA%\com.akashaforge.desktop\...\database\`. *(harness PASS)*
15. [ ] Local storage initializes under the same app-data root. *(harness PASS)*

## Secrets (AF-DESKTOP-007 — Windows production path)
16. [ ] Windows **Credential Manager** contains an Akasha master-key entry (service `com.akashaforge.desktop`, key `akasha_master_key`). *(Windows-only — Linux used the dev file fallback)*
17. [ ] No plaintext `.akasha_secret` exists under the app-data dir.
18. [ ] Same master key survives a restart (Credential Manager entry unchanged).
19. [ ] Runtime config (`window.__AKASHA_RUNTIME_CONFIG__`) contains NO secrets. *(harness PASS: `6b`)*
20. [ ] No raw master key appears in `logs\backend.log`. *(Emergent-verified: 0 occurrences)*

## Data & providers
21. [ ] Create a project. *(harness PASS)*
22. [ ] Create representative project data (character/bible). *(harness PASS)*
23. [ ] Add a Provider Hub API key → response shows only a masked key.
24. [ ] Close Akasha Forge → backend process terminates. *(harness PASS)*
25. [ ] No orphan `AkashaForgeBackend.exe` remains. *(harness PASS)*
26. [ ] Relaunch → project data survives. *(harness PASS)*
27. [ ] Provider encrypted credentials still decrypt after restart. *(harness PASS via persisted vault key)*
28. [ ] Project deletion cascade works. *(harness PASS)*

## Installer (NSIS)
29. [ ] NSIS installer (`*-setup.exe`) installs successfully.
30. [ ] Start Menu entry launches the application.
31. [ ] Uninstaller works and removes the install directory.
32. [ ] Uninstall does NOT delete user project data (app-data dir preserved).
33. [ ] Reinstall / update can access preserved user data.
34. [ ] WebView2: installs silently if missing (online bootstrapper); no-op if already present.
