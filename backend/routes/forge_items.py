"""Generic Forge CRUD — one reusable persistence layer for all Forge modules.

A single `forge_items` collection stores records for every module/kind
(story chapters, world locations, video scenes/shots, voice profiles,
music briefs, workflow graphs, image galleries/assets, etc.). This avoids
duplicating CRUD logic per module.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso

router = APIRouter(prefix="/api", tags=["forge"])


class ForgeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    module: str
    kind: str
    title: str = "Untitled"
    data: Dict[str, Any] = Field(default_factory=dict)
    order: int = 0
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ForgeItemCreate(BaseModel):
    kind: str
    title: str = "Untitled"
    data: Dict[str, Any] = Field(default_factory=dict)


class ForgeItemUpdate(BaseModel):
    title: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    order: Optional[int] = None


@router.get("/projects/{project_id}/forge/{module}", response_model=List[ForgeItem])
async def list_items(project_id: str, module: str, kind: Optional[str] = None):
    query: Dict[str, Any] = {"project_id": project_id, "module": module}
    if kind:
        query["kind"] = kind
    return await db.forge_items.find(query, {"_id": 0}).sort([("order", 1), ("created_at", 1)]).to_list(2000)


@router.post("/projects/{project_id}/forge/{module}", response_model=ForgeItem)
async def create_item(project_id: str, module: str, body: ForgeItemCreate):
    count = await db.forge_items.count_documents({"project_id": project_id, "module": module, "kind": body.kind})
    item = ForgeItem(project_id=project_id, module=module, kind=body.kind, title=body.title or "Untitled", data=body.data, order=count)
    await db.forge_items.insert_one(item.model_dump())
    return item


@router.get("/forge-items/{item_id}", response_model=ForgeItem)
async def get_item(item_id: str):
    doc = await db.forge_items.find_one({"id": item_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return doc


@router.put("/forge-items/{item_id}", response_model=ForgeItem)
async def update_item(item_id: str, body: ForgeItemUpdate):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = now_iso()
    res = await db.forge_items.update_one({"id": item_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return await db.forge_items.find_one({"id": item_id}, {"_id": 0})


@router.delete("/forge-items/{item_id}")
async def delete_item(item_id: str):
    res = await db.forge_items.delete_one({"id": item_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}
