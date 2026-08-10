"""Backend API tests for Akasha Forge."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "https://forge-studio-core.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------------- Health ----------------
def test_root(s):
    r = s.get(f"{API}/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "online"


# ---------------- Providers ----------------
def test_providers_seeded(s):
    r = s.get(f"{API}/providers")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 8, f"expected >=8 seeded providers, got {len(data)}"
    # verify no _id field leaked
    assert all("_id" not in p for p in data)
    names = {p["name"] for p in data}
    for expected in ["OpenAI", "Anthropic", "Google Gemini", "Stable Diffusion",
                     "Runway", "ElevenLabs", "Suno", "DeepL"]:
        assert expected in names


def test_providers_filter_llm(s):
    r = s.get(f"{API}/providers", params={"category": "llm"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 3
    assert all(p["category"] == "llm" for p in data)


def test_provider_toggle_and_default(s):
    # get an llm provider
    r = s.get(f"{API}/providers", params={"category": "llm"})
    llm = r.json()
    assert len(llm) >= 2
    p1, p2 = llm[0], llm[1]

    # enable p1
    r = s.put(f"{API}/providers/{p1['id']}", json={"enabled": True, "is_default": True})
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert r.json()["is_default"] is True

    # now set p2 as default -> p1 should be unset
    r = s.put(f"{API}/providers/{p2['id']}", json={"enabled": True, "is_default": True})
    assert r.status_code == 200
    assert r.json()["is_default"] is True

    # verify p1 no longer default
    r = s.get(f"{API}/providers", params={"category": "llm"})
    updated = {p["id"]: p for p in r.json()}
    assert updated[p1["id"]]["is_default"] is False
    assert updated[p2["id"]]["is_default"] is True


# ---------------- Projects CRUD ----------------
def test_projects_crud(s):
    # CREATE
    payload = {"name": "TEST_Project_A", "description": "hello", "type": "story", "color": "#6D3BFF"}
    r = s.post(f"{API}/projects", json=payload)
    assert r.status_code == 200, r.text
    proj = r.json()
    assert proj["name"] == "TEST_Project_A"
    assert proj["type"] == "story"
    assert "id" in proj
    pid = proj["id"]

    # LIST
    r = s.get(f"{API}/projects")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pid in ids

    # GET
    r = s.get(f"{API}/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Project_A"

    # UPDATE
    r = s.put(f"{API}/projects/{pid}", json={"name": "TEST_Project_A_Updated", "status": "archived"})
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Project_A_Updated"
    assert r.json()["status"] == "archived"

    # verify persistence
    r = s.get(f"{API}/projects/{pid}")
    assert r.json()["name"] == "TEST_Project_A_Updated"

    # DELETE
    r = s.delete(f"{API}/projects/{pid}")
    assert r.status_code == 200

    r = s.get(f"{API}/projects/{pid}")
    assert r.status_code == 404


# ---------------- Settings ----------------
def test_settings_get(s):
    r = s.get(f"{API}/settings")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "global"
    assert "general" in d
    assert "appearance" in d


def test_settings_partial_update(s):
    # get current
    current = s.get(f"{API}/settings").json()
    general = dict(current.get("general") or {})
    general["autosave"] = not general.get("autosave", True)
    new_val = general["autosave"]

    r = s.put(f"{API}/settings", json={"general": general})
    assert r.status_code == 200
    assert r.json()["general"]["autosave"] == new_val

    # verify persist
    r = s.get(f"{API}/settings")
    assert r.json()["general"]["autosave"] == new_val

    # restore
    general["autosave"] = not new_val
    s.put(f"{API}/settings", json={"general": general})
