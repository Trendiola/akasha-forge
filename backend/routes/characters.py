"""Character Consistency Engine — the flagship Character Bible."""
from typing import List, Optional, Dict, Any
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso, logger

router = APIRouter(prefix="/api", tags=["characters"])


# ----------------------------- Sub-models -----------------------------
class ReferenceImage(BaseModel):
    id: str = Field(default_factory=new_id)
    file_id: str
    url: str = ""
    label: str = ""
    is_primary: bool = False


class Outfit(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    file_id: str = ""
    url: str = ""


class Expression(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""
    file_id: str = ""
    url: str = ""


class Prop(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: str = ""


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=new_id)
    text: str
    tag: str = "note"
    created_at: str = Field(default_factory=now_iso)


class Relationship(BaseModel):
    id: str = Field(default_factory=new_id)
    character_id: str = ""
    name: str = ""
    type: str = "ally"
    description: str = ""


class Character(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: str
    name: str
    role: str = "supporting"          # protagonist | antagonist | supporting | minor
    tagline: str = ""
    ai_prompt: str = ""
    # Appearance lock
    appearance: str = ""
    appearance_locked: bool = False
    age: str = ""
    height: str = ""
    color_palette: List[str] = Field(default_factory=list)
    # Personality
    personality: str = ""
    traits: List[str] = Field(default_factory=list)
    backstory: str = ""
    # Voice assignment
    voice: Dict[str, Any] = Field(default_factory=dict)  # {provider_id, voice_id, description}
    # Libraries
    reference_images: List[ReferenceImage] = Field(default_factory=list)
    outfits: List[Outfit] = Field(default_factory=list)
    expressions: List[Expression] = Field(default_factory=list)
    props: List[Prop] = Field(default_factory=list)
    memory: List[MemoryEntry] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    version: int = 1
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class CharacterCreate(BaseModel):
    name: str
    role: str = "supporting"
    tagline: str = ""
    ai_prompt: str = ""
    appearance: str = ""
    personality: str = ""


class CharacterUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    role: Optional[str] = None
    tagline: Optional[str] = None
    appearance: Optional[str] = None
    appearance_locked: Optional[bool] = None
    age: Optional[str] = None
    height: Optional[str] = None
    color_palette: Optional[List[str]] = None
    personality: Optional[str] = None
    traits: Optional[List[str]] = None
    backstory: Optional[str] = None
    voice: Optional[Dict[str, Any]] = None
    reference_images: Optional[List[ReferenceImage]] = None
    outfits: Optional[List[Outfit]] = None
    expressions: Optional[List[Expression]] = None
    props: Optional[List[Prop]] = None
    memory: Optional[List[MemoryEntry]] = None
    relationships: Optional[List[Relationship]] = None


# ----------------------------- Routes -----------------------------
@router.get("/projects/{project_id}/characters", response_model=List[Character])
async def list_characters(project_id: str):
    return await db.characters.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)


@router.post("/projects/{project_id}/characters", response_model=Character)
async def create_character(project_id: str, body: CharacterCreate):
    try:
        character = Character(project_id=project_id, **body.model_dump())
        await db.characters.insert_one(character.model_dump())
        logger.info("Created character %s in project %s", character.id, project_id)
        return character
    except Exception:
        logger.exception("Failed to create character in project %s", project_id)
        raise HTTPException(status_code=500, detail="Could not create character")


@router.get("/characters/{character_id}", response_model=Character)
async def get_character(character_id: str):
    doc = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Character not found")
    return doc


@router.put("/characters/{character_id}", response_model=Character)
async def update_character(character_id: str, body: CharacterUpdate):
    existing = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Character not found")
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = now_iso()
    updates["version"] = existing.get("version", 1) + 1
    await db.characters.update_one({"id": character_id}, {"$set": updates})
    return await db.characters.find_one({"id": character_id}, {"_id": 0})


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    res = await db.characters.delete_one({"id": character_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Character not found")
    await db.character_versions.delete_many({"character_id": character_id})
    return {"ok": True}


class AICharacterCreate(BaseModel):
    prompt: str
    role: Optional[str] = None


AI_SYSTEM = (
    "You are Akasha Brain, a character designer. Convert the user's prompt into a "
    "structured Character Bible. Return ONLY strict minified JSON (no markdown, no prose) "
    "with EXACTLY these keys: name (string), role (one of protagonist|antagonist|supporting|minor), "
    "tagline (string), appearance (string, vivid physical canon), personality (string), "
    "voice_suggestion (string), color_palette (array of 3-5 hex color strings), "
    "outfits (array of {name, description}), expressions (array of {name, description}), "
    "props (array of {name, description}), relationships (array of {name, type, description}), "
    "memory (array of {text}). Populate every field meaningfully based on the prompt. "
    "Keep each string under 200 characters and at most 3 items per array. Output compact JSON only."
)


def _parse_ai_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start:end + 1])


@router.post("/projects/{project_id}/characters/ai", response_model=Character)
async def create_character_ai(project_id: str, body: AICharacterCreate):
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail="Please describe the character.")
    from routes.brain import _llm
    try:
        raw = await _llm(AI_SYSTEM, body.prompt.strip(), max_tokens=3500)
        parsed = _parse_ai_json(raw)
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI character parse failed for project %s", project_id)
        raise HTTPException(status_code=422, detail="Akasha Brain couldn't turn that prompt into a character. Please rephrase and try again.")

    def _list(key, fields):
        out = []
        for it in (parsed.get(key) or []):
            if isinstance(it, dict):
                out.append({f: str(it.get(f, "")) for f in fields})
        return out

    try:
        character = Character(
            project_id=project_id,
            name=str(parsed.get("name") or "Unnamed").strip(),
            role=(body.role or parsed.get("role") or "supporting"),
            tagline=str(parsed.get("tagline") or ""),
            appearance=str(parsed.get("appearance") or ""),
            appearance_locked=True,
            color_palette=[str(c) for c in (parsed.get("color_palette") or []) if isinstance(c, str)][:5],
            personality=str(parsed.get("personality") or ""),
            voice={"description": str(parsed.get("voice_suggestion") or "")},
            outfits=_list("outfits", ["name", "description"]),
            expressions=_list("expressions", ["name", "description"]),
            props=_list("props", ["name", "description"]),
            relationships=_list("relationships", ["name", "type", "description"]),
            memory=[{"text": str(m.get("text", ""))} for m in (parsed.get("memory") or []) if isinstance(m, dict)],
            ai_prompt=body.prompt.strip(),
        )
    except Exception:
        logger.exception("AI character build failed for project %s", project_id)
        raise HTTPException(status_code=422, detail="Akasha Brain returned an unexpected format. Please try again.")

    await db.characters.insert_one(character.model_dump())
    logger.info("Created AI character %s in project %s", character.id, project_id)
    return character



# ------- Version history -------
@router.post("/characters/{character_id}/versions")
async def snapshot_character(character_id: str, label: str = ""):
    doc = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Character not found")
    snapshot = {
        "id": new_id(),
        "character_id": character_id,
        "version": doc.get("version", 1),
        "label": label or f"v{doc.get('version', 1)}",
        "snapshot": doc,
        "created_at": now_iso(),
    }
    await db.character_versions.insert_one(dict(snapshot))
    snapshot.pop("_id", None)
    return snapshot


@router.get("/characters/{character_id}/versions")
async def list_versions(character_id: str):
    return await db.character_versions.find({"character_id": character_id}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/characters/{character_id}/versions/{version_id}/restore", response_model=Character)
async def restore_version(character_id: str, version_id: str):
    snap = await db.character_versions.find_one({"id": version_id, "character_id": character_id}, {"_id": 0})
    if not snap:
        raise HTTPException(status_code=404, detail="Version not found")
    current = await db.characters.find_one({"id": character_id}, {"_id": 0})
    restored = dict(snap["snapshot"])
    restored["version"] = current.get("version", 1) + 1
    restored["updated_at"] = now_iso()
    restored.pop("_id", None)
    await db.characters.update_one({"id": character_id}, {"$set": restored})
    return await db.characters.find_one({"id": character_id}, {"_id": 0})
