"""Provider Hub — production-ready, adapter-based provider management.

Providers are never hardcoded in the UI. New providers/categories can be added
by registering an adapter without modifying existing code.
"""
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso, encrypt, decrypt, mask_key, logger

router = APIRouter(prefix="/api", tags=["providers"])

# ----------------------------- Capability framework -----------------------------
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_CONFIGURED = "configured"
STATUS_READY = "ready"
STATUS_ERROR = "error"
STATUS_DISABLED = "disabled"

PROVIDER_CATEGORIES = [
    {"id": "llm", "label": "Language Models", "features": ["chat", "completion", "vision", "function-calling", "streaming"]},
    {"id": "image", "label": "Image", "features": ["generation", "inpainting", "outpainting", "upscaling", "style-transfer"]},
    {"id": "video", "label": "Video", "features": ["text-to-video", "image-to-video", "upscaling"]},
    {"id": "voice", "label": "Voice", "features": ["tts", "stt", "voice-cloning"]},
    {"id": "music", "label": "Music", "features": ["generation", "stems"]},
    {"id": "translation", "label": "Translation", "features": ["text", "glossary", "tone-control"]},
    {"id": "publishing", "label": "Publishing", "features": ["schedule", "analytics", "multi-account"]},
]
_FEATURES = {c["id"]: c["features"] for c in PROVIDER_CATEGORIES}


class ProviderAdapter:
    """Adapter interface. Subclass + register to support new providers/categories.

    validate() performs a LIGHTWEIGHT, LOCAL check only — no expensive inference.
    Later this can be extended to hit provider-specific auth/health endpoints.
    """
    def validate(self, api_key: str, base_url: str) -> Dict[str, Any]:
        key = (api_key or "").strip()
        if len(key) < 12:
            return {"ok": False, "message": "API key looks too short to be valid."}
        if " " in key or "\n" in key:
            return {"ok": False, "message": "API key must not contain whitespace."}
        return {"ok": True, "message": "Key format validated locally. Ready."}


_ADAPTERS: Dict[str, ProviderAdapter] = {}
_DEFAULT_ADAPTER = ProviderAdapter()


def register_adapter(category: str, adapter: ProviderAdapter):
    _ADAPTERS[category] = adapter


def get_adapter(category: str) -> ProviderAdapter:
    return _ADAPTERS.get(category, _DEFAULT_ADAPTER)


