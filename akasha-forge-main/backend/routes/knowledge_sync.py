"""AF-005C — Automatic knowledge ingestion.

Syncs important module entities (bibles, characters, production nodes,
eligible forge_items) into the AF-005B `knowledge_items` store. All sync
functions are best-effort: they log and swallow errors so they can never
break the originating module's save/delete operation.
"""
import re
from typing import Any, Dict, List, Optional

from core import db, new_id, now_iso, logger

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

BIBLE_LABELS = {
    "story": "Story Bible", "world": "World Bible", "style": "Style Bible",
    "camera": "Camera Bible", "music": "Music Bible", "publishing": "Publishing Bible",
    "brand": "Brand Bible",
}
SKIP_FORGE_KINDS = {"canvas_state"}


def _norm_tags(tags: Optional[List[Any]]) -> List[str]:
    out, seen = [], set()
    for t in tags or []:
        s = str(t).strip().lower()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _clean(*parts: Any) -> str:
    vals = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip()
        if s:
            vals.append(s)
    return "\n".join(vals)


def _is_uuid(s: str) -> bool:
    return bool(_UUID_RE.match(s.strip()))


# ----------------------------- Core upsert / delete -----------------------------
async def upsert_knowledge(project_id, entity_type, entity_id, title, text, tags, source_module, metadata) -> str:
    identity = {"project_id": project_id, "entity_type": entity_type, "entity_id": entity_id, "source_module": source_module}
    now = now_iso()
    set_fields = {"title": title or "", "text": text or "", "tags": _norm_tags(tags), "metadata": metadata or {}, "updated_at": now}
    set_on_insert = {"id": new_id(), "created_at": now, **identity}
    res = await db.knowledge_items.update_one(identity, {"$set": set_fields, "$setOnInsert": set_on_insert}, upsert=True)
    return "created" if res.upserted_id is not None else "updated"


async def _delete(project_id, entity_type, entity_id, source_module):
    await db.knowledge_items.delete_one({
        "project_id": project_id, "entity_type": entity_type,
        "entity_id": entity_id, "source_module": source_module,
    })


# ----------------------------- Bibles -----------------------------
def _bible_map(doc: Dict[str, Any]) -> Dict[str, Any]:
    sections = doc.get("sections", []) or []
    btype = doc.get("type", "")
    title = BIBLE_LABELS.get(btype, btype or "Bible")
    parts = [_clean(s.get("heading"), s.get("content")) for s in sections]
    return dict(
        project_id=doc["project_id"], entity_type="bible", entity_id=doc["id"],
        title=title, text=_clean(title, *parts),
        tags=[btype] + [s.get("heading", "") for s in sections],
        source_module="bibles", metadata={"bible_type": btype, "section_count": len(sections)},
    )


async def sync_bible(doc: Dict[str, Any]) -> str:
    try:
        return await upsert_knowledge(**_bible_map(doc))
    except Exception:
        logger.exception("knowledge sync failed: bible %s", doc.get("id"))
        return "failed"


async def remove_bible(project_id: str, bible_id: str):
    try:
        await _delete(project_id, "bible", bible_id, "bibles")
    except Exception:
        logger.exception("knowledge remove failed: bible %s", bible_id)


# ----------------------------- Characters -----------------------------
def _character_map(doc: Dict[str, Any]) -> Dict[str, Any]:
    def _items(key, fields):
        out = []
        for it in doc.get(key, []) or []:
            if isinstance(it, dict):
                out.append(_clean(*[it.get(f) for f in fields]))
        return out

    voice = doc.get("voice", {}) or {}
    text = _clean(
        doc.get("name"), doc.get("role"), doc.get("tagline"),
        doc.get("appearance"), doc.get("personality"), doc.get("backstory"),
        ", ".join(doc.get("traits", []) or []),
        voice.get("description"),
        *_items("outfits", ["name", "description"]),
        *_items("expressions", ["name", "description"]),
        *_items("props", ["name", "description"]),
        *[m.get("text", "") for m in (doc.get("memory") or []) if isinstance(m, dict)],
        *_items("relationships", ["name", "type", "description"]),
        "appearance locked" if doc.get("appearance_locked") else "",
        " ".join(doc.get("color_palette", []) or []),
    )
    return dict(
        project_id=doc["project_id"], entity_type="character", entity_id=doc["id"],
        title=doc.get("name", "Unnamed"), text=text,
        tags=[doc.get("role", "")] + (doc.get("traits") or []),
        source_module="characters",
        metadata={
            "appearance_locked": doc.get("appearance_locked", False),
            "version": doc.get("version", 1),
            "voice_profile": voice.get("voice_id", "") or voice.get("provider_id", ""),
        },
    )


async def sync_character(doc: Dict[str, Any]) -> str:
    try:
        return await upsert_knowledge(**_character_map(doc))
    except Exception:
        logger.exception("knowledge sync failed: character %s", doc.get("id"))
        return "failed"


