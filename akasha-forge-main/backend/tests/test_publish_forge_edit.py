"""Backend regression tests for Publish Forge posts (AF-003)."""
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://forge-studio-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def test_list_posts():
    r = requests.get(f"{API}/publish/posts", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_platforms():
    r = requests.get(f"{API}/publish/platforms", timeout=15)
    assert r.status_code == 200
    assert "youtube" in r.json()


def test_create_edit_partial_persistence_delete():
    # CREATE
    payload = {"title": "TEST_AF003_Original", "content": "orig", "platforms": ["youtube"], "scheduled_at": "2026-06-15"}
    r = requests.post(f"{API}/publish/posts", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    post = r.json()
    pid = post["id"]
    assert post["title"] == payload["title"]
    original_status = post.get("status")
    original_campaign = post.get("campaign_id")

    try:
        # GET verify
        r = requests.get(f"{API}/publish/posts", timeout=15)
        assert any(p["id"] == pid for p in r.json())

        # PARTIAL UPDATE - only title
        r = requests.put(f"{API}/publish/posts/{pid}", json={"title": "TEST_AF003_Edited"}, timeout=15)
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["title"] == "TEST_AF003_Edited"
        # untouched fields preserved
        assert updated["platforms"] == ["youtube"]
        assert updated["scheduled_at"] == "2026-06-15"
        assert updated.get("status") == original_status
        assert updated.get("campaign_id") == original_campaign

        # UPDATE platforms + date
        r = requests.put(f"{API}/publish/posts/{pid}", json={"platforms": ["x", "linkedin"], "scheduled_at": "2026-07-01"}, timeout=15)
        assert r.status_code == 200
        u2 = r.json()
        assert u2["platforms"] == ["x", "linkedin"]
        assert u2["scheduled_at"] == "2026-07-01"
        assert u2["title"] == "TEST_AF003_Edited"  # preserved

        # Verify persistence via list
        r = requests.get(f"{API}/publish/posts", timeout=15)
        fetched = next(p for p in r.json() if p["id"] == pid)
        assert fetched["title"] == "TEST_AF003_Edited"
        assert fetched["platforms"] == ["x", "linkedin"]
    finally:
        # DELETE cleanup
        r = requests.delete(f"{API}/publish/posts/{pid}", timeout=15)
        assert r.status_code in (200, 204)


def test_cleanup_stale_test_posts():
    r = requests.get(f"{API}/publish/posts", timeout=15)
    for p in r.json():
        if p.get("title", "").startswith("TEST_"):
            requests.delete(f"{API}/publish/posts/{p['id']}", timeout=15)