# ----------------------------- Models -----------------------------
class Provider(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    name: str
    category: str
    kind: str = "api"
    base_url: str = ""
    models: List[str] = Field(default_factory=list)
    default_model: str = ""
    organization_id: str = ""
    notes: str = ""
    enabled: bool = False
    is_default: bool = False
    priority: int = 100
    status: str = STATUS_NOT_CONFIGURED
    error_message: str = ""
    features: List[str] = Field(default_factory=list)
    supported_features: List[str] = Field(default_factory=list)
    api_key_encrypted: str = ""
    last_validated: str = ""
    last_test_ms: int = 0
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ProviderCreate(BaseModel):
    name: str
    category: str
    kind: str = "api"
    base_url: str = ""
    models: List[str] = Field(default_factory=list)
    default_model: str = ""
    organization_id: str = ""
    notes: str = ""
    api_key: str = ""
    enabled: bool = False


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    models: Optional[List[str]] = None
    default_model: Optional[str] = None
    organization_id: Optional[str] = None
    notes: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = None
    features: Optional[List[str]] = None
    api_key: Optional[str] = None


def _public(doc: dict) -> dict:
    """Strip secrets; expose masked key + configured flag."""
    d = dict(doc)
    enc = d.pop("api_key_encrypted", "")
    d["configured"] = bool(enc)
    d["api_key_masked"] = mask_key(decrypt(enc)) if enc else ""
    d["supported_features"] = _FEATURES.get(d.get("category", ""), [])
    return d


def _derive_status(doc: dict) -> str:
    if not doc.get("enabled", False):
        return STATUS_DISABLED
    if not doc.get("api_key_encrypted"):
        return STATUS_NOT_CONFIGURED
    # keep ready/error if previously validated, else configured
    if doc.get("status") in (STATUS_READY, STATUS_ERROR):
        return doc["status"]
    return STATUS_CONFIGURED


# ----------------------------- Routes -----------------------------
@router.get("/provider-categories")
async def provider_categories():
    return PROVIDER_CATEGORIES


@router.get("/providers")
async def list_providers(category: Optional[str] = None):
    query = {"category": category} if category else {}
    docs = await db.providers.find(query, {"_id": 0}).sort([("priority", 1), ("name", 1)]).to_list(1000)
    return [_public(d) for d in docs]


@router.post("/providers")
async def create_provider(body: ProviderCreate):
    provider = Provider(
        name=body.name, category=body.category, kind=body.kind,
        base_url=body.base_url, models=body.models,
        default_model=body.default_model, organization_id=body.organization_id,
        notes=body.notes, enabled=body.enabled,
        supported_features=_FEATURES.get(body.category, []),
    )
    if body.api_key:
        provider.api_key_encrypted = encrypt(body.api_key)
    doc = provider.model_dump()
    doc["status"] = _derive_status(doc)
    await db.providers.insert_one(dict(doc))
    return _public(doc)


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, body: ProviderUpdate):
    existing = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Provider not found")
    updates: Dict[str, Any] = {}
    payload = body.model_dump(exclude_none=True)
    if "api_key" in payload:
        updates["api_key_encrypted"] = encrypt(payload.pop("api_key"))
    updates.update(payload)
    updates["updated_at"] = now_iso()

    if updates.get("is_default"):
        await db.providers.update_many({"category": existing["category"]}, {"$set": {"is_default": False}})

    merged = {**existing, **updates}
    merged["status"] = _derive_status(merged)
    updates["status"] = merged["status"]

    await db.providers.update_one({"id": provider_id}, {"$set": updates})
    doc = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    return _public(doc)


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    res = await db.providers.delete_one({"id": provider_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    # Forward-compat (AF-DESKTOP-007): best-effort removal of any optional vault
    # entry for this provider. Never blocks deletion; never logs the secret value.
    try:
        import secret_vault
        secret_vault.delete_secret(secret_vault.provider_key_name(provider_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vault cleanup skipped for provider %s: %s", provider_id, exc)
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str):
    doc = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Provider not found")

    start = time.perf_counter()
    if not doc.get("enabled", False):
        result = {"status": STATUS_DISABLED, "message": "Provider is disabled. Enable it to test."}
    elif not doc.get("api_key_encrypted"):
        result = {"status": STATUS_NOT_CONFIGURED, "message": "No API key configured."}
    else:
        adapter = get_adapter(doc["category"])
        key = decrypt(doc["api_key_encrypted"])
        check = adapter.validate(key, doc.get("base_url", ""))
        result = {
            "status": STATUS_READY if check["ok"] else STATUS_ERROR,
            "message": check["message"],
        }
    response_ms = max(1, round((time.perf_counter() - start) * 1000))
    result["response_ms"] = response_ms

    await db.providers.update_one(
        {"id": provider_id},
        {"$set": {
            "status": result["status"],
            "error_message": "" if result["status"] == STATUS_READY else result["message"],
            "last_validated": now_iso(),
            "last_test_ms": response_ms,
        }},
    )
    doc = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    return {**result, "provider": _public(doc)}


# ----------------------------- Catalog -----------------------------
PROVIDER_CATALOG = [
    {"name": "OpenAI", "category": "llm", "base_url": "https://api.openai.com/v1", "models": ["GPT-5.5", "GPT-5.4", "GPT-5.4 Mini"]},
    {"name": "Google Gemini", "category": "llm", "base_url": "https://generativelanguage.googleapis.com", "models": ["Gemini 3", "Gemini 3.1 Pro", "Gemini 3 Flash"]},
    {"name": "Anthropic Claude", "category": "llm", "base_url": "https://api.anthropic.com", "models": ["Claude Opus", "Claude Sonnet", "Claude Haiku"]},
    {"name": "ElevenLabs", "category": "voice", "base_url": "https://api.elevenlabs.io", "models": ["ElevenLabs v3", "Multilingual v2"]},
    {"name": "Suno", "category": "music", "base_url": "https://api.suno.ai", "models": ["Suno v5.5", "Suno v4"]},
    {"name": "Runway", "category": "video", "base_url": "https://api.runwayml.com", "models": ["Gen-3", "Gen-2"]},
    {"name": "Veo", "category": "video", "base_url": "https://generativelanguage.googleapis.com", "models": ["Veo 3.1", "Veo 3"]},
    {"name": "Kling", "category": "video", "base_url": "https://api.klingai.com", "models": ["Kling 3", "Kling 2"]},
    {"name": "Fal", "category": "image", "base_url": "https://fal.run", "models": ["flux-pro", "flux-dev"]},
    {"name": "Replicate", "category": "image", "base_url": "https://api.replicate.com", "models": ["flux", "sdxl"]},
    {"name": "Stability AI", "category": "image", "base_url": "https://api.stability.ai", "models": ["SD 3.5", "SDXL"]},
]


@router.get("/provider-catalog")
async def provider_catalog():
    return PROVIDER_CATALOG


# ----------------------------- Seed -----------------------------
DEFAULT_PROVIDERS = [
    {"name": "OpenAI", "category": "llm", "base_url": "https://api.openai.com/v1", "models": ["gpt-5.4", "gpt-5.4-mini"], "priority": 10},
    {"name": "Anthropic", "category": "llm", "base_url": "https://api.anthropic.com", "models": ["claude-sonnet-4-6"], "priority": 20},
    {"name": "Google Gemini", "category": "llm", "base_url": "https://generativelanguage.googleapis.com", "models": ["gemini-3.1-pro"], "priority": 30},
    {"name": "Stable Diffusion", "category": "image", "base_url": "", "models": ["sdxl"], "priority": 10},
    {"name": "Runway", "category": "video", "base_url": "https://api.runwayml.com", "models": ["gen-3"], "priority": 10},
    {"name": "ElevenLabs", "category": "voice", "base_url": "https://api.elevenlabs.io", "models": ["multilingual-v2"], "priority": 10},
    {"name": "Suno", "category": "music", "base_url": "", "models": ["v4"], "priority": 10},
    {"name": "DeepL", "category": "translation", "base_url": "https://api.deepl.com", "models": [], "priority": 10},
]


async def seed_providers():
    await db.providers.create_index("id", unique=True)
    if await db.providers.count_documents({}) == 0:
        docs = []
        for p in DEFAULT_PROVIDERS:
            prov = Provider(**p, supported_features=_FEATURES.get(p["category"], []))
            docs.append(prov.model_dump())
        await db.providers.insert_many(docs)

    # Ensure every catalog provider exists (idempotent, non-destructive — matched by name).
    existing_names = set(await db.providers.distinct("name"))
    to_insert = []
    for entry in PROVIDER_CATALOG:
        if entry["name"] not in existing_names:
            prov = Provider(
                name=entry["name"], category=entry["category"], base_url=entry["base_url"],
                models=entry["models"], default_model=entry["models"][0] if entry["models"] else "",
                supported_features=_FEATURES.get(entry["category"], []),
            )
            to_insert.append(prov.model_dump())
    if to_insert:
        await db.providers.insert_many(to_insert)

    # Backfill new/missing fields on previously-seeded docs.
    async for doc in db.providers.find({}):
        patch = {}
        if "priority" not in doc:
            patch["priority"] = 100
        if "status" not in doc:
            patch["status"] = STATUS_NOT_CONFIGURED
        if "supported_features" not in doc:
            patch["supported_features"] = _FEATURES.get(doc.get("category", ""), [])
        if "default_model" not in doc:
            models = doc.get("models", [])
            patch["default_model"] = models[0] if models else ""
        if "organization_id" not in doc:
            patch["organization_id"] = ""
        if "notes" not in doc:
            patch["notes"] = ""
        if "last_test_ms" not in doc:
            patch["last_test_ms"] = 0
        if patch:
            await db.providers.update_one({"id": doc["id"]}, {"$set": patch})
