"""Scene Production System — architecture only: Project → Acts → Chapters → Scenes → Shots."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso

router = APIRouter(prefix="/api", tags=["production"])

HIERARCHY = ["act", "chapter", "scene", "shot"]
_CHILD = {"act": "chapter", "chapter": "scene", "scene": "shot", "shot": None}


class Node(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    type: str
    parent_id: Optional[str] = None
    title: str
    description: str = ""
    status: str = "draft"      # draft | in_progress | ready | locked
    order: int = 0
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class NodeCreate(BaseModel):
    type: str
    parent_id: Optional[str] = None
    title: str
    description: str = ""


class NodeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    order: Optional[int] = None


def _build_tree(nodes: List[dict]) -> List[dict]:
    by_parent = {}
    for n in nodes:
        by_parent.setdefault(n.get("parent_id"), []).append(n)
    for group in by_parent.values():
        group.sort(key=lambda x: (x.get("order", 0), x.get("created_at", "")))

    def children(parent_id):
        result = []
        for n in by_parent.get(parent_id, []):
            result.append({**n, "children": children(n["id"])})
        return result

    return children(None)


@router.get("/projects/{project_id}/production")
async def get_production(project_id: str):
    nodes = await db.production_nodes.find({"project_id": project_id}, {"_id": 0}).to_list(5000)
    return {"tree": _build_tree(nodes), "count": len(nodes), "hierarchy": HIERARCHY}


@router.post("/projects/{project_id}/production", response_model=Node)
async def create_node(project_id: str, body: NodeCreate):
    if body.type not in HIERARCHY:
        raise HTTPException(status_code=400, detail="Invalid node type")
    count = await db.production_nodes.count_documents({"project_id": project_id, "parent_id": body.parent_id})
    node = Node(project_id=project_id, order=count, **body.model_dump())
    await db.production_nodes.insert_one(node.model_dump())
    return node


@router.put("/production/{node_id}", response_model=Node)
async def update_node(node_id: str, body: NodeUpdate):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = now_iso()
    res = await db.production_nodes.update_one({"id": node_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    return await db.production_nodes.find_one({"id": node_id}, {"_id": 0})


@router.delete("/production/{node_id}")
async def delete_node(node_id: str):
    # cascade delete descendants
    to_delete = [node_id]
    frontier = [node_id]
    while frontier:
        children = await db.production_nodes.find({"parent_id": {"$in": frontier}}, {"_id": 0, "id": 1}).to_list(5000)
        ids = [c["id"] for c in children]
        to_delete.extend(ids)
        frontier = ids
    await db.production_nodes.delete_many({"id": {"$in": to_delete}})
    return {"ok": True, "deleted": len(to_delete)}
