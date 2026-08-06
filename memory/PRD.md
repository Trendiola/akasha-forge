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

## Framework Completion Sprint (2026-06)
Built ONE reusable Forge CRUD framework and applied it consistently (no per-module CRUD duplication):
- **Backend**: generic `forge_items` collection + `routes/forge_items.py` (list/create/get/update/delete by project+module+kind). Cascade-deletes with project. Added `ai_prompt` to Character.
- **Frontend shared**: `features/forge/hooks.ts`, `components/forge/ItemFormModal.tsx` (schema-driven form + friendly error toasts), `ForgeWorkspace.tsx` (header + tabs + list + create/edit/delete), `ProviderRequired.tsx`.
- **Applied to**: Story (chapters/drafts/beats + bible), World (locations/factions/rules/timeline + bible), Video (scenes/shots-with-scene-ref/render queue), Voice (voice profiles), Music (briefs + bible), Image (canvas upload→persisted assets, galleries, assets grid, gated generation), Workflow (node/edge graph editor persisting to Mongo).
- **Character Forge extended**: added "Create with AI" prompt mode (prompt persisted) + Consistency tab; quick-create still opens the full editor.
- Provider-required (not fake) states for image/video/voice/music. Friendly toasts everywhere; no React error overlay.
- Verified: testing agent 100% — backend 21/21, all frontend CRUD + F5-persistence flows pass. Applied a11y fix (action buttons no longer hover-only).
