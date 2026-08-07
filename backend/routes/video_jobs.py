"""AF-VIDEO-001 — One-Prompt Video Creator foundation.

Planner (POST /api/video-projects/plan) builds a full production plan via
Akasha Brain and persists Acts→Scenes→Shots into the EXISTING production_nodes
hierarchy (no second hierarchy). Render jobs live in a new video_render_jobs
collection with a provider-neutral API. Planned nodes are auto-ingested into
the AF-005C knowledge store for Brain search.
"""
import json
import math
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator

from core import db, new_id, now_iso, logger
from routes import brain, knowledge_sync
from services import video_execution, video_export
import video_adapters

router = APIRouter(prefix="/api", tags=["video"])

JOB_STATUSES = {"draft", "queued", "submitting", "processing", "completed", "failed", "cancelled"}
_DELETE_PROTECTED = {"submitting", "processing"}


# ============================================================================
# video_render_jobs model + indexes
# ============================================================================
class RenderJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    shot_id: str = ""
    provider_id: Optional[str] = None
    provider_type: str = "video"
    model: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    reference_asset_ids: List[str] = Field(default_factory=list)
    duration_seconds: int = 8
    aspect_ratio: str = "16:9"
    status: str = "draft"
    progress: int = 0
    provider_job_id: str = ""
    result_asset_id: str = ""
    error_code: str = ""
    error_message: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    started_at: str = ""
    completed_at: str = ""


async def ensure_video_indexes():
    try:
        await db.video_render_jobs.create_index("id", unique=True)
        await db.video_render_jobs.create_index([("project_id", 1), ("status", 1)])
        await db.video_render_jobs.create_index([("project_id", 1), ("shot_id", 1)])
        await db.video_render_jobs.create_index("provider_job_id")
    except Exception as exc:
        logger.warning("video_render_jobs index setup deferred: %s", exc)


async def _resolve_video_provider():
    return await db.providers.find_one(
        {"category": "video", "enabled": True, "is_default": True}, {"_id": 0}
    ) or await db.providers.find_one(
        {"category": "video", "enabled": True}, {"_id": 0}, sort=[("priority", 1)]
    )


# ============================================================================
# PART 1/2 — One-Prompt Video Project Planner (reuses production_nodes)
# ============================================================================
class PlanRequest(BaseModel):
    project_id: str
    prompt: str
    target_duration_seconds: int = 60
    aspect_ratio: str = "16:9"
    language: str = "en"
    clip_duration_seconds: int = 8
    style: Optional[str] = None
    target_audience: Optional[str] = None

    @field_validator("project_id", "prompt")
    @classmethod
    def _nonempty(cls, v: str, info):
        if not str(v).strip():
            raise ValueError(f"{info.field_name} is required")
        return str(v).strip()

    @field_validator("target_duration_seconds", "clip_duration_seconds")
    @classmethod
    def _positive(cls, v: int, info):
        if v is None or v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v


PLAN_SYSTEM = (
    "You are Akasha Brain, a film director and AI video producer. Turn the user's single idea into a "
    "COMPACT creative plan for an AI-generated video. Return ONLY strict minified JSON (no markdown, no "
    "prose) with EXACTLY these keys: title (string), concept (string), story_summary (string), "
    "visual_style (string), narration (string), music_direction (string), sound_effects (array of short "
    "strings), scenes (array of 3 to 8 items). Each scene = {title, summary, location, "
    "characters:[strings], camera, lighting}. Keep every string under 160 characters. The scenes must "
    "flow chronologically and keep characters, world and style consistent. Output compact JSON only."
)

_CAMERA_CYCLE = ["wide establishing shot", "medium shot", "close-up", "tracking shot", "over-the-shoulder", "low-angle shot"]
_DEFAULT_NEGATIVE = "blurry, low quality, distorted, deformed, watermark, text, extra limbs"


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])


