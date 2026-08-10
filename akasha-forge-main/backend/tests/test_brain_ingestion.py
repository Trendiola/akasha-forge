"""AF-005C — Automatic knowledge ingestion backend tests."""
import os
import uuid
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
BRAIN = f"{BASE}/brain"


def _new_project():
    r = requests.post(f"{BASE}/projects", json={"name": f"TEST_ING_{uuid.uuid4().hex[:8]}", "type": "story"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _del_project(pid):
    requests.delete(f"{BASE}/projects/{pid}")


def _knowledge(pid, **filters):
    params = {"project_id": pid, "limit": 500, **filters}
    return requests.get(f"{BRAIN}/knowledge", params=params).json()


def _find(pid, entity_type, entity_id):
    return [k for k in _knowledge(pid, entity_type=entity_type) if k["entity_id"] == entity_id]


def test_bible_create_update_delete_syncs_knowledge():
    pid = _new_project()
    try:
        # create/update bible
        r = requests.put(f"{BASE}/projects/{pid}/bibles/world", json={"sections": [
            {"heading": "Geography", "content": "The frostbound Northlands and molten Ashlands."},
        ]})
        assert r.status_code == 200, r.text
        bid = r.json()["id"]
        items = _find(pid, "bible", bid)
        assert len(items) == 1
        assert "frostbound" in items[0]["text"].lower()
        assert items[0]["source_module"] == "bibles"
        assert items[0]["metadata"]["section_count"] == 1

        # update -> same item, updated text
        r2 = requests.put(f"{BASE}/projects/{pid}/bibles/world", json={"sections": [
            {"heading": "Geography", "content": "Now includes the Sunken Marsh."},
        ]})
        assert r2.status_code == 200
        items2 = _find(pid, "bible", bid)
        assert len(items2) == 1 and "sunken marsh" in items2[0]["text"].lower()

        # delete bible -> knowledge removed
        d = requests.delete(f"{BASE}/projects/{pid}/bibles/world")
        assert d.status_code == 200
        assert len(_find(pid, "bible", bid)) == 0
    finally:
        _del_project(pid)


def test_character_create_update_delete_syncs_knowledge():
    pid = _new_project()
    try:
        c = requests.post(f"{BASE}/projects/{pid}/characters", json={"name": "Zephyrus", "role": "protagonist", "appearance": "silver cloak"})
        assert c.status_code == 200, c.text
        cid = c.json()["id"]
        items = _find(pid, "character", cid)
        assert len(items) == 1 and items[0]["title"] == "Zephyrus"
        assert "silver cloak" in items[0]["text"].lower()

        # update adds searchable text
        u = requests.put(f"{BASE}/characters/{cid}", json={"personality": "stoic and loyal guardian"})
        assert u.status_code == 200
        items2 = _find(pid, "character", cid)
        assert len(items2) == 1 and "stoic" in items2[0]["text"].lower()

        # search returns ingested record
        s = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "Zephyrus"}).json()
        assert s["count"] >= 1 and any(r["entity_id"] == cid for r in s["results"])

        d = requests.delete(f"{BASE}/characters/{cid}")
        assert d.status_code == 200
        assert len(_find(pid, "character", cid)) == 0
    finally:
        _del_project(pid)


def test_production_node_create_update_no_duplicate():
    pid = _new_project()
    try:
        n = requests.post(f"{BASE}/projects/{pid}/production", json={"type": "scene", "title": "Opening duel", "description": "rooftop chase at night"})
        assert n.status_code == 200, n.text
        nid = n.json()["id"]
        assert len(_find(pid, "production_node", nid)) == 1

        requests.put(f"{BASE}/production/{nid}", json={"description": "rooftop chase during a thunderstorm"})
        items = _find(pid, "production_node", nid)
        assert len(items) == 1 and "thunderstorm" in items[0]["text"].lower()

        d = requests.delete(f"{BASE}/production/{nid}")
        assert d.status_code == 200
        assert len(_find(pid, "production_node", nid)) == 0
    finally:
        _del_project(pid)


