"""Akasha Brain — Command Center, Prompt Optimizer, Context Engine (lightweight)."""
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator

from core import db, now_iso, new_id, logger

router = APIRouter(prefix="/api/brain", tags=["brain"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"


class OptimizeRequest(BaseModel):
    prompt: str
    target: str = "image"       # image | video | text | music | voice
    project_id: Optional[str] = None


class AssistRequest(BaseModel):
    message: str
    project_id: Optional[str] = None


async def _project_context(project_id: str) -> Dict[str, Any]:
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        return {}
    bibles = await db.bibles.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    characters = await db.characters.find({"project_id": project_id}, {"_id": 0}).to_list(200)
    return {
        "project": {"name": project["name"], "type": project.get("type"), "description": project.get("description", "")},
        "bibles": [
            {"type": b["type"], "headings": [s.get("heading", "") for s in b.get("sections", [])]}
            for b in bibles if b.get("sections")
        ],
        "characters": [
            {
                "name": c["name"], "role": c.get("role"),
                "appearance": c.get("appearance", ""),
                "appearance_locked": c.get("appearance_locked", False),
                "color_palette": c.get("color_palette", []),
            }
            for c in characters
        ],
    }


def _context_prompt(ctx: Dict[str, Any]) -> str:
    if not ctx:
        return ""
    lines = []
    p = ctx.get("project", {})
    lines.append(f"Project: {p.get('name','')} ({p.get('type','')}). {p.get('description','')}")
    if ctx.get("characters"):
        lines.append("Characters (respect locked appearances exactly):")
        for c in ctx["characters"]:
            lock = " [APPEARANCE LOCKED]" if c.get("appearance_locked") else ""
            pal = f" palette:{','.join(c['color_palette'])}" if c.get("color_palette") else ""
            lines.append(f" - {c['name']} ({c.get('role')}){lock}: {c.get('appearance','')}{pal}")
    if ctx.get("bibles"):
        lines.append("Bible topics: " + "; ".join(f"{b['type']}[{', '.join(h for h in b['headings'] if h)}]" for b in ctx["bibles"]))
    return "\n".join(lines)


async def _llm(system: str, user: str, max_tokens: int = 700) -> str:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="LLM key not configured")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"akasha-brain-{new_id()}",
            system_message=system,
        ).with_model(MODEL_PROVIDER, MODEL_NAME).with_params(max_tokens=max_tokens)
        reply = await chat.send_message(UserMessage(text=user))
        return reply if isinstance(reply, str) else str(reply)
    except HTTPException:
        raise
    except Exception as exc:  # graceful degradation
        raise HTTPException(status_code=502, detail=f"Akasha Brain error: {exc}")


@router.post("/optimize")
async def optimize_prompt(body: OptimizeRequest):
    ctx = await _project_context(body.project_id) if body.project_id else {}
    ctx_text = _context_prompt(ctx)
    system = (
        "You are Akasha Brain, an expert prompt engineer for AI creative generation. "
        f"Rewrite the user's raw idea into a single, production-grade {body.target} generation prompt. "
        "Be vivid, specific and structured (subject, style, lighting, composition, mood, technical params). "
        "If project context is provided, stay consistent with it — especially any LOCKED character appearances. "
        "Return ONLY the optimized prompt text, no preamble."
    )
    user = (f"PROJECT CONTEXT:\n{ctx_text}\n\n" if ctx_text else "") + f"RAW IDEA:\n{body.prompt}"
    optimized = await _llm(system, user, max_tokens=600)
    await db.brain_history.insert_one({
        "id": new_id(), "kind": "optimize", "target": body.target,
        "project_id": body.project_id, "input": body.prompt, "output": optimized,
        "created_at": now_iso(),
    })
    return {"optimized": optimized.strip(), "target": body.target, "used_context": bool(ctx_text)}


@router.post("/assist")
async def assist(body: AssistRequest):
    ctx = await _project_context(body.project_id) if body.project_id else {}
    ctx_text = _context_prompt(ctx)
    system = (
        "You are Akasha Brain, the creative co-pilot inside Akasha Forge (a creative OS). "
        "Give concise, practical, expert guidance on storytelling, world-building, characters, "
        "visuals, and production workflow. Use the project context when relevant."
    )
    user = (f"PROJECT CONTEXT:\n{ctx_text}\n\n" if ctx_text else "") + body.message
    reply = await _llm(system, user, max_tokens=800)
    return {"reply": reply.strip(), "used_context": bool(ctx_text)}


@router.get("/status")
async def brain_status():
    providers = await db.providers.find({}, {"_id": 0}).to_list(1000)
    by_cat: Dict[str, Dict[str, int]] = {}
    for p in providers:
        c = by_cat.setdefault(p["category"], {"total": 0, "ready": 0, "enabled": 0})
        c["total"] += 1
        if p.get("enabled"):
            c["enabled"] += 1
        if p.get("status") == "ready":
            c["ready"] += 1
    return {
        "model": f"{MODEL_PROVIDER}/{MODEL_NAME}",
        "online": bool(EMERGENT_LLM_KEY),
        "providers_total": len(providers),
        "providers_enabled": sum(1 for p in providers if p.get("enabled")),
        "categories": by_cat,
    }


@router.get("/history")
async def brain_history(limit: int = 20):
    return await db.brain_history.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


