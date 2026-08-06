"""Project Bible — permanent per-project memory persisted in MongoDB."""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso
from routes import knowledge_sync

router = APIRouter(prefix="/api", tags=["bibles"])

# Available bible types (never hardcoded into UI logic — served to the client).
BIBLE_TYPES = [
    {"type": "story", "label": "Story Bible", "icon": "book-open"},
    {"type": "world", "label": "World Bible", "icon": "globe"},
    {"type": "style", "label": "Style Bible", "icon": "palette"},
    {"type": "camera", "label": "Camera Bible", "icon": "camera"},
    {"type": "music", "label": "Music Bible", "icon": "music"},
    {"type": "publishing", "label": "Publishing Bible", "icon": "send"},
    {"type": "brand", "label": "Brand Bible", "icon": "sparkles"},
]
_VALID = {b["type"] for b in BIBLE_TYPES}


class Section(BaseModel):
    id: str = Field(default_factory=new_id)
    heading: str = ""
    content: str = ""


class Bible(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    type: str
    sections: List[Section] = Field(default_factory=list)
    updated_at: str = Field(default_factory=now_iso)


class BibleUpdate(BaseModel):
    sections: List[Section]


@router.get("/bible-types")
async def bible_types():
    return BIBLE_TYPES


@router.get("/projects/{project_id}/bibles")
async def list_bibles(project_id: str):
    docs = await db.bibles.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    by_type = {d["type"]: d for d in docs}
    result = []
    for b in BIBLE_TYPES:
        existing = by_type.get(b["type"])
        result.append({
            **b,
            "filled": bool(existing and existing.get("sections")),
            "sections_count": len(existing["sections"]) if existing else 0,
        })
    return result


@router.get("/projects/{project_id}/bibles/{bible_type}", response_model=Bible)
async def get_bible(project_id: str, bible_type: str):
    if bible_type not in _VALID:
        raise HTTPException(status_code=400, detail="Unknown bible type")
    doc = await db.bibles.find_one({"project_id": project_id, "type": bible_type}, {"_id": 0})
    if not doc:
        return Bible(project_id=project_id, type=bible_type)
    return doc


@router.put("/projects/{project_id}/bibles/{bible_type}", response_model=Bible)
async def update_bible(project_id: str, bible_type: str, body: BibleUpdate):
    if bible_type not in _VALID:
        raise HTTPException(status_code=400, detail="Unknown bible type")
    existing = await db.bibles.find_one({"project_id": project_id, "type": bible_type}, {"_id": 0})
    bible = Bible(
        id=existing["id"] if existing else new_id(),
        project_id=project_id,
        type=bible_type,
        sections=[s.model_dump() for s in body.sections],
    )
    await db.bibles.update_one(
        {"project_id": project_id, "type": bible_type},
        {"$set": bible.model_dump()},
        upsert=True,
    )
    await knowledge_sync.sync_bible(bible.model_dump())
    return bible


@router.delete("/projects/{project_id}/bibles/{bible_type}")
async def delete_bible(project_id: str, bible_type: str):
    if bible_type not in _VALID:
        raise HTTPException(status_code=400, detail="Unknown bible type")
    doc = await db.bibles.find_one({"project_id": project_id, "type": bible_type}, {"_id": 0})
    res = await db.bibles.delete_one({"project_id": project_id, "type": bible_type})
    if doc:
        await knowledge_sync.remove_bible(project_id, doc["id"])
    return {"ok": True, "deleted": res.deleted_count}
