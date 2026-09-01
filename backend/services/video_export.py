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
import re
from typing import Any, Dict, List

from fastapi import HTTPException

from core import (
    db, new_id, now_iso, logger, put_object, resolve_object_path,
    get_object, APP_NAME, STORAGE_BACKEND,
)

def _resolve_ffmpeg() -> str:
    """ffmpeg: env override → system PATH → pip-bundled static binary (survives
    container resets where apt's ffmpeg is wiped)."""
    env = os.environ.get("AKASHA_FFMPEG")
    if env:
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = _resolve_ffmpeg()
FFPROBE = os.environ.get("AKASHA_FFPROBE") or shutil.which("ffprobe") or "ffprobe"


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
        value = float(out.stdout.strip())
        if value > 0:
            return round(value, 3)
    except Exception:
        pass
    # Some desktop installations expose ffmpeg before ffprobe (and the
    # imageio fallback contains ffmpeg only). Its metadata output still gives
    # an accurate duration, so do not report a false zero.
    try:
        out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True, timeout=30)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out.stderr or "")
        if match:
            hours, minutes, seconds = match.groups()
            return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)
    except Exception:
        pass
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


def _srt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def _build_srt(project_id: str, ordered: List[Dict[str, Any]]) -> str:
    """Build an SRT from existing shot narration text + clip order/duration."""
    shots = await db.production_nodes.find(
        {"project_id": project_id, "type": "shot"}, {"_id": 0}).to_list(10000)
    shot_by_id = {s["id"]: s for s in shots}
    cues, clock, idx = [], 0.0, 1
    for j in ordered:
        node = shot_by_id.get(j.get("shot_id", ""), {})
        dur = float(node.get("duration_seconds") or j.get("duration_seconds") or 8)
        text = (j.get("narration_text") or node.get("narration_text") or "").strip()
        if text:
            cues.append(f"{idx}\n{_srt_ts(clock)} --> {_srt_ts(clock + dur)}\n{text}\n")
            idx += 1
        clock += dur
    return "\n".join(cues)


async def _store_srt(project_id: str, srt_text: str) -> str:
    file_id = new_id()
    path = f"{APP_NAME}/exports/{file_id}.srt"
    data = srt_text.encode("utf-8")
    stored = put_object(path, data, "application/x-subrip")
    record = {
        "id": file_id, "storage_backend": STORAGE_BACKEND,
        "storage_path": stored["path"], "relative_path": stored["path"],
        "original_filename": f"{file_id}.srt", "content_type": "application/x-subrip",
        "mime_type": "application/x-subrip", "size": stored.get("size", len(data)),
        "size_bytes": stored.get("size", len(data)), "category": "documents",
        "project_id": project_id, "kind": "subtitles", "is_deleted": False, "created_at": now_iso(),
    }
    await db.files.insert_one(dict(record))
    return file_id


