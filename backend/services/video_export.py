"""AF-VIDEO-003 — minimal multi-shot FFmpeg assembly → one final MP4.

Reuses everything: completed `video_render_jobs` → their `result_asset_id`
(`files` records) → local storage paths, ordered by the existing
`production_nodes.order`, concatenated with FFmpeg into a single MP4 that is
saved back through the existing storage/`files` layer. Video-only (any source
audio is preserved when compatible); no timeline/effects/voice/music.
"""
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List

from fastapi import HTTPException

from core import (
    db, new_id, now_iso, logger, put_object, resolve_object_path,
    get_object, APP_NAME, STORAGE_BACKEND,
)

FFMPEG = os.environ.get("AKASHA_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("AKASHA_FFPROBE", "ffprobe")


def _err(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


def _tool_available(tool: str) -> bool:
    if shutil.which(tool):
        return True
    try:
        subprocess.run([tool, "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def _ffprobe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return round(float(out.stdout.strip()), 3)
    except Exception:
        return 0.0


async def _local_path_for_asset(asset_id: str) -> str:
    """Resolve a completed job's result asset to an absolute local file path.

    Remote-storage objects are materialized to a temp file so FFmpeg can read
    them; local-mode objects resolve directly on disk.
    """
    rec = await db.files.find_one({"id": asset_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise _err(422, "MISSING_CLIP", f"Result asset {asset_id} not found.", asset_id=asset_id)
    storage_path = rec.get("storage_path", "")
    if STORAGE_BACKEND == "local":
        p = resolve_object_path(storage_path)
        if not p or not p.is_file():
            raise _err(422, "MISSING_CLIP", f"Clip file missing on disk for asset {asset_id}.", asset_id=asset_id)
        return str(p)
    # remote: download to a temp file
    try:
        data, _ = get_object(storage_path)
    except Exception:
        raise _err(422, "MISSING_CLIP", f"Clip object unavailable for asset {asset_id}.", asset_id=asset_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.write(data)
    tmp.close()
    return tmp.name


async def _ordered_completed_clips(project_id: str) -> List[Dict[str, Any]]:
    """Return completed (non-cancelled) render jobs in film order; block if unsafe."""
    jobs = await db.video_render_jobs.find({"project_id": project_id}, {"_id": 0}).to_list(10000)
    if not jobs:
        raise _err(422, "NO_COMPLETED_JOBS", "This project has no render jobs to export.")

    # Safety: any non-cancelled job that is not completed blocks the final export.
    blocking = [j for j in jobs if j.get("status") not in ("completed", "cancelled")]
    if blocking:
        raise _err(409, "EXPORT_BLOCKED_INCOMPLETE",
                   "Some render jobs are not completed yet. Finish or cancel them before exporting.",
                   pending=[{"id": j["id"], "status": j.get("status")} for j in blocking[:20]])

    completed = [j for j in jobs if j.get("status") == "completed"]
    if not completed:
        raise _err(422, "NO_COMPLETED_JOBS", "This project has no completed clips to assemble.")

    # Order by the existing production_nodes shot order.
    shots = await db.production_nodes.find(
        {"project_id": project_id, "type": "shot"}, {"_id": 0}).to_list(10000)
    order_by_shot = {s["id"]: s.get("order", 0) for s in shots}

    seen_shots = set()
    resolvable, unresolved = [], []
    for j in completed:
        sid = j.get("shot_id", "")
        if sid and sid in order_by_shot:
            if sid in seen_shots:
                raise _err(409, "DUPLICATE_SHOT",
                           f"More than one completed job maps to shot {sid}.", shot_id=sid)
            seen_shots.add(sid)
            resolvable.append((order_by_shot[sid], j))
        else:
            unresolved.append(j)

    resolvable.sort(key=lambda t: t[0])
    ordered = [j for _, j in resolvable]
    # Fallback for jobs without a resolvable shot: append by creation time.
    ordered += sorted(unresolved, key=lambda j: j.get("created_at", ""))

    for j in ordered:
        if not j.get("result_asset_id"):
            raise _err(422, "MISSING_CLIP", f"Completed job {j['id']} has no result asset.", job_id=j["id"])
    return ordered


def _run_ffmpeg(list_file: str, out_path: str) -> None:
    """Concat via demuxer: try stream copy, fall back to a minimal re-encode."""
    base = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_file]
    copy_cmd = base + ["-c", "copy", "-movflags", "+faststart", out_path]
    r = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=600)
    if r.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return
    logger.info("FFmpeg stream-copy concat failed; re-encoding. stderr: %s", (r.stderr or "")[-400:])
    reencode = base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", out_path]
    r2 = subprocess.run(reencode, capture_output=True, text=True, timeout=1800)
    if r2.returncode != 0 or not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        raise _err(500, "ASSEMBLY_FAILED",
                   "FFmpeg could not assemble the clips into a valid MP4.",
                   detail=(r2.stderr or r.stderr or "")[-400:])


async def assemble_project(project_id: str, output_name: str = "") -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not (_tool_available(FFMPEG) and _tool_available(FFPROBE)):
        raise _err(503, "FFMPEG_NOT_AVAILABLE",
                   "FFmpeg/ffprobe is not available. Install FFmpeg or bundle it with the desktop app.")

    ordered = await _ordered_completed_clips(project_id)
    clip_paths = [await _local_path_for_asset(j["result_asset_id"]) for j in ordered]

    workdir = tempfile.mkdtemp(prefix="akasha_export_")
    tmp_downloads = [p for p in clip_paths if p.startswith(tempfile.gettempdir()) and workdir not in p]
    try:
        list_file = os.path.join(workdir, "clips.txt")
        with open(list_file, "w", encoding="utf-8") as fh:
            for p in clip_paths:
                fh.write(f"file '{p}'\n")  # paths only, never user-derived strings

        out_path = os.path.join(workdir, "final.mp4")
        _run_ffmpeg(list_file, out_path)

        duration = _ffprobe_duration(out_path)
        with open(out_path, "rb") as fh:
            data = fh.read()

        file_id = new_id()
        safe_name = "".join(c for c in (output_name or f"{project.get('name','movie')}") if c.isalnum() or c in (" ", "-", "_")).strip() or "movie"
        filename = f"{safe_name}.mp4"
        storage_path = f"{APP_NAME}/exports/{file_id}.mp4"
        stored = put_object(storage_path, data, "video/mp4")

        record = {
            "id": file_id, "storage_backend": STORAGE_BACKEND,
            "storage_path": stored["path"], "relative_path": stored["path"],
            "original_filename": filename, "content_type": "video/mp4", "mime_type": "video/mp4",
            "size": stored.get("size", len(data)), "size_bytes": stored.get("size", len(data)),
            "category": "exports", "project_id": project_id,
            "kind": "final_movie", "clip_count": len(clip_paths),
            "source_render_job_ids": [j["id"] for j in ordered],
            "duration_seconds": duration, "is_deleted": False, "created_at": now_iso(),
        }
        await db.files.insert_one(dict(record))

        return {
            "status": "completed", "project_id": project_id, "asset_id": file_id,
            "url": f"/api/files/{file_id}", "filename": filename,
            "duration_seconds": duration, "size": record["size"],
            "clip_count": len(clip_paths),
            "clip_asset_ids": [j["result_asset_id"] for j in ordered],  # order for verification
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        for p in tmp_downloads:
            try:
                os.unlink(p)
            except Exception:
                pass