def _distribute(total: int, buckets: int) -> List[int]:
    """Spread `total` shots across `buckets` scenes as evenly as possible (each >=1)."""
    buckets = max(1, min(buckets, total))
    base, rem = divmod(total, buckets)
    return [base + (1 if i < rem else 0) for i in range(buckets)]


async def _insert_node(project_id, ntype, parent_id, title, description, order, status, meta=None):
    node = {
        "id": new_id(), "project_id": project_id, "type": ntype, "parent_id": parent_id,
        "title": title or ntype.title(), "description": description or "",
        "status": status, "order": order,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    if meta:
        node["meta"] = meta
    await db.production_nodes.insert_one(dict(node))
    node.pop("_id", None)
    await knowledge_sync.sync_production_node(node)
    return node


@router.post("/video-projects/plan")
async def plan_video_project(body: PlanRequest):
    project = await db.projects.find_one({"id": body.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    num_shots = max(1, math.ceil(body.target_duration_seconds / body.clip_duration_seconds))
    warn_stub = {
        "project_id": body.project_id,
        "estimated_total_clips": num_shots,
        "clip_duration_seconds": body.clip_duration_seconds,
    }

    if not brain.EMERGENT_LLM_KEY:
        return {"status": "needs_configuration",
                "warning": "No LLM provider is configured. Add and enable an LLM provider in Provider Hub to generate a plan.",
                **warn_stub}

    style_line = f"Preferred visual style: {body.style}. " if body.style else ""
    audience_line = f"Target audience: {body.target_audience}. " if body.target_audience else ""
    user = (
        f"{style_line}{audience_line}Language: {body.language}. Aspect ratio: {body.aspect_ratio}. "
        f"The final video is ~{body.target_duration_seconds}s split into {num_shots} clips of ~{body.clip_duration_seconds}s each.\n\n"
        f"IDEA:\n{body.prompt}"
    )
    try:
        raw = await brain._llm(PLAN_SYSTEM, user, max_tokens=1800)
        parsed = _parse_json(raw)
    except HTTPException as exc:
        return {"status": "needs_configuration", "warning": f"Akasha Brain is unavailable: {exc.detail}", **warn_stub}
    except Exception:
        logger.exception("Video plan generation failed for project %s", body.project_id)
        return {"status": "error",
                "warning": "Akasha Brain couldn't turn that prompt into a plan. Please rephrase and try again.",
                **warn_stub}

    visual_style = str(parsed.get("visual_style", "") or body.style or "cinematic")
    narration = str(parsed.get("narration", ""))
    scenes_raw = parsed.get("scenes") if isinstance(parsed.get("scenes"), list) else []
    scenes_raw = [s for s in scenes_raw if isinstance(s, dict)]
    if not scenes_raw:
        scenes_raw = [{"title": "Scene 1", "summary": parsed.get("story_summary", "") or body.prompt}]

    # Deterministically expand scenes into EXACTLY num_shots shots with continuity.
    per_scene = _distribute(num_shots, len(scenes_raw))
    active_scenes = scenes_raw[: len(per_scene)]

    # Group scenes into Acts (up to 3 scenes per act) — reuses the production hierarchy.
    acts_out, scenes_out, shots_out = [], [], []
    shot_order = 0
    act_node = None
    for s_idx, scene in enumerate(active_scenes):
        if s_idx % 3 == 0:
            act_index = s_idx // 3
            act_node = await _insert_node(body.project_id, "act", None, f"Act {act_index + 1}", parsed.get("story_summary", ""), act_index, "planned")
            acts_out.append({"id": act_node["id"], "title": act_node["title"], "summary": parsed.get("story_summary", ""), "order": act_index})

        s_summary = str(scene.get("summary", "") or scene.get("title", ""))
        s_location = str(scene.get("location", ""))
        s_chars = scene.get("characters", []) if isinstance(scene.get("characters"), list) else []
        s_camera = str(scene.get("camera", ""))
        s_lighting = str(scene.get("lighting", ""))
        scene_node = await _insert_node(body.project_id, "scene", act_node["id"], scene.get("title", f"Scene {s_idx+1}"), s_summary, s_idx, "planned")
        scenes_out.append({"id": scene_node["id"], "act_id": act_node["id"], "title": scene_node["title"], "summary": s_summary, "order": s_idx})

        for beat in range(per_scene[s_idx]):
            camera = s_camera or _CAMERA_CYCLE[shot_order % len(_CAMERA_CYCLE)]
            visual_prompt = ", ".join([p for p in [s_summary, s_location, visual_style] if p]).strip(", ")
            meta = {
                "scene_id": scene_node["id"],
                "duration_seconds": body.clip_duration_seconds,
                "visual_prompt": visual_prompt or body.prompt,
                "negative_prompt": _DEFAULT_NEGATIVE,
                "camera": camera,
                "lighting": s_lighting or "natural cinematic lighting",
                "action": s_summary,
                "characters": s_chars,
                "location": s_location,
                "continuity_notes": ("Opening shot; establish characters, world and style." if shot_order == 0
                                     else "Continues from the previous shot; keep characters, wardrobe, world, style, camera and lighting consistent."),
                "narration_text": narration if (shot_order == 0 and beat == 0) else "",
                "sound_notes": str(parsed.get("music_direction", "")),
            }
            shot_node = await _insert_node(
                body.project_id, "shot", scene_node["id"],
                f"{scene_node['title']} — Shot {beat + 1}", meta["visual_prompt"], shot_order, "planned", meta=meta,
            )
            shots_out.append({
                "id": shot_node["id"], "scene_id": scene_node["id"], "order": shot_order,
                "title": shot_node["title"], "duration_seconds": body.clip_duration_seconds,
                "visual_prompt": meta["visual_prompt"], "negative_prompt": meta["negative_prompt"],
                "camera": meta["camera"], "lighting": meta["lighting"], "action": meta["action"],
                "characters": meta["characters"], "location": meta["location"],
                "continuity_notes": meta["continuity_notes"], "narration_text": meta["narration_text"],
                "sound_notes": meta["sound_notes"], "status": "planned",
            })
            shot_order += 1

    return {
        "status": "planned",
        "project_id": body.project_id,
        "title": parsed.get("title", project.get("name", "Untitled")),
        "concept": parsed.get("concept", ""),
        "story_summary": parsed.get("story_summary", ""),
        "visual_style": visual_style,
        "aspect_ratio": body.aspect_ratio,
        "language": body.language,
        "clip_duration_seconds": body.clip_duration_seconds,
        "estimated_total_clips": num_shots,
        "narration": narration,
        "music_direction": parsed.get("music_direction", ""),
        "sound_effects": parsed.get("sound_effects", []) if isinstance(parsed.get("sound_effects"), list) else [],
        "acts": acts_out,
        "scenes": scenes_out,
        "shots": shots_out,
    }


# ============================================================================
# PART 3/4 — Render job API
# ============================================================================
class RenderJobCreate(BaseModel):
    project_id: str
    shot_id: str = ""
    provider_id: Optional[str] = None
    model: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    reference_asset_ids: List[str] = Field(default_factory=list)
    duration_seconds: int = 8
    aspect_ratio: str = "16:9"

    @field_validator("project_id")
    @classmethod
    def _nonempty(cls, v: str):
        if not str(v).strip():
            raise ValueError("project_id is required")
        return str(v).strip()


class RenderJobUpdate(BaseModel):
    model: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    reference_asset_ids: Optional[List[str]] = None
    duration_seconds: Optional[int] = None
    aspect_ratio: Optional[str] = None
    provider_id: Optional[str] = None
    provider_job_id: Optional[str] = None
    result_asset_id: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


async def _build_job(payload: dict, provider: Optional[dict]) -> RenderJob:
    return RenderJob(
        project_id=payload["project_id"], shot_id=payload.get("shot_id", ""),
        provider_id=(provider or {}).get("id") if not payload.get("provider_id") else payload["provider_id"],
        provider_type="video",
        model=payload.get("model") or ((provider or {}).get("default_model", "") if provider else ""),
        prompt=payload.get("prompt", ""), negative_prompt=payload.get("negative_prompt", ""),
        reference_asset_ids=payload.get("reference_asset_ids", []) or [],
        duration_seconds=payload.get("duration_seconds", 8), aspect_ratio=payload.get("aspect_ratio", "16:9"),
        status="draft",
    )


@router.post("/video-jobs")
async def create_video_job(body: RenderJobCreate):
    provider = None
    if body.provider_id:
        provider = await db.providers.find_one({"id": body.provider_id}, {"_id": 0})
    else:
        provider = await _resolve_video_provider()
    job = await _build_job(body.model_dump(), provider)
    doc = job.model_dump()
    await db.video_render_jobs.insert_one(dict(doc))
    warning = "" if provider else "No enabled video provider found. Saved as a Draft job — configure one in Provider Hub."
    return {**doc, "warning": warning}


@router.get("/video-jobs")
async def list_video_jobs(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    shot_id: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
):
    query: Dict[str, Any] = {}
    if project_id:
        query["project_id"] = project_id
    if status:
        query["status"] = status
    if shot_id:
        query["shot_id"] = shot_id
    return await db.video_render_jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)


@router.get("/video-jobs/{job_id}")
async def get_video_job(job_id: str):
    doc = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Render job not found")
    return doc


@router.put("/video-jobs/{job_id}")
async def update_video_job(job_id: str, body: RenderJobUpdate):
    existing = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Render job not found")
    updates = body.model_dump(exclude_none=True)
    if "status" in updates:
        target = updates["status"]
        if target not in JOB_STATUSES:
            raise HTTPException(status_code=422, detail=f"Invalid status. Allowed: {sorted(JOB_STATUSES)}")
        current = existing.get("status", "draft")
        # Manual PUT is an admin override; it must still never resurrect a terminal
        # job (the sprint's forbidden cases: completed→*, cancelled→active). The
        # strict forward chain is enforced by the execution service.
        if current in ("completed", "cancelled") and target in ("queued", "submitting", "processing"):
            raise HTTPException(status_code=409, detail={
                "code": "INVALID_TRANSITION",
                "message": f"Cannot move a {current} job to '{target}'."})
    updates["updated_at"] = now_iso()
    await db.video_render_jobs.update_one({"id": job_id}, {"$set": updates})
    return await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})


