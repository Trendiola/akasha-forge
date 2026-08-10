"""Backend tests for the shared Forge CRUD framework and Character AI prompt field."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://forge-studio-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def project(session):
    r = session.post(f"{API}/projects", json={"name": "TEST_forge_pytest", "description": "pytest scoped"})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    session.delete(f"{API}/projects/{pid}")


MODULES = [
    ("story", "chapter", {"summary": "Prologue"}),
    ("story", "draft", {"content": "Once upon a time"}),
    ("story", "beat", {"content": "Inciting incident"}),
    ("world", "location", {"description": "Capital city"}),
    ("world", "faction", {"description": "Rebels"}),
    ("world", "rule", {"description": "Magic requires blood"}),
    ("world", "timeline", {"description": "Year zero"}),
    ("video", "scene", {"description": "Opening"}),
    ("video", "shot", {"scene_id": "abc", "duration": 3, "camera": "wide"}),
    ("video", "render", {"provider": "none"}),
    ("voice", "profile", {"language": "en", "accent": "US", "provider": "elevenlabs", "voice_id": "xyz"}),
    ("music", "brief", {"mood": "calm", "genre": "ambient", "tempo": 80, "duration": 60, "loop": True}),
    ("image", "gallery", {"description": "Concept art"}),
    ("image", "asset", {"url": "https://example.com/img.png"}),
    ("workflow", "graph", {"nodes": [], "edges": []}),
]


class TestForgeCRUD:
    """CRUD across all module/kind combinations."""

    @pytest.mark.parametrize("module,kind,data", MODULES)
    def test_create_list_update_delete(self, session, project, module, kind, data):
        # CREATE
        title = f"TEST_{module}_{kind}"
        r = session.post(f"{API}/projects/{project}/forge/{module}", json={"kind": kind, "title": title, "data": data})
        assert r.status_code == 200, r.text
        item = r.json()
        assert item["title"] == title
        assert item["kind"] == kind
        assert item["module"] == module
        assert item["project_id"] == project
        assert item["data"] == data
        item_id = item["id"]

        # LIST -> item present
        r = session.get(f"{API}/projects/{project}/forge/{module}?kind={kind}")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert item_id in ids

        # GET single
        r = session.get(f"{API}/forge-items/{item_id}")
        assert r.status_code == 200
        assert r.json()["id"] == item_id

        # UPDATE title + data
        new_data = {**data, "extra": "updated"}
        r = session.put(f"{API}/forge-items/{item_id}", json={"title": title + "_v2", "data": new_data})
        assert r.status_code == 200
        assert r.json()["title"] == title + "_v2"
        assert r.json()["data"].get("extra") == "updated"

        # GET after update
        r = session.get(f"{API}/forge-items/{item_id}")
        assert r.json()["title"] == title + "_v2"

        # DELETE
        r = session.delete(f"{API}/forge-items/{item_id}")
        assert r.status_code == 200

        # GET -> 404
        r = session.get(f"{API}/forge-items/{item_id}")
        assert r.status_code == 404


class TestForgeEdgeCases:
    def test_update_nonexistent(self, session):
        r = session.put(f"{API}/forge-items/does-not-exist", json={"title": "x"})
        assert r.status_code == 404

    def test_delete_nonexistent(self, session):
        r = session.delete(f"{API}/forge-items/does-not-exist")
        assert r.status_code == 404

    def test_update_empty_body(self, session, project):
        r = session.post(f"{API}/projects/{project}/forge/story", json={"kind": "chapter", "title": "TEST_empty"})
        item_id = r.json()["id"]
        r = session.put(f"{API}/forge-items/{item_id}", json={})
        assert r.status_code == 400
        session.delete(f"{API}/forge-items/{item_id}")

    def test_list_filtered_by_kind(self, session, project):
        session.post(f"{API}/projects/{project}/forge/world", json={"kind": "location", "title": "TEST_loc1"})
        session.post(f"{API}/projects/{project}/forge/world", json={"kind": "faction", "title": "TEST_fac1"})
        r = session.get(f"{API}/projects/{project}/forge/world?kind=location")
        titles = [x["title"] for x in r.json()]
        assert "TEST_loc1" in titles
        assert "TEST_fac1" not in titles


class TestCascadeDelete:
    def test_deleting_project_cascades_forge_items(self, session):
        r = session.post(f"{API}/projects", json={"name": "TEST_cascade"})
        pid = r.json()["id"]
        r = session.post(f"{API}/projects/{pid}/forge/story", json={"kind": "chapter", "title": "TEST_cascade_ch"})
        item_id = r.json()["id"]
        # delete project
        session.delete(f"{API}/projects/{pid}")
        # item should be gone
        r = session.get(f"{API}/forge-items/{item_id}")
        assert r.status_code == 404


class TestCharacterAIPrompt:
    """Character Forge now supports ai_prompt field."""

    def test_create_character_with_ai_prompt(self, session, project):
        r = session.post(f"{API}/projects/{project}/characters", json={
            "name": "TEST_AI_Character",
            "role": "protagonist",
            "ai_prompt": "A stoic wanderer with a silver sword",
        })
        assert r.status_code == 200, r.text
        char = r.json()
        assert char.get("ai_prompt") == "A stoic wanderer with a silver sword"
        # persist check
        r = session.get(f"{API}/characters/{char['id']}")
        assert r.status_code == 200
        assert r.json().get("ai_prompt") == "A stoic wanderer with a silver sword"
        session.delete(f"{API}/characters/{char['id']}")