def test_forge_item_eligible_ingest_and_canvas_state_skipped():
    pid = _new_project()
    try:
        # eligible: music brief with searchable content
        brief = requests.post(f"{BASE}/projects/{pid}/forge/music", json={"kind": "brief", "title": "Main Theme", "data": {"mood": "heroic orchestral swell"}})
        assert brief.status_code == 200, brief.text
        bid = brief.json()["id"]
        bk = _find(pid, "brief", bid)
        assert len(bk) == 1 and "heroic orchestral" in bk[0]["text"].lower()
        assert bk[0]["source_module"] == "forge_items:music"

        # canvas_state must be skipped
        cs = requests.post(f"{BASE}/projects/{pid}/forge/image", json={"kind": "canvas_state", "title": "canvas", "data": {"asset_id": "abc"}})
        assert cs.status_code == 200
        csid = cs.json()["id"]
        assert len(_find(pid, "canvas_state", csid)) == 0
        # nothing with that entity_id anywhere
        assert not any(k["entity_id"] == csid for k in _knowledge(pid))

        # delete eligible forge item removes knowledge
        d = requests.delete(f"{BASE}/forge-items/{bid}")
        assert d.status_code == 200
        assert len(_find(pid, "brief", bid)) == 0
    finally:
        _del_project(pid)


def test_backfill_creates_and_is_idempotent():
    pid = _new_project()
    try:
        # Seed data directly through module endpoints (which also auto-ingest),
        # then wipe knowledge to simulate pre-existing records, then backfill.
        requests.put(f"{BASE}/projects/{pid}/bibles/story", json={"sections": [{"heading": "Premise", "content": "A heist across dimensions."}]})
        requests.post(f"{BASE}/projects/{pid}/characters", json={"name": "Nyx", "role": "antagonist"})
        requests.post(f"{BASE}/projects/{pid}/production", json={"type": "act", "title": "Act I"})
        requests.post(f"{BASE}/projects/{pid}/forge/world", json={"kind": "location", "title": "The Vault", "data": {"desc": "a shifting labyrinth"}})

        # remove existing knowledge to force backfill to CREATE
        for k in _knowledge(pid):
            requests.delete(f"{BRAIN}/knowledge/{k['id']}")
        assert len(_knowledge(pid)) == 0

        b1 = requests.post(f"{BRAIN}/knowledge/backfill", json={"project_id": pid})
        assert b1.status_code == 200, b1.text
        totals1 = b1.json()["totals"]
        assert totals1["created"] == 4 and totals1["failed"] == 0
        assert len(_knowledge(pid)) == 4

        # running twice creates no duplicates
        b2 = requests.post(f"{BRAIN}/knowledge/backfill", json={"project_id": pid})
        totals2 = b2.json()["totals"]
        assert totals2["created"] == 0 and totals2["updated"] == 4
        assert len(_knowledge(pid)) == 4
    finally:
        _del_project(pid)


def test_project_isolation():
    a, b = _new_project(), _new_project()
    try:
        requests.post(f"{BASE}/projects/{a}/characters", json={"name": "Solaire", "role": "supporting"})
        requests.post(f"{BASE}/projects/{b}/characters", json={"name": "Solaire", "role": "supporting"})

        ka = _knowledge(a)
        assert all(k["project_id"] == a for k in ka)
        s = requests.get(f"{BRAIN}/search", params={"project_id": a, "q": "Solaire"}).json()
        assert s["count"] == 1 and all(r["project_id"] == a for r in s["results"])
    finally:
        _del_project(a)
        _del_project(b)


def test_existing_module_crud_still_works():
    pid = _new_project()
    try:
        c = requests.post(f"{BASE}/projects/{pid}/characters", json={"name": "Regression", "role": "minor"})
        assert c.status_code == 200
        cid = c.json()["id"]
        assert requests.get(f"{BASE}/characters/{cid}").status_code == 200
        assert requests.put(f"{BASE}/characters/{cid}", json={"tagline": "still working"}).status_code == 200
        # bible get, production get, forge list still fine
        assert requests.get(f"{BASE}/projects/{pid}/bibles").status_code == 200
        assert requests.get(f"{BASE}/projects/{pid}/production").status_code == 200
        assert requests.get(f"{BASE}/projects/{pid}/forge/music").status_code == 200
        # existing brain endpoints
        assert requests.get(f"{BRAIN}/status").status_code == 200
    finally:
        _del_project(pid)