@router.post("/video-jobs/{job_id}/queue")
async def queue_video_job(job_id: str):
    job = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    provider = None
    if job.get("provider_id"):
        provider = await db.providers.find_one({"id": job["provider_id"], "enabled": True}, {"_id": 0})
    if not provider:
        provider = await _resolve_video_provider()
    if not provider:
        return {**job, "queued": False, "warning": "No enabled video provider. Configure one in Provider Hub before queueing."}
    await db.video_render_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "queued", "provider_id": provider["id"], "provider_type": "video", "updated_at": now_iso()}},
    )
    doc = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    return {**doc, "queued": True}


@router.post("/video-jobs/{job_id}/execute")
async def execute_video_job(job_id: str):
    """AF-VIDEO-002: submit a queued/draft job to its provider adapter."""
    return await video_execution.execute_job(job_id)


@router.post("/video-jobs/{job_id}/refresh")
async def refresh_video_job(job_id: str):
    """AF-VIDEO-002: poll a submitted job's provider status and persist it."""
    return await video_execution.refresh_job(job_id)


@router.post("/video-jobs/{job_id}/retry")
async def retry_video_job(job_id: str):
    """AF-VIDEO-002: reset a failed job to queued, preserving creative inputs."""
    return await video_execution.retry_job(job_id)


