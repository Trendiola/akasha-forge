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

## Framework Completion Sprint (2026-06)
Built ONE reusable Forge CRUD framework and applied it consistently (no per-module CRUD duplication):
- **Backend**: generic `forge_items` collection + `routes/forge_items.py` (list/create/get/update/delete by project+module+kind). Cascade-deletes with project. Added `ai_prompt` to Character.
- **Frontend shared**: `features/forge/hooks.ts`, `components/forge/ItemFormModal.tsx` (schema-driven form + friendly error toasts), `ForgeWorkspace.tsx` (header + tabs + list + create/edit/delete), `ProviderRequired.tsx`.
- **Applied to**: Story (chapters/drafts/beats + bible), World (locations/factions/rules/timeline + bible), Video (scenes/shots-with-scene-ref/render queue), Voice (voice profiles), Music (briefs + bible), Image (canvas upload→persisted assets, galleries, assets grid, gated generation), Workflow (node/edge graph editor persisting to Mongo).
- **Character Forge extended**: added "Create with AI" prompt mode (prompt persisted) + Consistency tab; quick-create still opens the full editor.
- Provider-required (not fake) states for image/video/voice/music. Friendly toasts everywhere; no React error overlay.
- Verified: testing agent 100% — backend 21/21, all frontend CRUD + F5-persistence flows pass. Applied a11y fix (action buttons no longer hover-only).
