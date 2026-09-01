"""V2 backend tests: Characters, Bibles, Provider Hub (masking/test), Brain, Production, Publish, Image Edit, Files."""
import io
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    return sess


@pytest.fixture(scope="module")
def project(s):
    r = s.post(f"{API}/projects", json={"name": "TEST_V2_Project", "type": "story"})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    s.delete(f"{API}/projects/{pid}")


# ---------------- Characters ----------------
def test_character_lifecycle(s, project):
    r = s.post(f"{API}/projects/{project}/characters",
               json={"name": "TEST_Hero", "role": "protagonist", "appearance": "tall, red cape"})
    assert r.status_code == 200, r.text
    ch = r.json()
    cid = ch["id"]
    assert ch["version"] == 1
    assert ch["appearance_locked"] is False

    # update: lock appearance, palette
    r = s.put(f"{API}/characters/{cid}",
              json={"appearance_locked": True, "color_palette": ["#FF0000", "#000000"]})
    assert r.status_code == 200
    ch2 = r.json()
    assert ch2["appearance_locked"] is True
    assert ch2["color_palette"] == ["#FF0000", "#000000"]
    assert ch2["version"] == 2

    # snapshot version
    r = s.post(f"{API}/characters/{cid}/versions", params={"label": "v2-snap"})
    assert r.status_code == 200
    snap = r.json()
    vid = snap["id"]
    assert snap["version"] == 2
    assert "_id" not in snap

    # list versions
    r = s.get(f"{API}/characters/{cid}/versions")
    assert r.status_code == 200
    assert any(v["id"] == vid for v in r.json())

    # mutate then restore
    s.put(f"{API}/characters/{cid}", json={"appearance": "different"})
    r = s.post(f"{API}/characters/{cid}/versions/{vid}/restore")
    assert r.status_code == 200
    restored = r.json()
    assert restored["appearance"] == "tall, red cape"
    # version increments after restore
    assert restored["version"] >= 4

    # cleanup
    s.delete(f"{API}/characters/{cid}")


# ---------------- Bibles ----------------
def test_bible_types(s):
    r = s.get(f"{API}/bible-types")
    assert r.status_code == 200
    types = r.json()
    assert len(types) == 7
    ids = {t["type"] for t in types}
    assert {"story", "world", "style", "camera", "music", "publishing", "brand"} <= ids


def test_bible_persistence(s, project):
    payload = {"sections": [{"heading": "Geography", "content": "Vast plains"},
                             {"heading": "Cultures", "content": "Nomadic tribes"}]}
    r = s.put(f"{API}/projects/{project}/bibles/world", json=payload)
    assert r.status_code == 200, r.text
    assert len(r.json()["sections"]) == 2

    r = s.get(f"{API}/projects/{project}/bibles/world")
    assert r.status_code == 200
    assert r.json()["sections"][0]["heading"] == "Geography"

    r = s.get(f"{API}/projects/{project}/bibles")
    assert r.status_code == 200
    lst = r.json()
    world = next(b for b in lst if b["type"] == "world")
    assert world["filled"] is True
    assert world["sections_count"] == 2


# ---------------- Provider Hub ----------------
def test_provider_masking_and_test(s):
    r = s.get(f"{API}/providers", params={"category": "llm"})
    llm = r.json()
    pid = llm[0]["id"]

    # PUT api_key; response should mask and never leak raw
    raw = "sk-test-abcdef123456789"
    r = s.put(f"{API}/providers/{pid}", json={"api_key": raw, "enabled": True})
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is True
    assert body["api_key_masked"] and body["api_key_masked"] != raw
    assert "api_key_encrypted" not in body
    assert raw not in str(body)

    # test with key + enabled -> ready
    r = s.post(f"{API}/providers/{pid}/test")
    assert r.status_code == 200
    tb = r.json()
    assert tb["status"] == "configured", tb
    assert "not verified" in tb["message"].lower()

    # disable -> disabled
    s.put(f"{API}/providers/{pid}", json={"enabled": False})
    r = s.post(f"{API}/providers/{pid}/test")
    assert r.json()["status"] == "disabled"

    # re-enable but no key on a fresh provider
    r = s.post(f"{API}/providers", json={"name": "TEST_NoKey", "category": "image"})
    assert r.status_code == 200
    nid = r.json()["id"]
    s.put(f"{API}/providers/{nid}", json={"enabled": True})
    r = s.post(f"{API}/providers/{nid}/test")
    assert r.json()["status"] == "not_configured"

    # delete custom
    r = s.delete(f"{API}/providers/{nid}")
    assert r.status_code == 200
    r = s.get(f"{API}/providers")
    assert nid not in {p["id"] for p in r.json()}