@router.post("/video-jobs/process-queue")
async def process_video_queue(limit: int = Query(1, ge=1, le=5)):
    """AF-VIDEO-002: advance up to `limit` queued jobs locally (concurrency ~1)."""
    return await video_execution.process_queue(limit)


class VideoExportBody(BaseModel):
    project_id: str
    output_name: str = ""

    @field_validator("project_id")
    @classmethod
    def _nonempty(cls, v: str):
        if not str(v).strip():
            raise ValueError("project_id is required")
        return str(v).strip()


@router.post("/video-export")
async def export_project_video(body: VideoExportBody):
    """AF-VIDEO-003: assemble a project's completed clips into one final MP4."""
    return await video_export.assemble_project(body.project_id, body.output_name)


@router.post("/video-jobs/{job_id}/cancel")
async def cancel_video_job(job_id: str):
    job = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    if job.get("status") == "completed":
        raise HTTPException(status_code=409, detail={
            "code": "INVALID_TRANSITION", "message": "A completed job cannot be cancelled."})
    if job.get("status") == "cancelled":
        return job
    # Best-effort provider-side cancel (adapter-neutral; never leaks secrets).
    if job.get("provider_job_id"):
        try:
            provider = await db.providers.find_one({"id": job.get("provider_id")}, {"_id": 0})
            if provider:
                adapter = video_adapters.get_video_adapter(
                    (provider.get("kind") or "").strip().lower(), {})
                if adapter is not None:
                    await adapter.cancel(job["provider_job_id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Provider cancel best-effort failed for job %s: %s", job_id, exc)
    await db.video_render_jobs.update_one(
        {"id": job_id}, {"$set": {"status": "cancelled", "updated_at": now_iso()}})
    return await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})


