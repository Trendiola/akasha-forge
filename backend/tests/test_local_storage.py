"""AF-DESKTOP-003 — Local file storage backend tests.

Two layers:
 * Unit tests exercise the LOCAL filesystem backend directly by pointing core at
   a temp AKASHA_DATA_DIR (independent of the running server's remote mode).
 * API tests confirm the /api/files interface is preserved in the running
   (remote-mode) preview server.
"""
import io
import os
import importlib
import uuid
from pathlib import Path

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"


# --------------------------- LOCAL BACKEND UNIT TESTS ---------------------------
@pytest.fixture()
def local_core(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHA_DB_BACKEND", "local")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("AKASHA_DATA_DIR", str(tmp_path / "AkashaForge"))
    import core as core_mod
    importlib.reload(core_mod)
    core_mod.init_storage()
    yield core_mod


def test_local_dirs_created(local_core):
    root = local_core.STORAGE_ROOT / "akasha-forge"
    for sub in ["images", "videos", "audio", "music", "documents", "thumbnails", "exports"]:
        assert (root / sub).is_dir(), sub
    for sib in ["projects", "cache", "logs"]:
        assert (local_core.AKASHA_DATA_DIR / sib).is_dir(), sib


def test_local_put_image_video_audio_and_categories(local_core):
    img = local_core.put_object("akasha-forge/general/a.png", b"img-bytes", "image/png")
    vid = local_core.put_object("akasha-forge/general/b.mp4", b"vid-bytes", "video/mp4")
    aud = local_core.put_object("akasha-forge/general/c.wav", b"aud-bytes", "audio/wav")
    mus = local_core.put_object("akasha-forge/music/d.mp3", b"mus-bytes", "audio/mpeg")
    assert img["path"] == "akasha-forge/images/a.png"
    assert vid["path"] == "akasha-forge/videos/b.mp4"
    assert aud["path"] == "akasha-forge/audio/c.wav"
    assert mus["path"] == "akasha-forge/music/d.mp3"
    # bytes really on disk
    data, ct = local_core.get_object(img["path"])
    assert data == b"img-bytes" and ct == "image/png"


def test_local_object_ids_unique(local_core):
    ids = {local_core.new_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_local_stream_and_metadata(local_core):
    put = local_core.put_object("akasha-forge/general/x.png", b"0123456789" * 100, "image/png")
    stream, ct = local_core.get_object_stream(put["path"])
    collected = b"".join(stream)
    assert collected == b"0123456789" * 100 and ct == "image/png"
    meta = local_core.get_object_metadata(put["path"])
    assert meta["size_bytes"] == 1000 and meta["storage_backend"] == "local"


def test_local_missing_and_traversal_rejected(local_core):
    with pytest.raises(FileNotFoundError):
        local_core.get_object("akasha-forge/images/does-not-exist.png")
    for evil in ["../../etc/passwd", "akasha-forge/../../secret", "..\\..\\windows\\system32"]:
        with pytest.raises(ValueError):
            local_core.resolve_object_path(evil)


def test_local_delete_only_target(local_core):
    a = local_core.put_object("akasha-forge/general/keep.png", b"keep", "image/png")
    b = local_core.put_object("akasha-forge/general/drop.png", b"drop", "image/png")
    assert local_core.delete_object(b["path"]) is True
    assert local_core.object_exists(b["path"]) is False
    assert local_core.object_exists(a["path"]) is True  # unrelated file untouched
    assert local_core.delete_object("akasha-forge/images/missing.png") is False


def test_windows_style_data_dir(tmp_path, monkeypatch):
    win_like = str(tmp_path / "AppData" / "Roaming" / "AkashaForge")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("AKASHA_DATA_DIR", win_like)
    monkeypatch.setenv("AKASHA_DB_BACKEND", "local")
    import core as core_mod
    importlib.reload(core_mod)
    core_mod.init_storage()
    put = core_mod.put_object("akasha-forge/general/w.png", b"win", "image/png")
    assert core_mod.object_exists(put["path"])


# --------------------------- REMOTE-MODE API PRESERVATION ---------------------------
def test_remote_api_upload_serve_delete_roundtrip():
    png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    files = {"file": ("probe.png", io.BytesIO(png), "image/png")}
    up = requests.post(f"{BASE}/files/upload", files=files, data={"category": "image-edit"})
    assert up.status_code == 200, up.text
    rec = up.json()
    assert rec["id"] and rec["storage_backend"] in ("remote", "local")
    assert rec["mime_type"] == "image/png" and rec["checksum"]

    got = requests.get(f"{BASE}/files/{rec['id']}")
    assert got.status_code == 200
    assert got.headers.get("content-type", "").startswith("image/")
    assert got.content == png  # F5 re-fetch returns the same bytes

    assert requests.get(f"{BASE}/files/{uuid.uuid4()}").status_code == 404

    d = requests.delete(f"{BASE}/files/{rec['id']}")
    assert d.status_code == 200 and d.json()["ok"] is True
    assert requests.get(f"{BASE}/files/{rec['id']}").status_code == 404