# ---------------- Brain ----------------
def test_brain_status(s):
    r = s.get(f"{API}/brain/status")
    assert r.status_code == 200
    d = r.json()
    assert d["model"] == "anthropic/claude-sonnet-4-6"
    assert isinstance(d["online"], bool)
    assert isinstance(d["categories"], dict)
    assert d["providers_total"] >= 8


def test_brain_optimize(s):
    status = s.get(f"{API}/brain/status").json()
    if not status.get("online"):
        pytest.skip("Akasha Brain requires an explicitly configured LLM credential")
    r = s.post(f"{API}/brain/optimize",
               json={"prompt": "a wizard casting a spell in a rainy alley", "target": "image"},
               timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d.get("optimized"), str)
    assert len(d["optimized"]) > 20
    assert d["target"] == "image"


# ---------------- Production ----------------
def test_production_tree_and_cascade(s, project):
    r = s.post(f"{API}/projects/{project}/production",
               json={"type": "act", "title": "Act I"})
    assert r.status_code == 200
    act_id = r.json()["id"]

    r = s.post(f"{API}/projects/{project}/production",
               json={"type": "chapter", "parent_id": act_id, "title": "Ch 1"})
    assert r.status_code == 200
    ch_id = r.json()["id"]

    r = s.get(f"{API}/projects/{project}/production")
    assert r.status_code == 200
    tree = r.json()["tree"]
    top = next(n for n in tree if n["id"] == act_id)
    assert any(c["id"] == ch_id for c in top["children"])

    # cascade delete act -> chapter gone
    r = s.delete(f"{API}/production/{act_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] >= 2

    r = s.get(f"{API}/projects/{project}/production")
    ids = {n["id"] for n in r.json()["tree"]}
    assert act_id not in ids


# ---------------- Publish ----------------
def test_publish_flow(s):
    r = s.post(f"{API}/publish/campaigns", json={"name": "TEST_Camp"})
    assert r.status_code == 200
    cid = r.json()["id"]

    r = s.post(f"{API}/publish/posts", json={
        "title": "TEST_Post", "content": "hi",
        "platforms": ["youtube", "x"],
        "scheduled_at": "2026-02-01T10:00:00Z",
        "campaign_id": cid,
    })
    assert r.status_code == 200
    pid = r.json()["id"]
    assert r.json()["platforms"] == ["youtube", "x"]

    r = s.get(f"{API}/publish/posts")
    assert any(p["id"] == pid for p in r.json())

    r = s.delete(f"{API}/publish/posts/{pid}")
    assert r.status_code == 200
    s.delete(f"{API}/publish/campaigns/{cid}")


# ---------------- Image Edit ----------------
def test_image_operations_and_job(s):
    r = s.get(f"{API}/image/operations")
    assert r.status_code == 200
    ops = r.json()
    assert len(ops) == 5

    # No enabled image provider by default -> error status
    # disable any test-enabled ones first
    provs = s.get(f"{API}/providers", params={"category": "image"}).json()
    for p in provs:
        if p.get("enabled"):
            s.put(f"{API}/providers/{p['id']}", json={"enabled": False})

    r = s.post(f"{API}/image/jobs", json={"operation": "upscaling", "source_file_id": "fakefile"})
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "error"
    assert "provider" in j["message"].lower()

    # enable one image provider -> queued
    img = provs[0]
    s.put(f"{API}/providers/{img['id']}", json={"enabled": True})
    r = s.post(f"{API}/image/jobs", json={"operation": "upscaling", "source_file_id": "fakefile"})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    # cleanup
    s.put(f"{API}/providers/{img['id']}", json={"enabled": False})


# ---------------- Files ----------------
def test_file_upload_and_serve(s):
    # 1x1 PNG
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    files = {"file": ("t.png", io.BytesIO(png), "image/png")}
    r = s.post(f"{API}/files/upload", files=files, data={"category": "test"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] and d["url"].endswith(f"/api/files/{d['id']}")

    r = s.get(f"{BASE_URL}{d['url']}")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) == len(png)