@router.delete("/video-jobs/{job_id}")
async def delete_video_job(job_id: str):
    job = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    if job.get("status") in _DELETE_PROTECTED:
        raise HTTPException(status_code=409, detail=f"Cannot delete a job while it is {job['status']}. Cancel it first.")
    await db.video_render_jobs.delete_one({"id": job_id})
    return {"ok": True, "deleted": job_id}


class FromPlanBody(BaseModel):
    project_id: str
    provider_id: Optional[str] = None
    model: str = ""
    aspect_ratio: str = "16:9"

    @field_validator("project_id")
    @classmethod
    def _nonempty(cls, v: str):
        if not str(v).strip():
            raise ValueError("project_id is required")
        return str(v).strip()


@router.post("/video-jobs/from-plan")
async def create_jobs_from_plan(body: FromPlanBody):
    shots = await db.production_nodes.find({"project_id": body.project_id, "type": "shot"}, {"_id": 0}).sort("order", 1).to_list(5000)
    provider = None
    if body.provider_id:
        provider = await db.providers.find_one({"id": body.provider_id}, {"_id": 0})
    else:
        provider = await _resolve_video_provider()

    created, updated = 0, 0
    for shot in shots:
        meta = shot.get("meta", {}) or {}
        identity = {"project_id": body.project_id, "shot_id": shot["id"]}
        set_fields = {
            "prompt": meta.get("visual_prompt", "") or shot.get("description", ""),
            "negative_prompt": meta.get("negative_prompt", ""),
            "duration_seconds": meta.get("duration_seconds", 8),
            "aspect_ratio": body.aspect_ratio,
            "provider_id": (provider or {}).get("id") if not body.provider_id else body.provider_id,
            "provider_type": "video",
            "model": body.model or ((provider or {}).get("default_model", "") if provider else ""),
            "updated_at": now_iso(),
        }
        set_on_insert = {"id": new_id(), "status": "draft", "progress": 0, "provider_job_id": "",
                         "result_asset_id": "", "error_code": "", "error_message": "",
                         "reference_asset_ids": [], "started_at": "", "completed_at": "",
                         "created_at": now_iso(), **identity}
        res = await db.video_render_jobs.update_one(identity, {"$set": set_fields, "$setOnInsert": set_on_insert}, upsert=True)
        if res.upserted_id is not None:
            created += 1
        else:
            updated += 1

    warning = "" if provider else "No enabled video provider found. Jobs saved as Draft — configure one in Provider Hub."
    return {"project_id": body.project_id, "shots": len(shots), "created": created, "updated": updated, "warning": warning}
