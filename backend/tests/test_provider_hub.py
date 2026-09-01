"""AF-004 Provider Hub backend regression tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


class TestCatalogAndCategories:
    def test_categories(self, s):
        r = s.get(f"{API}/provider-categories", timeout=15)
        assert r.status_code == 200
        cats = r.json()
        ids = {c["id"] for c in cats}
        assert {"llm", "image", "video", "voice", "music"}.issubset(ids)

    def test_catalog_has_11(self, s):
        r = s.get(f"{API}/provider-catalog", timeout=15)
        assert r.status_code == 200
        cat = r.json()
        assert len(cat) == 11
        names = {c["name"] for c in cat}
        expected = {"OpenAI", "Google Gemini", "Anthropic Claude", "ElevenLabs",
                    "Suno", "Runway", "Veo", "Kling", "Fal", "Replicate", "Stability AI"}
        assert expected.issubset(names)

    def test_seeded_providers_contain_all_11_catalog_names(self, s):
        r = s.get(f"{API}/providers", timeout=15)
        assert r.status_code == 200
        provs = r.json()
        names = {p["name"] for p in provs}
        expected = {"OpenAI", "Google Gemini", "Anthropic Claude", "ElevenLabs",
                    "Suno", "Runway", "Veo", "Kling", "Fal", "Replicate", "Stability AI"}
        missing = expected - names
        assert not missing, f"Missing seeded catalog providers: {missing}"


class TestProviderCRUD:
    created_id = None

    def test_create_full_fields(self, s):
        payload = {
            "name": "TEST_ProviderAF004",
            "category": "llm",
            "base_url": "https://api.example.com",
            "models": ["m-alpha", "m-beta"],
            "default_model": "m-alpha",
            "organization_id": "org_TEST_123",
            "notes": "seed for AF-004 tests",
            "api_key": "sk-testkey-abcdef1234567890",
            "enabled": True,
        }
        r = s.post(f"{API}/providers", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == payload["name"]
        assert d["category"] == "llm"
        assert d["default_model"] == "m-alpha"
        assert d["organization_id"] == "org_TEST_123"
        assert d["notes"] == "seed for AF-004 tests"
        assert d["enabled"] is True
        # Encrypted key: masked returned, raw absent
        assert "api_key_encrypted" not in d
        assert d["configured"] is True
        assert d["api_key_masked"] and d["api_key_masked"] != payload["api_key"]
        # status derived: enabled+key -> configured
        assert d["status"] in ("configured", "ready")
        TestProviderCRUD.created_id = d["id"]

    def test_get_persists(self, s):
        assert TestProviderCRUD.created_id
        r = s.get(f"{API}/providers", timeout=15)
        assert r.status_code == 200
        got = next((p for p in r.json() if p["id"] == TestProviderCRUD.created_id), None)
        assert got is not None
        assert got["notes"] == "seed for AF-004 tests"
        assert got["default_model"] == "m-alpha"

    def test_update_partial(self, s):
        pid = TestProviderCRUD.created_id
        r = s.put(f"{API}/providers/{pid}", json={"notes": "updated notes", "default_model": "m-beta"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["notes"] == "updated notes"
        assert d["default_model"] == "m-beta"
        # Fields not sent are preserved
        assert d["organization_id"] == "org_TEST_123"
        assert d["configured"] is True

    def test_toggle_disable_status(self, s):
        pid = TestProviderCRUD.created_id
        r = s.put(f"{API}/providers/{pid}", json={"enabled": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "disabled"

    def test_test_endpoint_disabled(self, s):
        pid = TestProviderCRUD.created_id
        r = s.post(f"{API}/providers/{pid}/test", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "disabled"
        assert isinstance(d["response_ms"], int) and d["response_ms"] >= 1

    def test_test_endpoint_configured_unverified(self, s):
        pid = TestProviderCRUD.created_id
        s.put(f"{API}/providers/{pid}", json={"enabled": True}, timeout=15)
        r = s.post(f"{API}/providers/{pid}/test", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "configured"
        assert "not verified" in d["message"].lower()
        assert d["response_ms"] >= 1
        assert d["provider"]["last_test_ms"] >= 1

    def test_test_endpoint_short_key_error(self, s):
        # Create a provider with a too-short key
        r = s.post(f"{API}/providers", json={
            "name": "TEST_ShortKey", "category": "llm", "api_key": "short", "enabled": True,
        }, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]
        r2 = s.post(f"{API}/providers/{pid}/test", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "error"
        # cleanup
        s.delete(f"{API}/providers/{pid}", timeout=15)

    def test_delete(self, s):
        pid = TestProviderCRUD.created_id
        r = s.delete(f"{API}/providers/{pid}", timeout=15)
        assert r.status_code == 200
        # Verify gone
        r2 = s.get(f"{API}/providers", timeout=15)
        assert not any(p["id"] == pid for p in r2.json())

    def test_delete_nonexistent_404(self, s):
        r = s.delete(f"{API}/providers/nonexistent-xyz", timeout=15)
        assert r.status_code == 404


    def test_zz_cleanup_leftover(self, s):
        """Best-effort cleanup — kept inside class so xdist keeps it on same worker after CRUD."""
        r = s.get(f"{API}/providers", timeout=15)
        for p in r.json():
            if p["name"].startswith("TEST_"):
                s.delete(f"{API}/providers/{p['id']}", timeout=15)
