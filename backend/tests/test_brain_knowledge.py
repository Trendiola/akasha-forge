"""AF-005B — Akasha Brain Knowledge Store & Search backend tests."""
import os
import uuid
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
BRAIN = f"{BASE}/brain"


def _pid():
    return f"TEST_KB_{uuid.uuid4().hex[:10]}"


def _cleanup(project_id):
    for it in requests.get(f"{BRAIN}/knowledge", params={"project_id": project_id, "limit": 500}).json():
        requests.delete(f"{BRAIN}/knowledge/{it['id']}")


def test_create_get_update_delete():
    pid = _pid()
    try:
        r = requests.post(f"{BRAIN}/knowledge", json={
            "project_id": pid, "entity_type": "character", "entity_id": "c1",
            "title": "Aria the Ranger", "text": "A silver-haired ranger of the north.",
            "tags": ["Hero", "hero", " ranger "], "source_module": "character",
            "metadata": {"role": "protagonist"},
        })
        assert r.status_code == 200, r.text
        item = r.json()
        assert item["id"] and item["project_id"] == pid
        assert item["tags"] == ["hero", "ranger"]  # normalized + deduped
        assert item["created_at"] and item["updated_at"]
        iid = item["id"]

        # retrieve
        g = requests.get(f"{BRAIN}/knowledge/{iid}")
        assert g.status_code == 200 and g.json()["title"] == "Aria the Ranger"

        # update (partial) preserves id/project_id/created_at
        u = requests.put(f"{BRAIN}/knowledge/{iid}", json={"title": "Aria the Warden", "tags": ["Warden"]})
        assert u.status_code == 200, u.text
        up = u.json()
        assert up["title"] == "Aria the Warden"
        assert up["tags"] == ["warden"]
        assert up["id"] == iid and up["project_id"] == pid and up["created_at"] == item["created_at"]

        # delete
        d = requests.delete(f"{BRAIN}/knowledge/{iid}")
        assert d.status_code == 200 and d.json()["ok"] is True
        assert requests.get(f"{BRAIN}/knowledge/{iid}").status_code == 404
    finally:
        _cleanup(pid)


def test_project_scoping_list_and_search():
    a, b = _pid(), _pid()
    try:
        requests.post(f"{BRAIN}/knowledge", json={"project_id": a, "entity_type": "world", "entity_id": "w1", "title": "Dragon Peak citadel", "text": "fortress of stone", "source_module": "world"})
        requests.post(f"{BRAIN}/knowledge", json={"project_id": b, "entity_type": "world", "entity_id": "w2", "title": "Dragon Peak keep", "text": "fortress of stone", "source_module": "world"})

        la = requests.get(f"{BRAIN}/knowledge", params={"project_id": a}).json()
        assert len(la) == 1 and la[0]["project_id"] == a

        # Project A search must never leak Project B records
        sa = requests.get(f"{BRAIN}/search", params={"project_id": a, "q": "Dragon"}).json()
        assert sa["count"] == 1
        assert all(r["project_id"] == a for r in sa["results"])
    finally:
        _cleanup(a)
        _cleanup(b)


def test_search_by_title_and_text_and_score():
    pid = _pid()
    try:
        requests.post(f"{BRAIN}/knowledge", json={"project_id": pid, "entity_type": "note", "entity_id": "n1", "title": "Obsidian gauntlet", "text": "a rare artifact", "source_module": "story"})
        requests.post(f"{BRAIN}/knowledge", json={"project_id": pid, "entity_type": "note", "entity_id": "n2", "title": "Riverside village", "text": "home of the obsidian smith", "source_module": "story"})

        by_title = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "gauntlet"}).json()
        assert by_title["count"] == 1 and by_title["results"][0]["entity_id"] == "n1"
        assert "score" in by_title["results"][0]

        by_text = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "smith"}).json()
        assert by_text["count"] == 1 and by_text["results"][0]["entity_id"] == "n2"

        both = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "obsidian"}).json()
        assert both["count"] == 2
    finally:
        _cleanup(pid)


def test_search_filters_entity_source_tag():
    pid = _pid()
    try:
        requests.post(f"{BRAIN}/knowledge", json={"project_id": pid, "entity_type": "character", "entity_id": "c1", "title": "Storm mage", "text": "wields lightning", "tags": ["magic"], "source_module": "character"})
        requests.post(f"{BRAIN}/knowledge", json={"project_id": pid, "entity_type": "location", "entity_id": "l1", "title": "Storm coast", "text": "wields nothing", "tags": ["geo"], "source_module": "world"})

        by_entity = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "Storm", "entity_type": "character"}).json()
        assert by_entity["count"] == 1 and by_entity["results"][0]["entity_type"] == "character"

        by_source = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "Storm", "source_module": "world"}).json()
        assert by_source["count"] == 1 and by_source["results"][0]["source_module"] == "world"

        by_tag = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "Storm", "tag": "MAGIC"}).json()
        assert by_tag["count"] == 1 and "magic" in by_tag["results"][0]["tags"]

        # list filters too
        lst = requests.get(f"{BRAIN}/knowledge", params={"project_id": pid, "entity_type": "location"}).json()
        assert len(lst) == 1 and lst[0]["entity_type"] == "location"
    finally:
        _cleanup(pid)


def test_ingest_upsert_no_duplicates():
    pid = _pid()
    try:
        body = {"project_id": pid, "entity_type": "character", "entity_id": "hero-1", "title": "Hero v1", "text": "first", "source_module": "character"}
        first = requests.post(f"{BRAIN}/knowledge/ingest", json=body)
        assert first.status_code == 200, first.text
        first_id = first.json()["id"]

        body2 = {**body, "title": "Hero v2", "text": "second"}
        second = requests.post(f"{BRAIN}/knowledge/ingest", json=body2)
        assert second.status_code == 200
        assert second.json()["id"] == first_id  # same record updated
        assert second.json()["title"] == "Hero v2"

        allitems = requests.get(f"{BRAIN}/knowledge", params={"project_id": pid}).json()
        assert len(allitems) == 1  # not duplicated
    finally:
        _cleanup(pid)


def test_empty_search_returns_valid_empty():
    pid = _pid()
    try:
        blank = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "   "}).json()
        assert blank["count"] == 0 and blank["results"] == [] and blank["project_id"] == pid

        nomatch = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "zzzznotfound"}).json()
        assert nomatch["count"] == 0 and nomatch["results"] == []
    finally:
        _cleanup(pid)


def test_invalid_required_fields_return_4xx():
    # missing source_module and title
    r = requests.post(f"{BRAIN}/knowledge", json={"project_id": _pid(), "entity_type": "note"})
    assert 400 <= r.status_code < 500

    # empty entity_type
    r2 = requests.post(f"{BRAIN}/knowledge", json={"project_id": _pid(), "entity_type": "   ", "title": "x", "source_module": "story"})
    assert 400 <= r2.status_code < 500

    # missing project_id on list
    r3 = requests.get(f"{BRAIN}/knowledge")
    assert 400 <= r3.status_code < 500

    # ingest missing entity_id
    r4 = requests.post(f"{BRAIN}/knowledge/ingest", json={"project_id": _pid(), "entity_type": "note", "title": "x", "source_module": "story"})
    assert 400 <= r4.status_code < 500


def test_existing_brain_endpoints_still_work():
    s = requests.get(f"{BRAIN}/status")
    assert s.status_code == 200 and "model" in s.json()
    h = requests.get(f"{BRAIN}/history", params={"limit": 5})
    assert h.status_code == 200 and isinstance(h.json(), list)
