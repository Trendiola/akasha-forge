"""Image Forge AI Editing — provider-independent service interfaces (no inference yet)."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso

router = APIRouter(prefix="/api/image", tags=["image-edit"])

OPERATIONS = [
    {"id": "object_removal", "label": "Object Removal", "icon": "eraser", "params": ["mask"]},
    {"id": "background_replacement", "label": "Background Replacement", "icon": "layers", "params": ["prompt"]},
    {"id": "inpainting", "label": "Inpainting", "icon": "brush", "params": ["mask", "prompt"]},
    {"id": "outpainting", "label": "Outpainting", "icon": "maximize", "params": ["direction", "prompt"]},
    {"id": "upscaling", "label": "Upscaling", "icon": "scaling", "params": ["scale"]},
]
_VALID_OPS = {o["id"] for o in OPERATIONS}


class EditJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: Optional[str] = None
    operation: str
    source_file_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    provider_id: Optional[str] = None
    provider_name: str = ""
    status: str = "queued"       # queued | processing | done | error
    result_file_id: Optional[str] = None
    message: str = ""
    created_at: str = Field(default_factory=now_iso)


class EditJobCreate(BaseModel):
    operation: str
    source_file_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None


@router.get("/operations")
async def operations():
    return OPERATIONS


@router.post("/jobs", response_model=EditJob)
async def create_job(body: EditJobCreate):
    if body.operation not in _VALID_OPS:
        raise HTTPException(status_code=400, detail="Unknown operation")
    # provider-independent: resolve the enabled default image provider (or highest priority)
    provider = await db.providers.find_one(
        {"category": "image", "enabled": True, "is_default": True}, {"_id": 0}
    ) or await db.providers.find_one(
        {"category": "image", "enabled": True}, {"_id": 0}, sort=[("priority", 1)]
    )
    job = EditJob(
        operation=body.operation,
        source_file_id=body.source_file_id,
        params=body.params,
        project_id=body.project_id,
        provider_id=provider["id"] if provider else None,
        provider_name=provider["name"] if provider else "",
        status="queued" if provider else "error",
        message="" if provider else "No enabled image provider. Configure one in Provider Hub.",
    )
    await db.image_jobs.insert_one(job.model_dump())
    return job


@router.get("/jobs", response_model=List[EditJob])
async def list_jobs(project_id: Optional[str] = None):
    query = {"project_id": project_id} if project_id else {}
    return await db.image_jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    await db.image_jobs.delete_one({"id": job_id})
    return {"ok": True}
