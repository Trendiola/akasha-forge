"""AF-PRODUCTION-001 — project-level production orchestrator.

Connects existing systems only: it CALLS video_execution (advance jobs) and
video_export (assemble + audio/subtitles). It derives production status from the
existing render-job records (single source of truth) — no duplicate state, no
queue/worker infra. Idempotent + resumable: completed jobs are never re-rendered.
"""
from typing import Any, Dict, List

from fastapi import HTTPException

from core import db
import services.video_execution as video_execution
import services.video_export as video_export

TERMINAL = {"completed", "cancelled", "failed"}


async def _jobs(project_id: str) -> List[Dict[str, Any]]:
    return await db.video_render_jobs.find({"project_id": project_id}, {"_id": 0}).to_list(10000)


def _counts(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    c = {k: 0 for k in ("draft", "queued", "submitting", "processing", "completed", "failed", "cancelled")}
    for j in jobs:
        c[j.get("status", "draft")] = c.get(j.get("status", "draft"), 0) + 1
    return c


async def _latest_final(project_id: str) -> Dict[str, Any]:
    rows = await db.files.find(
        {"project_id": project_id, "kind": "final_movie", "is_deleted": False}, {"_id": 0}
    ).sort("created_at", -1).to_list(1)
    return rows[0] if rows else {}


def _status_view(project_id: str, jobs: List[Dict[str, Any]], final: Dict[str, Any],
                 errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    c = _counts(jobs)
    total = len(jobs)
    non_cancelled = total - c["cancelled"]
    active = c["queued"] + c["submitting"] + c["processing"] + c["draft"]
    # Ready only when every non-cancelled job is completed (a failed shot blocks it).
    ready = non_cancelled > 0 and c["completed"] == non_cancelled and c["failed"] == 0
    progress = int(round(100 * c["completed"] / non_cancelled)) if non_cancelled else 0
    if final and ready:
        status = "completed"
    elif c["failed"] > 0 and active == 0:
        status = "failed"
    elif active > 0:
        status = "rendering"
    elif ready:
        status = "ready_for_export"
    else:
        status = "empty"
    return {
        "project_id": project_id, "status": status, "total_jobs": total,
        "draft": c["draft"], "queued": c["queued"], "submitting": c["submitting"],
        "processing": c["processing"], "completed": c["completed"], "failed": c["failed"],
        "cancelled": c["cancelled"], "progress": progress, "ready_for_export": ready,
        "final_asset_id": final.get("id", ""),
        "final_url": (f"/api/files/{final['id']}" if final else ""),
        "subtitle_asset_id": final.get("subtitle_asset_id", ""),
        "errors": errors,
    }


async def get_status(project_id: str) -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    jobs = await _jobs(project_id)
    return _status_view(project_id, jobs, await _latest_final(project_id), [])


async def produce(project_id: str, narration_asset_id: str = "", music_asset_id: str = "",
                  subtitles: bool = True, auto_export: bool = True) -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    jobs = await _jobs(project_id)
    if not jobs:
        raise HTTPException(status_code=422, detail={
            "code": "NO_RENDER_JOBS", "message": "This project has no render jobs to produce."})

    errors: List[Dict[str, Any]] = []

    # One advancement pass — never touches completed/cancelled/failed jobs (idempotent,
    # cost-safe: no re-rendering of valid completed shots). Real providers are slow,
    # so we advance one step per call rather than blocking the request.
    for j in jobs:
        st = j.get("status", "draft")
        try:
            if st == "draft":
                await db.video_render_jobs.update_one(
                    {"id": j["id"]}, {"$set": {"status": "queued"}})
                await video_execution.execute_job(j["id"])
            elif st == "queued":
                await video_execution.execute_job(j["id"])
            elif st in ("submitting", "processing") and j.get("provider_job_id"):
                await video_execution.refresh_job(j["id"])
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            errors.append({"job_id": j["id"], **detail})

    jobs = await _jobs(project_id)  # re-read after the pass
    view = _status_view(project_id, jobs, await _latest_final(project_id), errors)

    # Finalize once everything is complete (and not already exported this state).
    if auto_export and view["ready_for_export"] and not view["final_asset_id"]:
        try:
            final = await video_export.assemble_project(
                project_id, output_name=project.get("name", ""),
                narration_asset_id=narration_asset_id, music_asset_id=music_asset_id,
                subtitles=subtitles)
            view = _status_view(project_id, jobs, await _latest_final(project_id), errors)
            view["final_asset_id"] = final["asset_id"]
            view["final_url"] = final["url"]
            view["subtitle_asset_id"] = final.get("subtitle_asset_id", "")
            view["status"] = "completed"
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            errors.append({"stage": "export", **detail})
            view["errors"] = errors
    return view
