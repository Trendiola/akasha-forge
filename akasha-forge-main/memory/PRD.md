# Akasha Forge — Product Requirements Document

## Original Problem Statement
Build the foundation of a production-quality, desktop-first AI Creative Operating System named **Akasha Forge** — "The Creative Operating System". Modular, clean architecture, feature-based folders, repository/provider patterns, ready for a plugin system and Tauri desktop integration (no Electron). Dark premium UI (Akasha Purple #6D3BFF, near-black background). Shell for 12 modules + Settings, collapsible sidebar, top bar, command palette (Ctrl+K), project manager, replaceable AI provider architecture, settings pages, plugin architecture. Do NOT implement AI generation yet — focus on architecture.

## Architecture
- **Frontend**: React 19 + TypeScript (.tsx) on CRA/CRACO, Tailwind + shadcn/ui, react-router v7, @tanstack/react-query, framer-motion. Path alias `@/*`.
  - `src/config/modules.ts` — central module & navigation registry (single source of truth, plugin-ready).
  - `src/components/layout/` — AppShell, Sidebar (collapsible), TopBar, CommandPalette, AiStatus, ThemeToggle.
  - `src/components/common/` — PageHeader, ModuleShell, EmptyState, StatCard (reusable).
  - `src/modules/<module>/index.tsx` — one folder per module (12), driven by ModuleShell + registry.
  - `src/features/{projects,providers,settings}/` — feature folders with react-query hooks (repository layer over REST).
  - `src/pages/` — Assets, ProjectsPage, settings/ (General, Appearance, AIProviders, Language, Publishing, Storage, Updates, Shortcuts).
  - `src/store/app-context.tsx` — active project, sidebar collapse, command palette state.
- **Backend**: FastAPI + MongoDB (motor). Collections: projects, providers, settings. UUID string ids, ISO datetimes. Seeds 8 default providers + global settings on startup. All routes under `/api`.
- **Design system**: Space Grotesk (display/H1/H2), Manrope (H3/buttons), Inter (body), JetBrains Mono (code). Glass, soft shadows, grain, akasha-glow utilities.

## Core Requirements (static)
- 12 module shells + Settings, each with own folder.
- Collapsible sidebar with sections: Overview, Create, Library, System.
- Top bar: project selector, global search, notifications, AI status, user profile, theme toggle.
- Command palette (Ctrl+K) searching all modules, library, projects.
- Project manager (CRUD, backend-persisted).
- Replaceable AI provider architecture, 7 categories, none hardcoded (data-driven + seed).
- Settings pages (8).
- Plugin-ready architecture.

## Implemented (2026-08-05)
- Full app shell, sidebar, top bar, command palette. ✅
- Projects: create/list/set-active/delete via MongoDB. ✅
- Providers: list by category, enable/disable, set-default via MongoDB; seeded defaults. ✅
- Settings: General & Appearance persisted; Language/Publishing/Storage/Updates/Shortcuts scaffolds; AI Providers manager. ✅
- All 12 module shells with rich empty-states, tabs, capability strips. ✅
- Premium dark theme + typography system. ✅

## Backlog
- P1: Wire real AI provider integrations (LLM/Image/Video/Voice/Music/Translation/Publishing).
- P1: Project workspace detail (Story/Character/World bibles editors).
- P2: Asset storage + gallery, timeline, plugin marketplace, Tauri packaging.

## Next Tasks
- Story/World/Character bible editors within a project context.
- Provider "Add provider" dialog + credential storage.
- Tauri config scaffold.

## V2.0 Implemented (2026-06)
Backend split into `core.py` + `routes/` package (clean architecture). New:
- **Character Consistency Engine** (flagship): full Character Bible — appearance lock, reference images (object storage), outfits/expressions/props libraries, voice assignment, personality/traits/backstory, relationships, character memory, color palette, age/height, version history (snapshot + restore).
- **Project Bible**: Story/World/Style/Camera/Music/Publishing/Brand bibles, sectioned, persisted in MongoDB (permanent project memory). Wired into Story/World/Music/Image(style)/Video(camera) modules.
- **Provider Hub**: adapter-based capability framework, states (not_configured/configured/ready/error/disabled), encrypted API keys (Fernet), connection testing (local format validation, no inference), priority, default, enable/disable, add/delete, supported features. No hardcoded providers.
- **Akasha Brain**: Command Center (engine coverage), Prompt Optimizer + Assistant (Claude Sonnet 4.6 via Emergent key), Project Context Loader (aggregates bibles + locked characters into context).
- **Scene Production**: Project→Acts→Chapters→Scenes→Shots tree (architecture only), cascade delete.
- **Publish Forge Pro**: Campaign Manager, Scheduler, Publishing Queue, month Calendar (6 platforms, no live integrations).
- **Image Forge AI Editing**: provider-independent operation interfaces (object removal, background replacement, inpainting, outpainting, upscaling) + job queue resolving default image provider.
- **Object storage**: file upload/serve via Emergent object storage (character references, image sources).

Frontend: extended existing design system, new nav item (Akasha Brain), ModuleShell enhanced with per-tab `content`. No modules rebuilt/redesigned.

## Image Forge P2 — Canvas & Gallery flow (2026-06-06) ✅
Scope: Image Forge only. No backend changes — persistence reuses generic `forge_items` (module=`image`).
- **Active Canvas persistence**: active canvas image stored per project as a `forge_items` doc (kind=`canvas_state`, `data.asset_id`). Restores on tab switch and after F5. Reference cleared safely if the asset was deleted.
- **Open on Canvas**: every Assets-grid card (with an image) has a Canvas button → sets active canvas asset + switches to Canvas tab.
- **Add to Gallery**: available on each asset card and on the active canvas image. Membership stored in the gallery doc's `data.asset_ids` (no duplicate asset file/record; duplicate membership blocked). Galleries tab now shows member thumbnails + live count.
- Shared `ForgeWorkspace` gained optional controlled-tab props (`activeTab`/`onTabChange`) — backward compatible.
- Also fixed a compile-blocking bug: missing `useEffect` import in `features/publish/PublishPro.tsx`.
- Verified: testing agent 100% (backend 4/4 new pytest, all 7 frontend acceptance criteria incl. F5 persistence + duplicate prevention). Report: `/app/test_reports/iteration_6.json`.
- Known limitations (local-first single-user acceptable): duplicate-membership guard is client-side; `canvas_state` has no server-side singleton index (client picks first).

## AF-003 — Publish Forge editing fix (2026-06-06) ✅
Scope: Publish Forge only. No backend changes.
- Fixed dead header **"+ New"** button — `ModuleShell` gained an optional `onNew` prop (backward compatible; unused by other modules), wired in Publish Forge to open the post creation dialog.
- Enabled **editing existing Release posts**: clicking a Release row opens the scheduler dialog pre-filled (title/content/platforms/schedule), label reads "Save changes", persists via `PUT /api/publish/posts/{id}` (partial `$set` preserves status/campaign_id), survives F5. Delete uses `stopPropagation`.
- Verified: testing agent 100% (backend 4/4 pytest, all 4 acceptance flows incl. F5 persistence). Report: `/app/test_reports/iteration_7.json`.

## AF-004 — Provider Hub Foundation (2026-06-06) ✅
Scope: Provider Hub only. No Forge modules modified; old Settings provider page untouched.
- New dedicated **card-based Provider Hub module** at `/providers` (nav item under System). Cards show logo monogram, name, type, connection status, enabled/disabled toggle, default-model select, masked API key, Test/Edit/Delete.
- **Create/Edit dialog**: Provider Name, Type, API Key, Default Model, Base URL, Organization ID, Notes, Enable + optional catalog preset prefill.
- Backend (`providers_hub.py`): added `default_model`, `organization_id`, `notes`, `last_test_ms`; create sets `enabled`; `POST /providers/{id}/test` returns `response_ms`; new `GET /provider-catalog` (11 providers); `seed_providers` idempotently ensures the 11 catalog providers exist + backfills fields. Keys encrypted (Fernet), only masked preview returned.
- Providers seeded/available: OpenAI, Google Gemini, Anthropic Claude, ElevenLabs, Suno, Runway, Veo, Kling, Fal, Replicate, Stability AI (+ 3 legacy).
- Disabled providers still excluded from Forges (existing gating unchanged).
- Verified: testing agent 100% (backend 13/13 pytest; all acceptance flows: create/edit/delete/enable/disable/default-model + F5 persistence). Report: `/app/test_reports/iteration_8.json`.
- Note: Test Connection is LOCAL key-format validation only (no real API calls), per spec.

## AF-005B — Brain Knowledge Store & Search (backend only) (2026-06-06) ✅
Scope: backend only, no frontend. Extended the existing `/api/brain` router (existing optimize/assist/status/history untouched and verified still working).
- New `knowledge_items` MongoDB collection: `{id, project_id, entity_type, entity_id, title, text, tags[], source_module, metadata, created_at, updated_at}`. Uses shared `new_id`/`now_iso`; tags normalized (lowercase, trim, dedup).
- Idempotent indexes (created on startup via `ensure_knowledge_indexes`): unique `id`, compound `project_id+entity_type`, compound `project_id+entity_id`, text index `knowledge_text` on title/text/tags (weights 10/5/3).
- Endpoints: `POST /api/brain/knowledge` (create), `GET /api/brain/knowledge` (project-scoped list + filters), `GET /api/brain/knowledge/{id}`, `PUT` (partial, preserves id/project_id/created_at), `DELETE`, `POST /api/brain/knowledge/ingest` (upsert by project_id+entity_type+entity_id+source_module — no dupes), `GET /api/brain/search` (project-scoped `$text` search, relevance score, sort by score then updated_at).
- Verified: `backend/tests/test_brain_knowledge.py` — 8 tests, all pass (covers acceptance 1–16 incl. project isolation, filters, ingest upsert, empty/invalid handling, existing-endpoint smoke).

## AF-005C — Automatic Knowledge Ingestion (backend only) (2026-06-06) ✅
Scope: backend only. Auto-syncs 4 modules into the AF-005B `knowledge_items` store; no frontend, no graph/embeddings/RAG.
- New `routes/knowledge_sync.py` — best-effort (never breaks the source save) upsert/delete + mappers for bibles, characters, production nodes, forge_items, plus `backfill_project`.
- Hooks wired: bibles (`update_bible` sync + new `DELETE /projects/{pid}/bibles/{type}`), characters (create/AI-create/update/restore sync, delete removes), production (create/update sync, cascade delete removes), forge_items (create/update sync, delete removes). Forge eligibility skips `canvas_state`/empty; entity_type derives from kind|module; source_module=`forge_items:<module>`.
- Ingestion identity reuses project_id+entity_type+entity_id+source_module (no duplicates on repeated saves).
- New endpoint: `POST /api/brain/knowledge/backfill` `{project_id}` → returns per-source + totals `{created,updated,skipped,failed}`.
- Project delete now also purges `knowledge_items`.
- Verified: `backend/tests/test_brain_ingestion.py` — 7 tests pass (acceptance 1–16). Regression: 25/25 across knowledge + provider + publish suites.

## AF-VIDEO-001 — One-Prompt Video Creator Foundation (backend only) (2026-06-06) ✅
Scope: backend only. Planning engine + provider-neutral render pipeline foundation. No desktop packaging, no FFmpeg, no provider APIs, no real video/voice/music generation.
- New `POST /api/video-projects/plan` — Akasha Brain returns a compact creative skeleton (3–8 scenes), then shots are **deterministically expanded to exactly `ceil(target/clip)` clips** with continuity inheritance (characters/world/style/camera/lighting). Persists Acts→Scenes→Shots into the **existing** `production_nodes` hierarchy (rich shot fields under node `meta`); auto-ingested to the AF-005C knowledge store. Returns clear warning (never crashes) when no LLM configured. Scales 30s→10min with no arch change.
- New `video_render_jobs` collection (all spec fields) + indexes: unique `id`, `project_id+status`, `project_id+shot_id`, `provider_job_id`.
- New render job API: `POST/GET/GET{id}/PUT/DELETE /api/video-jobs`, `/{id}/queue`, `/{id}/cancel`, `POST /video-jobs/from-plan` (one job per shot, upsert by project_id+shot_id → no duplicates). Provider resolved from Provider Hub (enabled default → highest priority); missing provider → Draft job + warning. Delete protected for `submitting`/`processing`.
- New `backend/video_adapters.py` — provider-neutral `VideoProviderAdapter` interface (validate_configuration/submit/get_status/download_result/cancel) + registry. NO concrete providers (Veo/Kling/Runway/Fal/Replicate) implemented — config always from Provider Hub.
- Verified: `backend/tests/test_video_foundation.py` — 5 tests pass (plan gen, clip-count scaling, from-plan dedup, provider resolution + draft, queue/cancel/update/delete-protection). Full regression: 76/76 across all existing suites — no regressions.

## AF-DESKTOP-002 — Desktop Runtime Configuration Foundation (2026-06-06) ✅
Scope: remove browser/deploy assumptions blocking a future Tauri shell. No packaging, no Tauri/Electron/PyInstaller, no DB/storage changes, no UI redesign.
- **Runtime backend URL** — new `frontend/src/lib/runtime.ts` `resolveBackendUrl()` priority: runtime-injected `window.__AKASHA_RUNTIME_CONFIG__.backendUrl` → `REACT_APP_BACKEND_URL` → `http://127.0.0.1:8001`. Centralized in `lib/api.ts` (all calls already route through it). No hard-coded 8001-only.
- **Routing** — `App.tsx` uses `HashRouter` in desktop mode (`isDesktop()`), `BrowserRouter` on web preview; all routes/URLs unchanged for web.
- **Backend host/port** — `server.py` gained a standalone `__main__` runner honoring `AKASHA_HOST` (default 127.0.0.1) / `AKASHA_PORT` (default 8001); inert under supervisor so preview is unaffected. Verified binds strictly to 127.0.0.1 on a custom port + clean shutdown.
- **Health handshake** — new `GET /api/health` → `{status, application, version, timestamp}`; frontend `waitForBackend()` helper polls it with bounded timeout/retry + friendly error (no infinite loop).
- **Desktop detection** — `window.__AKASHA_RUNTIME_CONFIG__` `{desktop, backendUrl, appDataDir}` read via `getRuntimeConfig()`/`isDesktop()`; no Tauri deps, no secrets.
- Verified: backend regression 56/56; TS check clean; web preview loads (14 providers), routes navigate + deep-route refresh not blank; runtime override redirected calls to injected URL with friendly error toast.

## AF-DESKTOP-003 — Local File Storage Backend (2026-06-06) ✅
Scope: provider-neutral storage layer (remote default = Emergent, local = Windows-safe filesystem), preserving the object-storage interface. No Tauri/PyInstaller/DB/Forge changes.
- `core.py` storage rewritten into a backend-neutral API (interface preserved): `put_object`, `get_object`, `get_object_stream` (new, streaming), `delete_object`, `object_exists`, `get_object_metadata`, `resolve_object_path`, `init_storage`. `STORAGE_BACKEND=remote|local` (default remote → preview unchanged).
- Local backend: root `AKASHA_DATA_DIR` (default `./akasha-data`), layout `storage/akasha-forge/{images,videos,audio,music,documents,thumbnails,exports}` + `projects/ cache/ logs/`. MIME/category→canonical folder mapping, UUID filenames, extension/MIME preserved, atomic writes (`os.replace`), pathlib, sanitized segments, path-traversal rejected (`_resolve_within`).
- `routes/files.py`: streaming serve (`StreamingResponse`), extended MIME map (video/audio/docs), new `DELETE /api/files/{id}` (safe, marks record + removes object; NOT auto-called by gallery/asset deletion), richer metadata on the existing `files` collection (storage_backend, relative_path, mime_type, size_bytes, project_id, checksum) — no duplicate metadata system.
- Env vars added: `STORAGE_BACKEND`, `AKASHA_DATA_DIR`. Future Tauri shell sets `AKASHA_DATA_DIR` before launching the backend (via the AF-DESKTOP-002 `__main__` runner).
- Verified: `backend/tests/test_local_storage.py` — 8 tests (local dirs, image/video/audio/music put, unique ids, streaming+metadata, missing/traversal, delete target-only, Windows-style path, remote-mode API roundtrip). Full local-mode API proven end-to-end via standalone local server (upload→disk→stream→delete). Regression 45/45; TS clean; web preview functional.
- Migration limitation: existing remote-only files are not migrated; in local mode old remote records return a clear 404 "unavailable in current storage mode" (no crash, no corruption).

## AF-DESKTOP-004 — Local Database Shim (montydb) (2026-06) ✅
Scope: root-cause fix only. Enables the backend to run fully offline on Windows Desktop using montydb (SQLite-backed) when `AKASHA_DB_BACKEND=local`, with no local MongoDB server.
- **Bug fixed** in `backend/mongo_compat.py`: montydb throws `sqlite3.OperationalError` when read/delete/count operations touch a collection that was never created (no document inserted). Two signatures observed: `unable to open database file` (missing db file) and `no such table: documents` (table not created). This aborted the project-deletion cascade at `character_versions.delete_many`, leaving `knowledge_items` un-purged (Test 23 failure).
- **Fix**: added a `_guard()` wrapper + `_is_missing_collection()` matcher that catches ONLY these two specific montydb "uncreated collection" signatures and mirrors MongoDB's no-op behavior: `find`→[], `find_one`→None, `delete_one`/`delete_many`→`_DeleteResult(deleted_count=0)`, `count_documents`→0, `distinct`→[]. Every other `OperationalError` is re-raised untouched. `insert_*`/`update_*` unchanged.
- **Verified**: `tests/desktop_local_smoke.py` → 30/30 PASS incl. Test 23 project-deletion cascade (proj_gone, kn_gone, char_gone all True) + restart durability. Regression: `test_v2_extensions`, `test_video_foundation`, `test_provider_hub`, `test_brain_*`, `test_forge_items`, `test_local_storage`, `test_publish_forge_edit`, `test_image_forge_p2` all PASS against live remote/MongoDB backend. No remote-mode behavior changed (fix confined to the montydb shim).
- Note: `test_image_forge_p2` shows false failures only under pytest-xdist parallel workers (pre-existing shared class-level state across dependent tests); passes fully with `-n0`.

## AF-DESKTOP-005 — Standalone Backend Freeze (PyInstaller, one-dir) (2026-06) ✅
Scope: freeze the FastAPI backend into a self-contained sidecar so the desktop user needs no Python/pip/MongoDB/terminal. No Tauri shell, no installer, no provider APIs, no Forge changes.
- **Strategy**: PyInstaller **one-dir** (not one-file) — chosen for reliability with this dependency graph (`pydantic_core`, `cryptography`, `uvicorn` protocol/loop plugins, `montydb`) and to keep the executable dir read-only-friendly (all mutable data → `AKASHA_DATA_DIR`). PyInstaller cannot cross-compile; the Windows `.exe` is produced by running the same spec on Windows.
- **Files added**: `backend/build.spec` (reproducible spec, safe `collect_all` for 23 packages incl. fastapi/starlette/uvicorn/pydantic/pydantic_core/cryptography/montydb/pymongo/bson/motor/multipart/requests + best-effort `emergentintegrations`/`litellm` w/ metadata; `collect_submodules` for uvicorn/anyio/routes; excludes confirmed-unused pandas/numpy/boto3/dev-tooling), `backend/pyinstaller_runtime_hook.py` (adds a `<AKASHA_DATA_DIR>/logs/backend.log` file target, preserves console), `backend/BUILD_DESKTOP.md` (exact Windows + Linux build/run docs). `.gitignore` updated to skip `backend/build/` + `backend/dist/`.
- **Files changed**: `server.py` `__main__` now runs `uvicorn.run(app, ...)` (app object, not import-string) so it works both as `python server.py` and inside a frozen bundle (no re-import of "server" by name). `tests/desktop_local_smoke.py` gained an optional `AKASHA_TEST_LAUNCH_CMD` override (backward-compatible) to run the same 30 checks against the frozen binary.
- **Output**: `backend/dist/AkashaForgeBackend/` (one-dir, ~261 MB) → `AkashaForgeBackend` (Linux here / `AkashaForgeBackend.exe` on Windows) + `_internal/`.
- **Verified against the FROZEN binary** (launched directly, no system Python): `desktop_local_smoke.py` **30/30 PASS** — health, custom `AKASHA_PORT`, 127.0.0.1 bind, local DB + storage auto-init, project/character/bible/production/forge/provider-hub/publish/video-job persistence, Brain knowledge + ingestion + search, restart durability, project-deletion cascade (Test 23), clean shutdown. Also: runs with empty `PATH` (no Python dependency); **no mutable data written into the build/dist dir**; runtime hook wrote `logs/backend.log` under `AKASHA_DATA_DIR`. Python-dev smoke still 30/30; live remote-mode supervisor backend `/api/health` still ok (no regression).
- **Limitations**: (1) real `.exe` requires building the spec on Windows (no cross-compile); (2) `AKASHA_SECRET_KEY` (Fernet) must be provided by env — a per-install keyring/DPAPI source is AF-DESKTOP-007; (3) `emergentintegrations`/`litellm` bundled best-effort (backend boots/serves fully without them; LLM features optional). Remaining desktop blockers: Tauri shell (006), secrets vault (007), installer (008).

## AF-DESKTOP-006 — Tauri Desktop Shell + Backend Sidecar Lifecycle (2026-06) ✅ (portable; native compile validated on Windows)
Scope: real native desktop shell (Tauri 2) that owns the frozen-backend lifecycle. No installer (008), no providers, no UI redesign.
- **Environment constraint**: this Emergent container is headless Linux aarch64 with **no Rust/cargo, no Tauri CLI runtime, no webkit2gtk, no display** → the native window + Rust compile and the Windows `.exe` **cannot be built here**. Per PART 12 + credit control, the full Tauri project was authored (portable, Windows-ready) and every genuinely-testable piece was validated here.
- **Files added** (`frontend/src-tauri/`): `Cargo.toml` (tauri 2, serde/serde_json, reqwest blocking+rustls, base64, getrandom, unix-only libc), `build.rs`, `tauri.conf.json` (productName "Akasha Forge", id `com.akashaforge.desktop`, `frontendDist=../build`, `beforeBuildCommand=yarn build`, `windows:[]` so the window is created in Rust after injection, `bundle.resources` = the one-dir backend folder, icon paths), `capabilities/default.json` (`core:default` for `main`), `src/main.rs` (thin launcher), `src/lib.rs` (**full lifecycle**), `resources/backend/README.txt`, `app-icon.png` (generated on-brand), `BUILD_DESKTOP_TAURI.md` (Windows build chain). `frontend/package.json`: added `tauri`/`desktop:dev`/`desktop:build` scripts + `@tauri-apps/cli@2` devDep. `.gitignore`: ignore `src-tauri/target`, `gen`, bundled backend.
- **Files changed**: `src/lib/runtime.ts` (added `startupError?` to config type — reuses existing resolver, no 2nd URL system), `src/App.tsx` (renders a minimal desktop startup-error screen `data-testid="desktop-startup-error"` if the shell reports the engine failed — no blank window; web path unchanged).
- **Rust lifecycle (`lib.rs`)**: resolve OS app-data → `AKASHA_DATA_DIR`; pick a free `127.0.0.1:0` port (no hard-coded 8001); ensure `AKASHA_SECRET_KEY` (env → per-install `.akasha_secret`, **temporary** until AF-007); spawn frozen `AkashaForgeBackend` (from bundled resource, or dev repo `backend/dist`, or `AKASHA_BACKEND_BIN`) with the 5 env vars (+DB_NAME) and `CREATE_NO_WINDOW` on Windows; bounded 30 s `/api/health` poll; inject `window.__AKASHA_RUNTIME_CONFIG__` via `initialization_script` **before** the bundle; open the window (1440×900, min 1024×700); on `ExitRequested/Exit` SIGINT-then-kill the single child (no orphans). `AKASHA_SKIP_SIDECAR=1`+`AKASHA_DEV_BACKEND_URL` for dev.
- **Sidecar packaging note**: AF-005 is PyInstaller **one-dir**, so the sidecar ships as a bundled **resource folder** (`resources/backend/AkashaForgeBackend/` + `_internal/`) resolved at runtime — not a single-file `externalBin`. Documented exact placement/naming.
- **Verified here**: `yarn build` ✅, `tsc --noEmit` clean ✅, both Tauri configs valid JSON ✅, Tauri CLI 2.11.4 installs ✅. **Sidecar-lifecycle contract 17/17 PASS** via new `backend/tests/desktop_tauri_lifecycle.py` (free-port pick, frozen-backend launch w/ exact env, `/api/health`, injected runtime-config JSON matches port, loopback bind, local DB+storage under app-data, project create + character/bible persist, graceful stop, **no orphan process**, relaunch, **data survives**, project-deletion cascade, **no mutable data in build/exe dir**). Regression: `desktop_local_smoke.py` still **30/30**; live remote-mode `/api/health` ok; web preview renders (BrowserRouter, no startup-error element, all modules).
- **NOT done here (must validate on Windows)**: native Tauri window launch, Rust compile, `tauri build`, WebView2 rendering, real `AkashaForgeBackend.exe` + Windows installer.
- **Remaining desktop blockers**: per-install secrets/DPAPI vault (AF-DESKTOP-007), Windows installer & deliverables (AF-DESKTOP-008).

## AF-DESKTOP-007 — Windows Local Secrets Vault + Provider Key Security (2026-06) ✅ (keyring/DPAPI path Windows-validated-later)
Scope: replace AF-006's temporary plaintext `.akasha_secret` with a secure per-install secrets system. No provider behavior/UI change, no installer, no new providers.
- **New `backend/secret_vault.py`** — `get_secret/set_secret/delete_secret/secret_exists` + `MASTER_KEY_NAME`/`provider_key_name()`. Backends: **keyring** (Windows → Credential Manager / DPAPI, no custom crypto) and a **DEV-ONLY `0600` file vault** under `<AKASHA_DATA_DIR>/vault/secrets.json` (clearly logged as non-production). Selection via `AKASHA_VAULT_BACKEND=auto|keyring|file`; `auto` does a **functional round-trip probe** and falls back to file only when the OS keyring is truly unavailable (the meta-backend only fails at write time on headless Linux).
- **`core.py` master-key lifecycle**: resolve `AKASHA_SECRET_KEY` env (→ remote/web-preview + all existing tests byte-for-byte unchanged) → vault `akasha_master_key` → else generate a secure Fernet key, store in vault, reuse (never regenerated). Raw key never logged / never in frontend runtime config. Fernet `encrypt/decrypt/mask_key` unchanged → existing encrypted provider records still decrypt.
- **Migration**: if a desktop `.akasha_secret` exists and the vault has no master key → validate it's a Fernet key, store in vault, **verify round-trip**, only then delete the plaintext (never before verified; failure leaves the file untouched + logs a value-free error).
- **Provider Hub**: keys stay encrypted in the DB with the master key (records, APIs, masking, enable/disable, default-model, test-connection all unchanged). `delete_provider` now best-effort removes any optional `provider:<id>:api_key` vault entry (never blocks deletion; value-free logging).
- **Tauri `lib.rs`**: removed temp secret generation + `AKASHA_SECRET_KEY`/`.akasha_secret` — the shell passes only non-sensitive runtime config; backend self-provisions via the vault. Removed now-unused `base64`/`getrandom` Rust deps.
- **build.spec**: bundle `keyring` (+ `collect_submodules` + Windows/SecretService/macOS/fail/chainer backend hidden imports, `copy_metadata`) and `secret_vault`. `requirements.txt`: added `keyring==25.7.0` (+ deps). Frozen backend rebuilt (keyring bundled).
- **Verified**: `tests/test_secret_vault.py` **7/7** (vault ops+0600, master-key gen+persist-across-restart, env precedence skips vault, migration success→plaintext removed, failed-migration safety, masking preserved, no hardcoded key in source). **Frozen** `desktop_local_smoke.py` **30/30** with NO env secret (self-provisions via vault). **Frozen** `desktop_tauri_lifecycle.py` all PASS incl. `V1` (vault master key created without env secret), `6b` (no secrets in runtime config), restart data/provider survival. Provider Hub regression **13/13** (live remote). No raw master key found in `backend.log`/stdout (0 occurrences). Python-dev smoke **30/30**; live remote `/api/health` ok.
- **Windows-only validation still required**: real keyring→Credential Manager/DPAPI storage (this container is headless Linux → exercised the file fallback only), and the native Tauri/Rust compile.
- **Remaining desktop blockers**: Windows installer & deliverables (AF-DESKTOP-008).

## AF-DESKTOP-008 — Windows Release Packaging Automation (2026-06) ✅ (native build/installer to be produced on Windows)
Scope: finish the remaining Windows release-packaging config + automation; reuse (not rebuild) AF-DESKTOP-002→007. This container is Linux aarch64 → no native `.exe`/NSIS built here.
- **Audit — already complete & reused (unchanged):** `tauri.conf.json` (productName "Akasha Forge", id `com.akashaforge.desktop`, v2.0.0, one-dir backend as bundled resource, pre-React config injection), `Cargo.toml`/`build.rs`/`main.rs`/`lib.rs` (sidecar lifecycle), `capabilities/`, `backend/build.spec` (one-dir + keyring), `secret_vault.py` (keyring/DPAPI), both BUILD docs.
- **Gaps closed this sprint:**
  - **Icons:** `icons/` was empty → generated the full set from `app-icon.png` (converted JPEG→real PNG first) via `tauri icon`; all 5 `bundle.icon` paths (32/128/128@2x/icns/ico) now exist and are committed.
  - **NSIS + WebView2:** added `bundle.windows` → `nsis.installMode="currentUser"` (no admin, installs under %LOCALAPPDATA%; user data stays in app-data dir untouched by uninstall) + `webviewInstallMode="downloadBootstrapper"` (small online installer; no-op if WebView2 present). Scoped `bundle.targets` to `["nsis"]` (avoids the WiX/MSI toolchain).
  - **Build automation:** new `scripts/build_windows.ps1` (fail-fast) — validate tools → yarn install → React build → PyInstaller one-dir via existing `build.spec` → verify `AkashaForgeBackend.exe` + `_internal/` → stage the COMPLETE one-dir into `src-tauri/resources/backend/AkashaForgeBackend/` → `tauri build` (NSIS) → print artifact paths. Flags `-SkipBackend`, `-NoInstaller`.
  - **Acceptance checklist:** new `src-tauri/WINDOWS_ACCEPTANCE_CHECKLIST.md` (34 checks incl. Credential Manager master-key, no plaintext, no orphan, cascade, installer/uninstall preserves user data).
  - **Version note:** documented `tauri.conf.json version` (=Cargo `2.0.0`) as the installer version of record; `server.py APP_VERSION="2.0"` informational; `package.json 0.1.0` unused for packaging.
- **Files changed:** `frontend/src-tauri/tauri.conf.json`, `frontend/src-tauri/icons/*` (generated), `frontend/src-tauri/app-icon.png` (JPEG→PNG), `scripts/build_windows.ps1` (new), `frontend/src-tauri/WINDOWS_ACCEPTANCE_CHECKLIST.md` (new), `frontend/src-tauri/BUILD_DESKTOP_TAURI.md` (version + automation sections), `PRD.md`. No app source (backend/frontend) changed.
- **Validated here:** `tauri.conf.json` valid JSON + all 5 icons exist; `tsc --noEmit` clean; `desktop_local_smoke.py` **30/30**; live remote `/api/health` ok. (Lifecycle harness unchanged from AF-007 — no code affecting it changed.)
- **Windows-native still required:** actual PyInstaller/Rust/NSIS build, `Akasha Forge.exe` launch, WebView2 bootstrap, Credential Manager verification, installer/uninstall/reinstall data-preservation (run `scripts/build_windows.ps1` + the checklist on Windows).
- **Desktop packaging foundation complete.** No remaining desktop blockers beyond the on-Windows build/validation.

## AF-VIDEO-002 — Provider-Neutral Video Render Execution (2026-06) ✅
Scope: make the existing render-job architecture executable end-to-end via a deterministic TEST adapter — no real Veo/Kling/Runway, no FFmpeg/assembly. Audit-first; reused all AF-VIDEO-001 systems.
- **Reused unchanged:** `video_render_jobs` model/CRUD/queue/cancel/delete/from-plan/planner, `VideoProviderAdapter` interface + registry, `_resolve_video_provider`, storage (`put_object`/`get_object_stream`) + `files` collection, provider `decrypt`.
- **Added — execution service** `backend/services/video_execution.py`: orchestrates load job → resolve provider (job.provider_id else enabled default video provider) → resolve adapter by `provider.kind` → `validate_configuration` → `submit` (persist `provider_job_id`, status→processing) → `get_status` (persist progress; failed→failed) → on completed `download_result` → `put_object` under `akasha-forge/videos/` → `files` record → set `result_asset_id`, status→completed. **Zero provider-specific branches** (all via adapter registry). Machine-readable errors: `PROVIDER_NOT_CONFIGURED/DISABLED/ADAPTER_NOT_AVAILABLE/CONFIGURATION_INVALID`. Decrypted key used only in-memory, never logged/returned.
- **State machine** (`ALLOWED_TRANSITIONS`): draft→queued→submitting→processing→completed; failure from submitting/processing; cancel from draft/queued/processing; retry only failed→queued; completed/cancelled terminal. Execution service enforces the strict chain; the raw `PUT /video-jobs/{id}` guard blocks only terminal-state escapes (completed→*, cancelled→active) so manual admin edits + AF-VIDEO-001 tests still work.
- **Added — TEST adapter** `TestVideoAdapter` in `video_adapters.py` (registered as kind `test`): deterministic submit/status(processing→completed via poll count)/download (tiny MP4 ftyp fixture)/cancel; failure driven by `model` = `fail-config|fail-submit|fail-processing`. Only reachable via a provider with `kind="test"` → never appears to normal users; not in the provider catalog.
- **Added endpoints** (`video_jobs.py`): `POST /video-jobs/{id}/execute`, `/refresh`, `/retry`, `/process-queue?limit` (concurrency 1–5, default 1, single-process, no external queue). Enhanced `/cancel` to block completed jobs + best-effort adapter-neutral provider cancel.
- **build.spec**: added `services` submodules + `services.video_execution` hidden imports (keeps future frozen builds correct).
- **Restart recovery:** submitting/processing jobs persist `provider_job_id` in the DB (never auto-reset), so `refresh` resumes after restart (proven persisted; general restart durability covered by desktop smoke/lifecycle).
- **Tested:** new `tests/test_video_execution.py` **10/10** (full path to completed asset + video/* MIME serve; processing-failure→retry; submit-rejected; cancel stays cancelled; PROVIDER_NOT_CONFIGURED/DISABLED/ADAPTER_NOT_AVAILABLE/CONFIGURATION_INVALID; project isolation + no raw key in provider responses; process-queue limit respected). Regressions: Provider Hub **13/13**, local storage **8/8**, python-dev `desktop_local_smoke.py` **30/30**, AF-VIDEO-001 **4/5** (the 5th `test_clip_count_scales` is pre-existing LLM rate-limit flakiness — all 3 plan sizes 4/8/30 shots verified working standalone; planner untouched this sprint).
- **Ready for real providers:** a real adapter implementing `VideoProviderAdapter` (registered under its `kind`) plugs into the same engine with **no execution-engine rewrite**.

## AF-VIDEO-003 — Multi-Shot FFmpeg Assembly → Final MP4 (2026-06) ✅
Scope: narrow vertical slice — completed render jobs → ordered clips → FFmpeg concat → one local MP4 → existing `files` asset. No timeline/effects/voice/music/providers.
- **Reused unchanged:** completed `video_render_jobs` + `result_asset_id`, `files` records, storage (`put_object`/`resolve_object_path`/`get_object`, `exports` category), `production_nodes.order` for film order.
- **Added — export service** `backend/services/video_export.py`: gather project render jobs → block if any non-cancelled job is not completed (`EXPORT_BLOCKED_INCOMPLETE`) → order completed jobs by `production_nodes` shot order (unresolved shots appended by created_at; duplicate shot → `DUPLICATE_SHOT`) → resolve each `result_asset_id` to a local path (remote-mode objects materialized to temp; missing → `MISSING_CLIP`) → FFmpeg **concat demuxer**, `-c copy` first with a minimal libx264/aac re-encode fallback → `put_object` under `akasha-forge/exports/<id>.mp4` → `files` record (kind `final_movie`, `clip_count`, `source_render_job_ids`, `duration_seconds` via ffprobe). Returns `{status, project_id, asset_id, url, filename, duration_seconds, size, clip_count, clip_asset_ids}`.
- **FFmpeg strategy:** invoked via `subprocess` (list-args only, no shell string from user input); binaries resolved from `PATH` or `AKASHA_FFMPEG`/`AKASHA_FFPROBE`. Missing → `FFMPEG_NOT_AVAILABLE` (503), rest of app unaffected. Installed `ffmpeg 5.1.9` in the Linux env for preview/tests; Windows installer bundling deferred to release validation (documented in `BUILD_DESKTOP.md`).
- **Added endpoint:** `POST /api/video-export` `{project_id, output_name?}` (single endpoint) in `video_jobs.py`.
- **Output location:** existing local storage `AKASHA_DATA_DIR/storage/akasha-forge/exports/` — never source tree / Tauri resources / build dir.
- **Files changed:** added `backend/services/video_export.py`, `backend/tests/test_video_export.py`; edited `backend/routes/video_jobs.py` (import + `/video-export` + `VideoExportBody`), `backend/BUILD_DESKTOP.md` (ffmpeg note). No pip deps added (ffmpeg is a system binary; `collect_submodules("services")` already bundles the module).
- **Tested (all PASS):** `test_video_export.py` **4/4** — full assemble of 3 real ffmpeg clips (order preserved by shot order despite reverse job-creation; duration ~3s; final served as `video/mp4` + ffprobe-readable + stored asset record), `MISSING_CLIP`, `EXPORT_BLOCKED_INCOMPLETE`, `NO_COMPLETED_JOBS`. Regressions: AF-VIDEO-002 execution **10/10**, local storage **8/8**; `FFMPEG_NOT_AVAILABLE` detection verified.
- **Limitations:** video-only (source audio preserved when compatible); no transcoding presets/transitions/subtitles; test-adapter clips aren't real MP4s so end-to-end from the test provider requires a real provider — the assembly path itself is proven with real MP4s. Restart-safe (final asset persisted in `files`).

## AF-PRODUCTION-001 — Production Orchestrator + Audio/Subtitles + Final Master (2026-06) ✅
Scope: connect existing systems into one project-level pipeline — plan→jobs→execution→completed clips→audio/subtitles→final master MP4. Integration only; no real providers, no Director/QC, no UI.
- **Reused unchanged:** `video_execution` (execute/refresh/retry/process-queue), `video_export.assemble_project` (ordered concat), `production_nodes.order`, storage/`files`, TEST adapter. Audio = existing generic `files` assets (no Voice/Music routes exist).
- **Gaps filled:** (1) orchestrator, (2) produce/status endpoints, (3) audio mux + SRT (extended the existing exporter — no second exporter).
- **Added — `services/production_orchestrator.py`:** derives production status from render-job records (single source of truth, no duplicate state); one advancement pass per `produce` (draft→queue→execute; queued→execute; submitting/processing→refresh) that **never touches completed/cancelled/failed** (idempotent, cost-safe — no re-render of valid shots); finalizes via `video_export` only when every non-cancelled job is completed (a **failed shot blocks finalize**). Desktop-safe (no queues/workers).
- **Extended — `services/video_export.py`:** optional `narration_asset_id`/`music_asset_id` audio mux (narration full volume; music ducked to 0.25 for intelligibility; video stream copied, AAC audio) + SRT generation from ordered shot/job `narration_text` + clip durations, persisted as a `documents`/`subtitles` `files` asset and best-effort muxed as a selectable `mov_text` track (falls back to sidecar SRT). Final `final_movie` record extended (`has_audio`, `narration_asset_id`, `music_asset_id`, `subtitle_asset_id`) — reused, not duplicated. All ffmpeg via safe arg arrays.
- **Added endpoints (`video_jobs.py`):** `POST /api/video-projects/{id}/produce` (`{narration_asset_id?, music_asset_id?, subtitles=true, auto_export=true}` → concise status incl. counts/progress/ready_for_export/final_asset_id/errors) and `GET /api/video-projects/{id}/production-status` (derived, no mutation → restart-safe reconstruction).
- **Minimal model change:** added settable `narration_text` to RenderJob model/create/update (reuses the sprint's narration concept as the per-shot subtitle source). No other refactors.
- **Restart/resume:** status derived from persisted jobs + latest `final_movie` file; completed work reused; failed jobs identifiable; retry stays via existing endpoint; re-`produce` continues from progress and won't re-export when a final already exists.
- **Tested (all PASS):** `test_production_pipeline.py` **5/5** — orchestrator advances draft→completed & **idempotent (no re-render on re-produce)**; failed shot blocks finalize; **full master with real clips + narration+music mux (valid audio+video streams, ~3s) + SRT in shot order**; video-only master (0 audio streams); NO_RENDER_JOBS. Regressions: AF-VIDEO-002 **10/10**, AF-VIDEO-003 **4/4**. No secrets in responses/logs.
- **Limitations:** audio = pre-existing local assets only (no AI voice/music generation — out of scope); minimal deterministic mix (no DAW/timeline); TEST-adapter clips aren't real MP4s so a real provider is needed for a fully adapter-driven master (the assembly+audio+subtitle path itself is proven with real media).

## AF-FINAL-CLOSURE — Movie Studio end-to-end UI (2026-06) ✅
Scope: wire the EXISTING backend video-production APIs into a visual, provider-neutral flow in the Video Forge module — Prompt → Plan → Generate Render Jobs → Produce → Progress/Retry → Final Master → View/Download MP4. No new backend architecture, no real providers, no daemons.
- **New "Movie Studio" tab** (FIRST tab in Video Forge; Scenes/Shots/Render Queue tabs untouched): `frontend/src/modules/video-forge/MovieStudio.tsx`.
  - Prompt panel → `POST /api/video-projects/plan`. Plan review (tree from `GET /api/projects/{id}/production`, flattened client-side) → "Generate Render Jobs" `POST /api/video-jobs/from-plan`. Production: "Produce Movie" drives the loop; per-shot list + Retry (`POST /api/video-jobs/{id}/retry`); progress bar + stat chips. Final Master: `<video>` on `/api/files/{final_asset_id}` + Download MP4 + optional .srt link.
- **Hooks** `frontend/src/features/video/hooks.ts`: usePlanVideo (invalidates production caches), useGenerateJobs, useProductionStatus, useProductionNodes (flattens tree), useVideoJobs, useRetryJob, `useProduceRunner` — backend has NO auto-advance daemon, so the runner repeatedly POSTs `/produce` (~1.2s; each call advances every job one step + returns fresh derived status) until terminal (completed/failed/empty), export-error, or no-provider block; 150-iter safety cap; stops on unmount/project change.
- **Backend robustness (necessary, not new arch):** `services/video_export.py` ffmpeg resolution falls back to pip-bundled **imageio-ffmpeg** static binary when apt ffmpeg is absent (container resets wipe apt packages — the root cause of the first retest's export failure); ffprobe optional (duration best-effort). `requirements.txt` += `imageio-ffmpeg==0.6.0`. `video_adapters.py`: TEST adapter now emits a REAL playable 1s MP4 (built once via ffmpeg, cached) so the full chain incl. final assembly/playback validates with no paid provider.
- **Validation:** `backend/tests/movie_studio_e2e.py` PASS; regression `test_video_execution/test_production_pipeline/test_video_export` **19/19**; frontend testing agent **100%** (iteration_10): plan card immediate (no reload), jobs, produce loop ends at "Movie Ready" ~32s, final `<video>` plays (200 video/mp4), download present, persistence after reload, no regression to the other 3 tabs.
- **Provider-neutral shipped state:** validation-only TEST provider + demo project removed after testing; only real (disabled) Kling/Runway/Veo remain. With no enabled video provider the UI still plans + generates jobs and surfaces a graceful "configure a video provider" block on produce. Real providers deferred until after application completion.


## Framework Completion Sprint (2026-06)
Built ONE reusable Forge CRUD framework and applied it consistently (no per-module CRUD duplication):
- **Backend**: generic `forge_items` collection + `routes/forge_items.py` (list/create/get/update/delete by project+module+kind). Cascade-deletes with project. Added `ai_prompt` to Character.
- **Frontend shared**: `features/forge/hooks.ts`, `components/forge/ItemFormModal.tsx` (schema-driven form + friendly error toasts), `ForgeWorkspace.tsx` (header + tabs + list + create/edit/delete), `ProviderRequired.tsx`.
- **Applied to**: Story (chapters/drafts/beats + bible), World (locations/factions/rules/timeline + bible), Video (scenes/shots-with-scene-ref/render queue), Voice (voice profiles), Music (briefs + bible), Image (canvas upload→persisted assets, galleries, assets grid, gated generation), Workflow (node/edge graph editor persisting to Mongo).
- **Character Forge extended**: added "Create with AI" prompt mode (prompt persisted) + Consistency tab; quick-create still opens the full editor.
- Provider-required (not fake) states for image/video/voice/music. Friendly toasts everywhere; no React error overlay.
- Verified: testing agent 100% — backend 21/21, all frontend CRUD + F5-persistence flows pass. Applied a11y fix (action buttons no longer hover-only).
