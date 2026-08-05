"""Akasha Brain — Command Center, Prompt Optimizer, Context Engine (lightweight)."""
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import db, now_iso, new_id

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
