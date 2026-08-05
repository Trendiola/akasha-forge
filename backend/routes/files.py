"""File upload & serving (object storage backed)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from core import db, put_object, get_object, new_id, now_iso, APP_NAME

router = APIRouter(prefix="/api/files", tags=["files"])

MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("general")):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    content_type = file.content_type or MIME.get(ext, "application/octet-stream")
    file_id = new_id()
    path = f"{APP_NAME}/{category}/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, content_type)
    record = {
        "id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "category": category,
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
    data, content_type = get_object(record["storage_path"])
    return Response(content=data, media_type=record.get("content_type", content_type))
