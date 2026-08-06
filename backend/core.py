"""Shared core: database, helpers, storage, encryption. Single source of truth."""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger("akasha")

# ----------------------------- Database -----------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ----------------------------- Encryption ---------------------------
_fernet = Fernet(os.environ["AKASHA_SECRET_KEY"].encode())


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except Exception:
        return ""


def mask_key(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "•" * len(plain)
    return f"{plain[:4]}{'•' * 6}{plain[-4:]}"


# ----------------------------- Object Storage -----------------------
# Provider-neutral storage: STORAGE_BACKEND=remote (Emergent, default — preserves
# the web preview) or STORAGE_BACKEND=local (Windows-safe filesystem for desktop).
import re
import mimetypes

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "akasha-forge"

STORAGE_BACKEND = (os.environ.get("STORAGE_BACKEND") or "remote").strip().lower()
AKASHA_DATA_DIR = Path(os.environ.get("AKASHA_DATA_DIR") or (ROOT_DIR / "akasha-data"))
STORAGE_ROOT = AKASHA_DATA_DIR / "storage"

_CANONICAL = {"images", "videos", "audio", "music", "documents", "thumbnails", "exports"}
_LAYOUT = [
    STORAGE_ROOT / "akasha-forge" / "images",
    STORAGE_ROOT / "akasha-forge" / "videos",
    STORAGE_ROOT / "akasha-forge" / "audio",
    STORAGE_ROOT / "akasha-forge" / "music",
    STORAGE_ROOT / "akasha-forge" / "documents",
    STORAGE_ROOT / "akasha-forge" / "thumbnails",
    STORAGE_ROOT / "akasha-forge" / "exports",
    AKASHA_DATA_DIR / "projects",
    AKASHA_DATA_DIR / "cache",
    AKASHA_DATA_DIR / "logs",
]

_storage_key = None


# ----- helpers (local) -----
def _canonical_category(content_type: str, hint: str) -> str:
    ct = (content_type or "").lower()
    hint = (hint or "").lower()
    if ct.startswith("image/"):
        return "thumbnails" if "thumb" in hint else "images"
    if ct.startswith("video/"):
        return "videos"
    if ct.startswith("audio/"):
        return "music" if "music" in hint else "audio"
    for c in _CANONICAL:
        if c in hint:
            return c
    if "thumb" in hint:
        return "thumbnails"
    if "export" in hint:
        return "exports"
    return "documents"


def _resolve_within(root: Path, rel: str) -> Path:
    """Join `rel` under `root`, rejecting any path-traversal. Windows-safe."""
    parts = [p for p in re.split(r"[\\/]+", str(rel)) if p and p != "."]
    for p in parts:
        if p == "..":
            raise ValueError("Path traversal rejected")
    safe = [re.sub(r"[^A-Za-z0-9._-]", "_", p) for p in parts]
    if not safe:
        raise ValueError("Empty object path")
    root_res = root.resolve()
    target = root.joinpath(*safe).resolve()
    if target != root_res and not str(target).startswith(str(root_res) + os.sep):
        raise ValueError("Path escapes storage root")
    return target


def _ensure_local_dirs():
    for d in _LAYOUT:
        d.mkdir(parents=True, exist_ok=True)


# ----- remote backend (existing Emergent behaviour, unchanged) -----
def _remote_init(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _remote_put(path: str, data: bytes, content_type: str) -> dict:
    key = _remote_init()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code == 404:
        key = _remote_init(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _remote_get(path: str):
    key = _remote_init()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = _remote_init(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def _remote_delete(path: str) -> bool:
    key = _remote_init()
    resp = requests.delete(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    return resp.status_code < 300


# ----- local backend (filesystem) -----
def _local_put(path: str, data: bytes, content_type: str) -> dict:
    parts = [p for p in re.split(r"[\\/]+", str(path)) if p and p != "."]
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", parts[-1]) if parts else new_id()
    hint = parts[-2] if len(parts) >= 2 else ""
    canonical = _canonical_category(content_type, hint)
    rel = f"akasha-forge/{canonical}/{filename}"
    abs_path = _resolve_within(STORAGE_ROOT, rel)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = abs_path.with_name(abs_path.name + f".{uuid.uuid4().hex}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, abs_path)  # atomic within the same filesystem
    return {"path": rel, "size": len(data)}


def _local_stream(path: str):
    abs_path = _resolve_within(STORAGE_ROOT, path)
    if not abs_path.is_file():
        raise FileNotFoundError(path)
    ct, _ = mimetypes.guess_type(str(abs_path))

    def _gen():
        with open(abs_path, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                yield chunk

    return _gen(), ct or "application/octet-stream"


# ----------------------------- Public storage API -----------------------------
def init_storage(force: bool = False):
    if STORAGE_BACKEND == "local":
        _ensure_local_dirs()
        return "local"
    return _remote_init(force=force)


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_BACKEND == "local":
        return _local_put(path, data, content_type)
    return _remote_put(path, data, content_type)


def get_object(path: str):
    if STORAGE_BACKEND == "local":
        abs_path = _resolve_within(STORAGE_ROOT, path)
        if not abs_path.is_file():
            raise FileNotFoundError(path)
        ct, _ = mimetypes.guess_type(str(abs_path))
        return abs_path.read_bytes(), ct or "application/octet-stream"
    return _remote_get(path)


def get_object_stream(path: str):
    """Return (byte iterator, content_type). Local streams from disk; remote yields one blob."""
    if STORAGE_BACKEND == "local":
        return _local_stream(path)
    data, ct = _remote_get(path)
    return iter([data]), ct


def delete_object(path: str) -> bool:
    if STORAGE_BACKEND == "local":
        abs_path = _resolve_within(STORAGE_ROOT, path)
        if abs_path.is_file():
            abs_path.unlink()
            return True
        return False
    return _remote_delete(path)


def object_exists(path: str) -> bool:
    try:
        if STORAGE_BACKEND == "local":
            return _resolve_within(STORAGE_ROOT, path).is_file()
        _remote_get(path)
        return True
    except Exception:
        return False


def get_object_metadata(path: str) -> dict:
    if STORAGE_BACKEND == "local":
        abs_path = _resolve_within(STORAGE_ROOT, path)
        if not abs_path.is_file():
            return {}
        stat = abs_path.stat()
        ct, _ = mimetypes.guess_type(str(abs_path))
        return {"relative_path": path, "size_bytes": stat.st_size,
                "mime_type": ct or "application/octet-stream", "storage_backend": "local"}
    return {"relative_path": path, "storage_backend": "remote"}


def resolve_object_path(path: str):
    """Absolute Path for local objects (validated); None for remote (never expose fs paths)."""
    if STORAGE_BACKEND == "local":
        return _resolve_within(STORAGE_ROOT, path)
    return None

