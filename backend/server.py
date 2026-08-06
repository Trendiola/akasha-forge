from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso, init_storage, logger
from routes import (
    files as files_route,
    characters as characters_route,
    bibles as bibles_route,
    providers_hub,
    brain as brain_route,
    production as production_route,
    publish as publish_route,
    image_edit as image_edit_route,
    forge_items as forge_items_route,
    video_jobs as video_jobs_route,
)

app = FastAPI(title="Akasha Forge API")
api_router = APIRouter(prefix="/api")


# ----------------------------- Projects -----------------------------
class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    type: str = "story"
    status: str = "active"
    color: str = "#6D3BFF"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    type: str = "story"
    color: str = "#6D3BFF"
    tags: List[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "global"
    general: Dict[str, Any] = Field(default_factory=dict)
    appearance: Dict[str, Any] = Field(default_factory=dict)
    language: Dict[str, Any] = Field(default_factory=dict)
    publishing: Dict[str, Any] = Field(default_factory=dict)
    storage: Dict[str, Any] = Field(default_factory=dict)
    shortcuts: Dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=now_iso)


DEFAULT_SETTINGS = {
    "id": "global",
    "general": {"autosave": True, "telemetry": False, "startupModule": "akasha-core"},
    "appearance": {"theme": "dark", "accent": "#6D3BFF", "density": "comfortable", "sidebarCollapsed": False},
    "language": {"uiLanguage": "en", "defaultTargets": ["es", "fr", "de", "ja"]},
    "publishing": {"defaultPlatforms": []},
    "storage": {"location": "local", "cacheLimitGb": 10},
    "shortcuts": {"commandPalette": "Ctrl+K", "search": "Ctrl+F"},
    "updated_at": now_iso(),
}


@api_router.get("/")
async def root():
    return {"message": "Akasha Forge API", "status": "online", "version": "2.0"}


@api_router.get("/projects", response_model=List[Project])
async def list_projects():
    return await db.projects.find({}, {"_id": 0}).sort("updated_at", -1).to_list(1000)


@api_router.post("/projects", response_model=Project)
async def create_project(body: ProjectCreate):
    project = Project(**body.model_dump())
    await db.projects.insert_one(project.model_dump())
    return project


@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    doc = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    return doc


@api_router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, body: ProjectUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    res = await db.projects.update_one({"id": project_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return await db.projects.find_one({"id": project_id}, {"_id": 0})


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    res = await db.projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    # cascade project-scoped data
    char_ids = [c["id"] async for c in db.characters.find({"project_id": project_id}, {"_id": 0, "id": 1})]
    if char_ids:
        await db.character_versions.delete_many({"character_id": {"$in": char_ids}})
    for coll in ("characters", "bibles", "production_nodes", "image_jobs", "forge_items", "knowledge_items"):
        await db[coll].delete_many({"project_id": project_id})
    return {"ok": True}


# ----------------------------- Settings -----------------------------
@api_router.get("/settings", response_model=Settings)
async def get_settings():
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return doc or Settings(**DEFAULT_SETTINGS)


@api_router.put("/settings", response_model=Settings)
async def update_settings(body: Dict[str, Any]):
    existing = await db.settings.find_one({"id": "global"}, {"_id": 0}) or {}
    merged = dict(existing)
    for key, value in body.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    merged["updated_at"] = now_iso()
    merged["id"] = "global"
    await db.settings.update_one({"id": "global"}, {"$set": merged}, upsert=True)
    return await db.settings.find_one({"id": "global"}, {"_id": 0})


# ----------------------------- Wire routers -----------------------------
app.include_router(api_router)
app.include_router(files_route.router)
app.include_router(characters_route.router)
app.include_router(bibles_route.router)
app.include_router(providers_hub.router)
app.include_router(brain_route.router)
app.include_router(production_route.router)
app.include_router(publish_route.router)
app.include_router(image_edit_route.router)
app.include_router(forge_items_route.router)
app.include_router(video_jobs_route.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.on_event("startup")
async def on_startup():
    await db.projects.create_index("id", unique=True)
    await providers_hub.seed_providers()
    await brain_route.ensure_knowledge_indexes()
    await video_jobs_route.ensure_video_indexes()
    if await db.settings.count_documents({"id": "global"}) == 0:
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as exc:
        logger.warning("Storage init deferred: %s", exc)


@app.on_event("shutdown")
async def on_shutdown():
    from core import client
    client.close()