def _mux_audio(video: str, narration: str, music: str, out_path: str) -> None:
    """Mux narration/music onto the assembled video (video stream copied)."""
    cmd = [FFMPEG, "-y", "-i", video]
    if narration:
        cmd += ["-i", narration]
    if music:
        cmd += ["-i", music]
    if narration and music:
        # Narration full volume; music ducked so dialogue stays intelligible.
        cmd += ["-filter_complex",
                "[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=longest[a]",
                "-map", "0:v:0", "-map", "[a]"]
    elif narration:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    else:  # music only
        cmd += ["-filter_complex", "[1:a]volume=0.6[a]", "-map", "0:v:0", "-map", "[a]"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        raise _err(500, "ASSEMBLY_FAILED", "FFmpeg could not mux audio into the movie.",
                   detail=(r.stderr or "")[-400:])


def _mux_subs(video: str, srt: str, out_path: str) -> bool:
    """Best-effort selectable subtitle track (mov_text). Returns success."""
    cmd = [FFMPEG, "-y", "-i", video, "-i", srt, "-map", "0", "-map", "1",
           "-c", "copy", "-c:s", "mov_text", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0



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


async def assemble_project(project_id: str, output_name: str = "",
                           narration_asset_id: str = "", music_asset_id: str = "",
                           subtitles: bool = False) -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _tool_available(FFMPEG):
        raise _err(503, "FFMPEG_NOT_AVAILABLE",
                   "FFmpeg is not available. Install FFmpeg or bundle it with the desktop app.")

    ordered = await _ordered_completed_clips(project_id)
    clip_paths = [await _local_path_for_asset(j["result_asset_id"]) for j in ordered]

    workdir = tempfile.mkdtemp(prefix="akasha_export_")
    tmp_downloads = [p for p in clip_paths if p.startswith(tempfile.gettempdir()) and workdir not in p]
    try:
        list_file = os.path.join(workdir, "clips.txt")
        with open(list_file, "w", encoding="utf-8") as fh:
            for p in clip_paths:
                fh.write(f"file '{p}'\n")  # paths only, never user-derived strings

        out_path = os.path.join(workdir, "concat.mp4")
        _run_ffmpeg(list_file, out_path)

        # --- AF-PRODUCTION-001: optional audio mux + subtitles (video-only if none) ---
        final_media = out_path
        subtitle_asset_id = ""
        narration_path = await _local_path_for_asset(narration_asset_id) if narration_asset_id else None
        music_path = await _local_path_for_asset(music_asset_id) if music_asset_id else None
        if narration_path or music_path:
            muxed = os.path.join(workdir, "muxed.mp4")
            _mux_audio(out_path, narration_path, music_path, muxed)
            final_media = muxed

        srt_text = ""
        if subtitles:
            srt_text = await _build_srt(project_id, ordered)
            if srt_text.strip():
                srt_path = os.path.join(workdir, "subs.srt")
                with open(srt_path, "w", encoding="utf-8") as fh:
                    fh.write(srt_text)
                subbed = os.path.join(workdir, "subbed.mp4")
                if _mux_subs(final_media, srt_path, subbed):
                    final_media = subbed  # selectable mov_text track
                subtitle_asset_id = await _store_srt(project_id, srt_text)

        out_path = final_media
        duration = _ffprobe_duration(out_path)
        with open(out_path, "rb") as fh:
            data = fh.read()

        file_id = new_id()
        safe_name = "".join(c for c in (output_name or f"{project.get('name','movie')}") if c.isalnum() or c in (" ", "-", "_")).strip() or "movie"
        filename = f"{safe_name}.mp4"
        storage_path = f"{APP_NAME}/exports/{file_id}.mp4"
        stored = put_object(storage_path, data, "video/mp4")

        has_audio = bool(narration_path or music_path)
        record = {
            "id": file_id, "storage_backend": STORAGE_BACKEND,
            "storage_path": stored["path"], "relative_path": stored["path"],
            "original_filename": filename, "content_type": "video/mp4", "mime_type": "video/mp4",
            "size": stored.get("size", len(data)), "size_bytes": stored.get("size", len(data)),
            "category": "exports", "project_id": project_id,
            "kind": "final_movie", "clip_count": len(clip_paths),
            "source_render_job_ids": [j["id"] for j in ordered],
            "duration_seconds": duration, "has_audio": has_audio,
            "narration_asset_id": narration_asset_id or "", "music_asset_id": music_asset_id or "",
            "subtitle_asset_id": subtitle_asset_id, "is_deleted": False, "created_at": now_iso(),
        }
        await db.files.insert_one(dict(record))

        return {
            "status": "completed", "project_id": project_id, "asset_id": file_id,
            "url": f"/api/files/{file_id}", "filename": filename,
            "duration_seconds": duration, "size": record["size"],
            "clip_count": len(clip_paths), "has_audio": has_audio,
            "subtitle_asset_id": subtitle_asset_id,
            "clip_asset_ids": [j["result_asset_id"] for j in ordered],  # order for verification
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        for p in tmp_downloads:
            try:
                os.unlink(p)
            except Exception:
                pass
