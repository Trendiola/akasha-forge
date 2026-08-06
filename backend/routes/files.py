"""File upload & serving (provider-neutral storage backed: remote or local)."""
import hashlib
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from core import (
    db, put_object, get_object_stream, delete_object, new_id, now_iso, APP_NAME, STORAGE_BACKEND,
)

router = APIRouter(prefix="/api/files", tags=["files"])

MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    "mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime",
    "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg", "m4a": "audio/mp4", "flac": "audio/flac",
    "pdf": "application/pdf", "txt": "text/plain", "json": "application/json",
}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("general"), project_id: str = Form("")):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    content_type = file.content_type or MIME.get(ext, "application/octet-stream")
    file_id = new_id()
    path = f"{APP_NAME}/{category}/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, content_type)
    record = {
        "id": file_id,
        "storage_backend": STORAGE_BACKEND,
        "storage_path": result["path"],
        "relative_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "mime_type": content_type,
        "size": result.get("size", len(data)),
        "size_bytes": result.get("size", len(data)),
        "category": category,
        "project_id": project_id or "",
        "checksum": hashlib.sha256(data).hexdigest(),
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(dict(record))
    record.pop("_id", None)
    record["url"] = f"/api/files/{file_id}"
    return record


@router.get("/{file_id}")
async def serve_file(file_id: str):
    record = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        stream, content_type = get_object_stream(record["storage_path"])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception:
        # remote-only asset unavailable in local mode, or transient storage error
        raise HTTPException(status_code=404, detail="File is unavailable in the current storage mode")
    return StreamingResponse(stream, media_type=record.get("content_type") or content_type)


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    record = await db.files.find_one({"id": file_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    removed = False
    try:
        removed = delete_object(record["storage_path"])
    except Exception:
        removed = False
    await db.files.update_one({"id": file_id}, {"$set": {"is_deleted": True, "deleted_at": now_iso()}})
    return {"ok": True, "deleted": file_id, "object_removed": removed}
