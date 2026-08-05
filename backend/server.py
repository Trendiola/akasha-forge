from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Akasha Forge API")
api_router = APIRouter(prefix="/api")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ----------------------------- Models -----------------------------
class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    type: str = "story"          # story | film | game | album | book
    status: str = "active"       # active | archived | draft
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


class Provider(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    name: str
    category: str                # llm | image | video | voice | music | translation | publishing
    kind: str = "api"            # api | local | plugin
    base_url: str = ""
    enabled: bool = False
    is_default: bool = False
    models: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ProviderCreate(BaseModel):
    name: str
    category: str
    kind: str = "api"
    base_url: str = ""
    models: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    models: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


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


DEFAULT_PROVIDERS = [
    {"name": "OpenAI", "category": "llm", "base_url": "https://api.openai.com/v1", "models": ["gpt-5.4", "gpt-5.4-mini"]},
    {"name": "Anthropic", "category": "llm", "base_url": "https://api.anthropic.com", "models": ["claude-sonnet-4.6"]},
    {"name": "Google Gemini", "category": "llm", "base_url": "https://generativelanguage.googleapis.com", "models": ["gemini-3.1-pro"]},
    {"name": "Stable Diffusion", "category": "image", "base_url": "", "models": ["sdxl"]},
    {"name": "Runway", "category": "video", "base_url": "https://api.runwayml.com", "models": ["gen-3"]},
    {"name": "ElevenLabs", "category": "voice", "base_url": "https://api.elevenlabs.io", "models": ["multilingual-v2"]},
    {"name": "Suno", "category": "music", "base_url": "", "models": ["v4"]},
    {"name": "DeepL", "category": "translation", "base_url": "https://api.deepl.com", "models": []},
]

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


# ----------------------------- Routes -----------------------------
@api_router.get("/")
async def root():
    return {"message": "Akasha Forge API", "status": "online"}


# Projects
@api_router.get("/projects", response_model=List[Project])
async def list_projects():
    docs = await db.projects.find({}, {"_id": 0}).sort("updated_at", -1).to_list(1000)
    return docs


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
    doc = await db.projects.find_one({"id": project_id}, {"_id": 0})
    return doc


@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    res = await db.projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


# Providers
@api_router.get("/providers", response_model=List[Provider])
async def list_providers(category: Optional[str] = None):
    query = {"category": category} if category else {}
    docs = await db.providers.find(query, {"_id": 0}).to_list(1000)
    return docs


@api_router.post("/providers", response_model=Provider)
async def create_provider(body: ProviderCreate):
    provider = Provider(**body.model_dump())
    await db.providers.insert_one(provider.model_dump())
    return provider


@api_router.put("/providers/{provider_id}", response_model=Provider)
async def update_provider(provider_id: str, body: ProviderUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    if updates.get("is_default"):
        target = await db.providers.find_one({"id": provider_id}, {"_id": 0})
        if target:
            await db.providers.update_many(
                {"category": target["category"]}, {"$set": {"is_default": False}}
            )
    res = await db.providers.update_one({"id": provider_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    doc = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    return doc


@api_router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    res = await db.providers.delete_one({"id": provider_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"ok": True}


# Settings
@api_router.get("/settings", response_model=Settings)
async def get_settings():
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        return Settings(**DEFAULT_SETTINGS)
    return doc


@api_router.put("/settings", response_model=Settings)
async def update_settings(body: Dict[str, Any]):
    body["updated_at"] = now_iso()
    body["id"] = "global"
    await db.settings.update_one({"id": "global"}, {"$set": body}, upsert=True)
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return doc


@app.on_event("startup")
async def seed_defaults():
    if await db.providers.count_documents({}) == 0:
        providers = [Provider(**p).model_dump() for p in DEFAULT_PROVIDERS]
        await db.providers.insert_many(providers)
        logger.info("Seeded %d default providers", len(providers))
    if await db.settings.count_documents({"id": "global"}) == 0:
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
        logger.info("Seeded default settings")


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
