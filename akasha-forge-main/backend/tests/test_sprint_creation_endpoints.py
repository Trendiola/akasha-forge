"""Regression tests for Sprint - creation endpoints returning 200 (not 502) with valid JSON."""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://forge-studio-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def project(s):
    r = s.post(f"{API}/projects", json={
        "name": "TEST_sprint_regression",
        "description": "sprint reg",
        "type": "story",
        "color": "#6D3BFF",
    })
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    s.delete(f"{API}/projects/{pid}")


# ---------------- Characters ----------------
def test_create_character_returns_200_and_persists(s, project):
    r = s.post(f"{API}/projects/{project}/characters", json={
        "name": "TEST_Hero", "role": "protagonist", "ai_prompt": "a brave hero"
    })
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    data = r.json()
    assert "id" in data and isinstance(data["id"], str)
    assert data["name"] == "TEST_Hero"
    assert data["role"] == "protagonist"
    assert data["ai_prompt"] == "a brave hero"
    assert data["project_id"] == project
    # follow-up GET verifies persistence
    r2 = s.get(f"{API}/characters/{data['id']}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "TEST_Hero"
    # cleanup
    s.delete(f"{API}/characters/{data['id']}")


# ---------------- Workflow Forge ----------------
def test_create_workflow_returns_200_and_persists(s, project):
    r = s.post(f"{API}/projects/{project}/forge/workflow", json={
        "kind": "graph",
        "title": "TEST_Workflow_1",
        "data": {"nodes": [], "edges": []}
    })
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    data = r.json()
    assert "id" in data
    assert data["kind"] == "graph"
    assert data["title"] == "TEST_Workflow_1"
    wid = data["id"]
    # persistence
    r2 = s.get(f"{API}/forge-items/{wid}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "TEST_Workflow_1"
    # persist an updated graph
    r3 = s.put(f"{API}/forge-items/{wid}", json={
        "data": {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": [{"from": "n1", "to": "n2"}]}
    })
    assert r3.status_code == 200
    assert len(r3.json()["data"]["nodes"]) == 2
    # cleanup
    s.delete(f"{API}/forge-items/{wid}")


# ---------------- Publish: Campaign ----------------
def test_create_campaign_returns_200_and_persists(s, project):
    r = s.post(f"{API}/publish/campaigns", json={
        "name": "TEST_Campaign_A",
        "goal": "test",
        "project_id": project,
    })
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    data = r.json()
    assert "id" in data
    assert data["name"] == "TEST_Campaign_A"
    cid = data["id"]
    # follow-up list check
    r2 = s.get(f"{API}/publish/campaigns")
    assert r2.status_code == 200
    ids = [c["id"] for c in r2.json()]
    assert cid in ids
    # cleanup
    s.delete(f"{API}/publish/campaigns/{cid}")


# ---------------- Publish: Post ----------------
def test_create_post_returns_200_and_persists(s, project):
    # create a campaign to attach
    cr = s.post(f"{API}/publish/campaigns", json={"name": "TEST_CampaignForPost", "project_id": project})
    assert cr.status_code == 200
    campaign_id = cr.json()["id"]

    r = s.post(f"{API}/publish/posts", json={
        "title": "TEST_Post_1",
        "content": "hello",
        "platforms": ["youtube", "x"],
        "scheduled_at": "2026-06-01T12:00:00Z",
        "campaign_id": campaign_id,
        "project_id": project,
    })
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    data = r.json()
    assert "id" in data
    assert data["title"] == "TEST_Post_1"
    assert data["platforms"] == ["youtube", "x"]
    assert data["campaign_id"] == campaign_id
    pid = data["id"]
    # persistence check
    r2 = s.get(f"{API}/publish/posts")
    assert r2.status_code == 200
    ids = [p["id"] for p in r2.json()]
    assert pid in ids
    # cleanup
    s.delete(f"{API}/publish/posts/{pid}")
    s.delete(f"{API}/publish/campaigns/{campaign_id}")


# ---------------- Post with minimal fields (no campaign, no schedule) ----------------
def test_create_post_minimal_fields(s, project):
    r = s.post(f"{API}/publish/posts", json={"title": "TEST_MinimalPost", "project_id": project})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == "TEST_MinimalPost"
    assert data["platforms"] == []
    s.delete(f"{API}/publish/posts/{data['id']}")


# ---------------- Character with only required fields ----------------
def test_create_character_minimal(s, project):
    r = s.post(f"{API}/projects/{project}/characters", json={"name": "TEST_MinChar"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "TEST_MinChar"
    assert data["role"] == "supporting"
    s.delete(f"{API}/characters/{data['id']}")


# ---------------- Character validation: missing name -> 422 (not 500) ----------------
def test_create_character_missing_name_returns_422(s, project):
    r = s.post(f"{API}/projects/{project}/characters", json={"role": "protagonist"})
    assert r.status_code == 422, f"Expected 422 got {r.status_code}"
