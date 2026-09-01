"""Backend tests specifically covering Image Forge P2 persistence semantics:

- Uploads become forge_items kind='asset' with data.file_id
- Canvas state persists via kind='canvas_state' with data.asset_id
- Gallery membership persists via kind='gallery' with data.asset_ids array
- PUT $set-replaces data — frontend spreads existing keys (verified here)
- Membership de-dup is enforced by frontend logic (no backend uniqueness); we
  verify the backend faithfully persists whatever array the frontend sends.
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    return s


@pytest.fixture(scope="module")
def project(session):
    r = session.post(f"{API}/projects", json={"name": "TEST_image_p2", "description": "image forge p2"})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    session.delete(f"{API}/projects/{pid}")


@pytest.fixture(scope="module")
def uploaded_asset(session, project):
    """Create shared persisted state explicitly instead of relying on test order."""
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    upload = session.post(
        f"{API}/files/upload",
        files={"file": ("test.png", io.BytesIO(png), "image/png")},
        data={"category": "image-edit"},
    )
    assert upload.status_code == 200, upload.text
    file_id = upload.json()["id"]
    created = session.post(
        f"{API}/projects/{project}/forge/image",
        json={"kind": "asset", "title": "TEST_upload.png", "data": {"file_id": file_id, "source": "upload"}},
    )
    assert created.status_code == 200, created.text
    return {"file_id": file_id, "asset_id": created.json()["id"]}


class TestUploadAndAssetCreation:
    def test_upload_returns_id_and_url(self, session):
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
        files = {"file": ("test.png", io.BytesIO(png), "image/png")}
        data = {"category": "image-edit"}
        r = session.post(f"{API}/files/upload", files=files, data=data)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "id" in body
        assert body.get("url")
        # store on class for reuse
        TestUploadAndAssetCreation.file_id = body["id"]

    def test_create_asset_forge_item(self, session, project, uploaded_asset):
        file_id = uploaded_asset["file_id"]
        asset_id = uploaded_asset["asset_id"]

        # LIST kind=asset shows it
        r = session.get(f"{API}/projects/{project}/forge/image?kind=asset")
        ids = [x["id"] for x in r.json()]
        assert asset_id in ids


class TestCanvasStatePersistence:
    def test_create_and_update_canvas_state(self, session, project, uploaded_asset):
        asset_id = uploaded_asset["asset_id"]

        # Create canvas_state pointing at asset
        r = session.post(
            f"{API}/projects/{project}/forge/image",
            json={"kind": "canvas_state", "title": "canvas", "data": {"asset_id": asset_id}},
        )
        assert r.status_code == 200
        cs = r.json()
        assert cs["data"]["asset_id"] == asset_id
        cs_id = cs["id"]

        # F5 simulation — refetch
        r = session.get(f"{API}/projects/{project}/forge/image?kind=canvas_state")
        assert r.status_code == 200
        states = r.json()
        assert any(x["id"] == cs_id and x["data"]["asset_id"] == asset_id for x in states)

        # Clear reference (asset deleted case) via PUT
        r = session.put(f"{API}/forge-items/{cs_id}", json={"data": {"asset_id": None}})
        assert r.status_code == 200
        assert r.json()["data"]["asset_id"] is None


class TestGalleryMembership:
    def test_create_gallery_and_add_asset(self, session, project, uploaded_asset):
        asset_id = uploaded_asset["asset_id"]

        # Create gallery with empty membership
        r = session.post(
            f"{API}/projects/{project}/forge/image",
            json={"kind": "gallery", "title": "TEST_gallery", "data": {"asset_ids": [], "description": "keep me"}},
        )
        assert r.status_code == 200
        g = r.json()
        gid = g["id"]
        assert g["data"]["asset_ids"] == []

        # Add member — frontend spreads existing data because PUT $set replaces whole data
        r = session.put(
            f"{API}/forge-items/{gid}",
            json={"data": {**g["data"], "asset_ids": [asset_id]}},
        )
        assert r.status_code == 200
        updated = r.json()
        assert updated["data"]["asset_ids"] == [asset_id]
        assert updated["data"]["description"] == "keep me"  # spread preserved

        # F5 — GET gallery persists membership
        r = session.get(f"{API}/forge-items/{gid}")
        assert r.status_code == 200
        assert r.json()["data"]["asset_ids"] == [asset_id]

        # Try to add same asset — frontend's addToGallery would detect dup, but if a
        # buggy caller re-sends the same list, backend simply persists it. Confirm.
        r = session.put(f"{API}/forge-items/{gid}", json={"data": {**updated["data"], "asset_ids": [asset_id]}})
        assert r.status_code == 200
        assert r.json()["data"]["asset_ids"] == [asset_id]

        # Membership PUT should NOT create a second asset record — verify count is still 1
        r = session.get(f"{API}/projects/{project}/forge/image?kind=asset")
        asset_ids = [x["id"] for x in r.json()]
        assert asset_ids.count(asset_id) == 1