async def remove_character(project_id: str, character_id: str):
    try:
        await _delete(project_id, "character", character_id, "characters")
    except Exception:
        logger.exception("knowledge remove failed: character %s", character_id)


# ----------------------------- Production nodes -----------------------------
def _production_map(doc: Dict[str, Any]) -> Dict[str, Any]:
    return dict(
        project_id=doc["project_id"], entity_type="production_node", entity_id=doc["id"],
        title=doc.get("title", "Untitled"),
        text=_clean(doc.get("title"), doc.get("description"), doc.get("status"), doc.get("type")),
        tags=[doc.get("type", "")],
        source_module="production",
        metadata={"node_type": doc.get("type"), "parent_id": doc.get("parent_id")},
    )


async def sync_production_node(doc: Dict[str, Any]) -> str:
    try:
        return await upsert_knowledge(**_production_map(doc))
    except Exception:
        logger.exception("knowledge sync failed: production_node %s", doc.get("id"))
        return "failed"


async def remove_production_nodes(node_ids: List[str]):
    try:
        if node_ids:
            await db.knowledge_items.delete_many({
                "entity_type": "production_node", "source_module": "production",
                "entity_id": {"$in": node_ids},
            })
    except Exception:
        logger.exception("knowledge remove failed: production nodes %s", node_ids)


# ----------------------------- Forge items -----------------------------
def _forge_text(data: Any) -> str:
    parts: List[str] = []

    def walk(v):
        if isinstance(v, str):
            s = v.strip()
            if s and not s.startswith("http") and not _is_uuid(s):
                parts.append(s)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(data)
    return "\n".join(parts)


def _forge_type(doc: Dict[str, Any]) -> str:
    return doc.get("kind") or doc.get("module") or "item"


def _forge_source(doc: Dict[str, Any]) -> str:
    return f"forge_items:{doc.get('module', '')}"


def _forge_eligible(doc: Dict[str, Any]) -> bool:
    if doc.get("kind") in SKIP_FORGE_KINDS:
        return False
    data = doc.get("data", {}) or {}
    title = doc.get("title") or data.get("title") or data.get("name") or ""
    return bool(str(title).strip() or _forge_text(data).strip())


def _forge_map(doc: Dict[str, Any]) -> Dict[str, Any]:
    module = doc.get("module", "")
    kind = doc.get("kind", "")
    data = doc.get("data", {}) or {}
    title = doc.get("title") or data.get("title") or data.get("name") or f"{module} {kind}".strip()
    extra_tags = data.get("tags") if isinstance(data.get("tags"), list) else []
    return dict(
        project_id=doc["project_id"], entity_type=_forge_type(doc), entity_id=doc["id"],
        title=title, text=_clean(title, _forge_text(data)),
        tags=[module, kind] + extra_tags,
        source_module=_forge_source(doc),
        metadata={"module": module, "kind": kind},
    )


async def sync_forge_item(doc: Dict[str, Any]) -> str:
    try:
        if not _forge_eligible(doc):
            # Ensure no stale knowledge item remains if it became ineligible.
            await _delete(doc.get("project_id"), _forge_type(doc), doc.get("id"), _forge_source(doc))
            return "skipped"
        return await upsert_knowledge(**_forge_map(doc))
    except Exception:
        logger.exception("knowledge sync failed: forge_item %s", doc.get("id"))
        return "failed"


async def remove_forge_item(doc: Dict[str, Any]):
    try:
        await _delete(doc.get("project_id"), _forge_type(doc), doc.get("id"), _forge_source(doc))
    except Exception:
        logger.exception("knowledge remove failed: forge_item %s", doc.get("id"))


# ----------------------------- Backfill -----------------------------
async def backfill_project(project_id: str) -> Dict[str, Any]:
    sources: Dict[str, Dict[str, int]] = {
        "bibles": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
        "characters": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
        "production": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
        "forge_items": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
    }

    async def _run(source_key, cursor_docs, sync_fn):
        for doc in cursor_docs:
            status = await sync_fn(doc)
            sources[source_key][status] = sources[source_key].get(status, 0) + 1

    bibles = await db.bibles.find({"project_id": project_id}, {"_id": 0}).to_list(1000)
    await _run("bibles", bibles, sync_bible)

    chars = await db.characters.find({"project_id": project_id}, {"_id": 0}).to_list(2000)
    await _run("characters", chars, sync_character)

    nodes = await db.production_nodes.find({"project_id": project_id}, {"_id": 0}).to_list(5000)
    await _run("production", nodes, sync_production_node)

    items = await db.forge_items.find({"project_id": project_id}, {"_id": 0}).to_list(5000)
    await _run("forge_items", items, sync_forge_item)

    totals = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    for s in sources.values():
        for k, v in s.items():
            totals[k] += v
    return {"project_id": project_id, "sources": sources, "totals": totals}