# ============================================================================
# Knowledge Store (AF-005B) — one searchable, project-scoped knowledge store.
# ============================================================================
def _norm_tags(tags: Optional[List[Any]]) -> List[str]:
    out: List[str] = []
    seen = set()
    for t in tags or []:
        s = str(t).strip().lower()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


class KnowledgeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    entity_type: str
    entity_id: str = ""
    title: str = ""
    text: str = ""
    tags: List[str] = Field(default_factory=list)
    source_module: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class KnowledgeCreate(BaseModel):
    project_id: str
    entity_type: str
    entity_id: str = ""
    title: str
    text: str = ""
    tags: List[str] = Field(default_factory=list)
    source_module: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id", "entity_type", "source_module", "title")
    @classmethod
    def _nonempty(cls, v: str, info):
        if not str(v).strip():
            raise ValueError(f"{info.field_name} is required")
        return str(v).strip()


class KnowledgeIngest(BaseModel):
    project_id: str
    entity_type: str
    entity_id: str
    title: str
    text: str = ""
    tags: List[str] = Field(default_factory=list)
    source_module: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id", "entity_type", "entity_id", "source_module", "title")
    @classmethod
    def _nonempty(cls, v: str, info):
        if not str(v).strip():
            raise ValueError(f"{info.field_name} is required")
        return str(v).strip()


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    source_module: Optional[str] = None


async def ensure_knowledge_indexes():
    """Idempotent index creation for the knowledge_items collection."""
    try:
        await db.knowledge_items.create_index("id", unique=True)
        await db.knowledge_items.create_index([("project_id", 1), ("entity_type", 1)])
        await db.knowledge_items.create_index([("project_id", 1), ("entity_id", 1)])
        await db.knowledge_items.create_index(
            [("title", "text"), ("text", "text"), ("tags", "text")],
            name="knowledge_text",
            weights={"title": 10, "text": 5, "tags": 3},
        )
    except Exception as exc:
        logger.warning("knowledge_items index setup deferred: %s", exc)


@router.post("/knowledge")
async def create_knowledge(body: KnowledgeCreate):
    item = KnowledgeItem(**{**body.model_dump(), "tags": _norm_tags(body.tags)})
    doc = item.model_dump()
    await db.knowledge_items.insert_one(dict(doc))
    return doc


@router.get("/knowledge")
async def list_knowledge(
    project_id: str,
    entity_type: Optional[str] = None,
    source_module: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    query: Dict[str, Any] = {"project_id": project_id}
    if entity_type:
        query["entity_type"] = entity_type
    if source_module:
        query["source_module"] = source_module
    if tag:
        query["tags"] = tag.strip().lower()
    return await db.knowledge_items.find(query, {"_id": 0}).sort("updated_at", -1).skip(offset).limit(limit).to_list(limit)


@router.get("/knowledge/{item_id}")
async def get_knowledge(item_id: str, project_id: Optional[str] = None):
    doc = await db.knowledge_items.find_one({"id": item_id}, {"_id": 0})
    if not doc or (project_id and doc.get("project_id") != project_id):
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return doc


@router.put("/knowledge/{item_id}")
async def update_knowledge(item_id: str, body: KnowledgeUpdate):
    existing = await db.knowledge_items.find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    updates = body.model_dump(exclude_none=True)
    if "tags" in updates:
        updates["tags"] = _norm_tags(updates["tags"])
    for f in ("entity_type", "source_module", "title"):
        if f in updates and not str(updates[f]).strip():
            raise HTTPException(status_code=422, detail=f"{f} cannot be empty")
        if f in updates:
            updates[f] = str(updates[f]).strip()
    updates["updated_at"] = now_iso()
    await db.knowledge_items.update_one({"id": item_id}, {"$set": updates})
    return await db.knowledge_items.find_one({"id": item_id}, {"_id": 0})


@router.delete("/knowledge/{item_id}")
async def delete_knowledge(item_id: str):
    res = await db.knowledge_items.delete_one({"id": item_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return {"ok": True, "deleted": item_id}


@router.post("/knowledge/ingest")
async def ingest_knowledge(body: KnowledgeIngest):
    identity = {
        "project_id": body.project_id, "entity_type": body.entity_type,
        "entity_id": body.entity_id, "source_module": body.source_module,
    }
    now = now_iso()
    set_fields = {
        "title": body.title, "text": body.text,
        "tags": _norm_tags(body.tags), "metadata": body.metadata, "updated_at": now,
    }
    set_on_insert = {"id": new_id(), "created_at": now, **identity}
    await db.knowledge_items.update_one(identity, {"$set": set_fields, "$setOnInsert": set_on_insert}, upsert=True)
    return await db.knowledge_items.find_one(identity, {"_id": 0})


@router.get("/search")
async def brain_search(
    project_id: str,
    q: str,
    entity_type: Optional[str] = None,
    source_module: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
):
    if not q.strip():
        return {"query": q, "project_id": project_id, "count": 0, "results": []}
    query: Dict[str, Any] = {"project_id": project_id, "$text": {"$search": q}}
    if entity_type:
        query["entity_type"] = entity_type
    if source_module:
        query["source_module"] = source_module
    if tag:
        query["tags"] = tag.strip().lower()
    cursor = (
        db.knowledge_items.find(query, {"_id": 0, "score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"}), ("updated_at", -1)])
        .limit(limit)
    )
    results = await cursor.to_list(limit)
    return {"query": q, "project_id": project_id, "count": len(results), "results": results}
