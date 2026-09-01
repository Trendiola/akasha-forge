"""AF-VIDEO-002 — provider-neutral video render execution.

Orchestrates the EXISTING systems only: video_render_jobs (state), Provider Hub
(resolution + decrypted config), the registered VideoProviderAdapter, and the
AF-DESKTOP-003 storage/`files` asset layer. There are ZERO provider-specific
branches here — all provider behavior lives inside adapters resolved by
provider.kind. Local, single-process, desktop-safe (no queues/workers).
"""
import asyncio
import hashlib
from typing import Any, Dict, Optional

from fastapi import HTTPException

from core import db, new_id, now_iso, logger, decrypt, put_object, APP_NAME, STORAGE_BACKEND
import video_adapters

# --- Job state machine (single source of truth) ---------------------------- #
ALLOWED_TRANSITIONS = {
    "draft": {"queued", "submitting", "cancelled"},
    "queued": {"submitting", "cancelled"},
    "submitting": {"processing", "completed", "failed", "cancelled"},
    "processing": {"processing", "completed", "failed", "cancelled"},
    "failed": {"queued"},          # only via retry
    "completed": set(),            # terminal
    "cancelled": set(),            # terminal
}
ACTIVE_STATUSES = {"submitting", "processing"}


def can_transition(current: str, target: str) -> bool:
    if current == target:
        return target in ("processing",)  # idempotent progress refresh only
    return target in ALLOWED_TRANSITIONS.get(current, set())


def _err(status_code: int, code: str, message: str) -> HTTPException:
    # Machine-readable, secret-free error payload.
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


async def _get_job(job_id: str) -> Dict[str, Any]:
    job = await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return job


async def _resolve_provider(job: Dict[str, Any]) -> Dict[str, Any]:
    provider = None
    if job.get("provider_id"):
        provider = await db.providers.find_one({"id": job["provider_id"]}, {"_id": 0})
        if not provider:
            raise _err(422, "PROVIDER_NOT_CONFIGURED", "The job's provider no longer exists.")
    else:
        provider = await db.providers.find_one(
            {"category": "video", "enabled": True, "is_default": True}, {"_id": 0}
        ) or await db.providers.find_one(
            {"category": "video", "enabled": True}, {"_id": 0}, sort=[("priority", 1)]
        )
        if not provider:
            raise _err(422, "PROVIDER_NOT_CONFIGURED", "No enabled video provider is configured in Provider Hub.")
    if not provider.get("enabled", False):
        raise _err(422, "PROVIDER_DISABLED", "The selected video provider is disabled.")
    if provider.get("category") != "video":
        raise _err(422, "PROVIDER_NOT_CONFIGURED", "The selected provider is not a video provider.")
    return provider


def _adapter_for(provider: Dict[str, Any]):
    adapter_name = (provider.get("kind") or "").strip().lower()
    adapter = video_adapters.get_video_adapter(adapter_name, _adapter_config(provider))
    if adapter is None:
        raise _err(422, "PROVIDER_ADAPTER_NOT_AVAILABLE",
                   f"No execution adapter is available for provider kind '{adapter_name or 'unknown'}'.")
    return adapter


def _adapter_config(provider: Dict[str, Any]) -> Dict[str, Any]:
    api_key = ""
    if provider.get("api_key_encrypted"):
        try:
            api_key = decrypt(provider["api_key_encrypted"])
        except Exception:
            api_key = ""
    return {
        "api_key": api_key,  # decrypted here, never logged / never returned
        "base_url": provider.get("base_url", ""),
        "default_model": provider.get("default_model", ""),
    }


async def _set(job_id: str, **fields) -> Dict[str, Any]:
    fields["updated_at"] = now_iso()
    await db.video_render_jobs.update_one({"id": job_id}, {"$set": fields})
    return await db.video_render_jobs.find_one({"id": job_id}, {"_id": 0})


async def _validate(adapter, provider: Dict[str, Any]):
    result = await adapter.validate_configuration()
    if not result.get("ok"):
        raise _err(422, result.get("error_code", "PROVIDER_CONFIGURATION_INVALID"),
                   result.get("message", "Provider configuration is invalid."))


# --- Public operations ------------------------------------------------------ #
async def execute_job(job_id: str) -> Dict[str, Any]:
    """Submit a queued/draft job to its provider adapter and persist provider_job_id."""
    job = await _get_job(job_id)
    status = job.get("status", "draft")

    # Already-submitted jobs advance via refresh (idempotent execute).
    if status in ACTIVE_STATUSES and job.get("provider_job_id"):
        return await refresh_job(job_id)
    if status in ("completed", "cancelled"):
        raise _err(409, "INVALID_TRANSITION", f"Cannot execute a job that is {status}.")
    if status == "failed":
        raise _err(409, "INVALID_TRANSITION", "Retry the failed job before executing it again.")

    provider = await _resolve_provider(job)
    adapter = _adapter_for(provider)
    await _validate(adapter, provider)

    await _set(job_id, status="submitting", provider_id=provider["id"],
               provider_type="video", started_at=job.get("started_at") or now_iso())

    try:
        res = await adapter.submit({
            "id": job["id"], "prompt": job.get("prompt", ""),
            "negative_prompt": job.get("negative_prompt", ""),
            "model": job.get("model", "") or provider.get("default_model", ""),
            "duration_seconds": job.get("duration_seconds", 8),
            "aspect_ratio": job.get("aspect_ratio", "16:9"),
            "reference_asset_ids": job.get("reference_asset_ids", []),
            "shot_id": job.get("shot_id", ""), "project_id": job.get("project_id", ""),
        })
    except Exception as exc:  # noqa: BLE001 — one job's failure must not corrupt others
        logger.exception("Video submit failed for job %s", job_id)
        return await _set(job_id, status="failed", error_code="PROVIDER_SUBMIT_ERROR",
                          error_message=f"Submission error: {exc}")

    if res.get("status") == "failed" or not res.get("provider_job_id"):
        return await _set(job_id, status="failed",
                          error_code=res.get("error_code", "PROVIDER_SUBMIT_REJECTED"),
                          error_message=res.get("error_message", "Provider rejected the submission."))

    return await _set(job_id, status="processing", provider_job_id=res["provider_job_id"],
                      progress=int(res.get("progress", 0)), error_code="", error_message="")


async def refresh_job(job_id: str) -> Dict[str, Any]:
    """Poll an already-submitted job's provider status and persist the latest state."""
    job = await _get_job(job_id)
    if job.get("status") not in ACTIVE_STATUSES:
        raise _err(409, "INVALID_TRANSITION",
                   f"Only submitting/processing jobs can be refreshed (job is {job.get('status')}).")
    if not job.get("provider_job_id"):
        raise _err(409, "NO_PROVIDER_JOB", "This job has no provider_job_id yet; execute it first.")

    provider = await _resolve_provider(job)
    adapter = _adapter_for(provider)

    try:
        st = await adapter.get_status(job["provider_job_id"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Video status poll failed for job %s", job_id)
        return await _set(job_id, status="failed", error_code="PROVIDER_STATUS_ERROR",
                          error_message=f"Status error: {exc}")

    pstatus = st.get("status", "processing")
    if pstatus == "failed":
        return await _set(job_id, status="failed",
                          error_code=st.get("error_code", "PROVIDER_PROCESSING_FAILED"),
                          error_message=st.get("error_message", "Provider reported a failure."))
    if pstatus != "completed":
        return await _set(job_id, status="processing", progress=int(st.get("progress", job.get("progress", 0))))

    # Completed → download + persist through the EXISTING storage/asset layer.
    try:
        dl = await adapter.download_result(job["provider_job_id"])
        asset = await _store_result(job, dl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Video result storage failed for job %s", job_id)
        return await _set(job_id, status="failed", error_code="RESULT_STORAGE_ERROR",
                          error_message=f"Could not store the generated clip: {exc}")

    return await _set(job_id, status="completed", progress=100, result_asset_id=asset["id"],
                      error_code="", error_message="", completed_at=now_iso())


async def _store_result(job: Dict[str, Any], dl: Dict[str, Any]) -> Dict[str, Any]:
    """Save the generated clip via the existing storage abstraction + files record."""
    data = dl.get("data")
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("adapter download_result returned no bytes")
    data = bytes(data)
    mime = dl.get("mime_type", "video/mp4")
    ext = "mp4" if "mp4" in mime else (mime.split("/")[-1] or "mp4")
    file_id = new_id()
    # Lives under <storage>/akasha-forge/videos/ via the canonical local mapping.
    path = f"{APP_NAME}/videos/{file_id}.{ext}"
    stored = put_object(path, data, mime)
    record = {
        "id": file_id,
        "storage_backend": STORAGE_BACKEND,
        "storage_path": stored["path"],
        "relative_path": stored["path"],
        "original_filename": dl.get("filename", f"{file_id}.{ext}"),
        "content_type": mime, "mime_type": mime,
        "size": stored.get("size", len(data)), "size_bytes": stored.get("size", len(data)),
        "category": "videos",
        "project_id": job.get("project_id", ""),
        "shot_id": job.get("shot_id", ""),
        "render_job_id": job.get("id", ""),
        "checksum": hashlib.sha256(data).hexdigest(),
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(dict(record))
    return record


async def retry_job(job_id: str) -> Dict[str, Any]:
    """Reset a FAILED job to queued, clearing transient state, preserving inputs."""
    job = await _get_job(job_id)
    if job.get("status") != "failed":
        raise _err(409, "INVALID_TRANSITION", "Only failed jobs can be retried.")
    return await _set(job_id, status="queued", provider_job_id="", progress=0,
                      error_code="", error_message="", completed_at="")


async def process_queue(limit: int = 1) -> Dict[str, Any]:
    """Advance up to `limit` queued jobs locally (conservative concurrency = 1)."""
    limit = max(1, min(int(limit or 1), 5))
    # MontyDB's async compatibility cursor does not consistently enforce the
    # ``to_list(length)`` bound on Windows. Slice defensively so the public
    # concurrency contract is honored by every supported backend.
    queued = (await db.video_render_jobs.find({"status": "queued"}, {"_id": 0}).sort("created_at", 1).to_list(limit))[:limit]
    results = []
    for q in queued:
        try:
            job = await execute_job(q["id"])
            results.append({"id": q["id"], "status": job.get("status")})
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            results.append({"id": q["id"], "status": "error", "error": detail})
        await asyncio.sleep(0)  # yield; keep single-process desktop responsive
    return {"processed": len(results), "limit": limit, "results": results}
