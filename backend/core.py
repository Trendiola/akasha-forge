"""Shared core: database, helpers, storage, encryption. Single source of truth."""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from cryptography.fernet import Fernet

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger("akasha")

# Desktop data root (shared with local file storage — AF-DESKTOP-003).
AKASHA_DATA_DIR = Path(os.environ.get("AKASHA_DATA_DIR") or (ROOT_DIR / "akasha-data"))

# ----------------------------- Database -----------------------------
# remote (default) = MongoDB via motor (Emergent/web preview, unchanged).
# local = self-contained montydb (SQLite) under <AKASHA_DATA_DIR>/database/ for desktop.
AKASHA_DB_BACKEND = (os.environ.get("AKASHA_DB_BACKEND") or "remote").strip().lower()

if AKASHA_DB_BACKEND == "local":
    from mongo_compat import make_local_db
    client, db = make_local_db(AKASHA_DATA_DIR, os.environ.get("DB_NAME", "akasha_forge"))
else:
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ["MONGO_URL"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ["DB_NAME"]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ----------------------------- Encryption ---------------------------
# Master-key resolution (AF-DESKTOP-007), in order:
#   1. AKASHA_SECRET_KEY env  → remote/web-preview & existing tests unchanged.
#   2. secure vault `akasha_master_key` (desktop; persisted across launches).
#   3. generate a new secure Fernet key, store it in the vault, reuse next time.
# The raw key is never logged and never exposed to the frontend/runtime config.
import secret_vault


def _valid_fernet_key(value: str) -> bool:
    try:
        Fernet((value or "").encode())
        return True
    except Exception:
        return False


def _migrate_akasha_secret_file() -> None:
    """One-time, safe migration of AF-006's temporary plaintext `.akasha_secret`.

    Only runs if the file exists AND the vault has no master key yet. Verifies a
    vault round-trip before deleting the plaintext file; on any failure the file
    is left untouched and provider credentials are never at risk.
    """
    secret_path = AKASHA_DATA_DIR / ".akasha_secret"
    try:
        if not secret_path.exists():
            return
        if secret_vault.secret_exists(secret_vault.MASTER_KEY_NAME):
            # Vault already provisioned — do not overwrite; only retire the file
            # if it is provably equivalent to the stored key.
            existing = (secret_path.read_text(encoding="utf-8") or "").strip()
            if existing and existing == secret_vault.get_secret(secret_vault.MASTER_KEY_NAME):
                secret_path.unlink()
                logger.info("Retired redundant .akasha_secret (matches vault master key).")
            return
        raw = (secret_path.read_text(encoding="utf-8") or "").strip()
        if not raw or not _valid_fernet_key(raw):
            logger.warning("Skipping .akasha_secret migration: file empty or not a valid key.")
            return
        secret_vault.set_secret(secret_vault.MASTER_KEY_NAME, raw)
        if secret_vault.get_secret(secret_vault.MASTER_KEY_NAME) != raw:
            logger.error("Master-key migration verification failed; keeping .akasha_secret.")
            return
        # Verified in vault → safe to remove the plaintext file.
        secret_path.unlink()
        logger.info("Migrated master key from .akasha_secret to secure vault; plaintext removed.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Master-key migration error (%s); leaving .akasha_secret untouched.", exc)


def _resolve_master_key() -> str:
    env_key = os.environ.get("AKASHA_SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    # Desktop/local: use the secure vault (migrate the temp file first if present).
    _migrate_akasha_secret_file()
    key = secret_vault.get_secret(secret_vault.MASTER_KEY_NAME)
    if key and _valid_fernet_key(key):
        return key
    key = Fernet.generate_key().decode()
    secret_vault.set_secret(secret_vault.MASTER_KEY_NAME, key)
    logger.info("Generated a new Akasha master key and stored it in the secure vault.")
    return key


_fernet = Fernet(_resolve_master_key().encode())


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


def backup_local_database() -> str:
    """Minimal backup foundation (local DB only): copy the sqlite DB dir into
    <AKASHA_DATA_DIR>/backups/<timestamp>/. No UI, no scheduling, no cloud."""
    if AKASHA_DB_BACKEND != "local":
        raise RuntimeError("backup_local_database only applies to the local database backend")
    import shutil
    src = AKASHA_DATA_DIR / "database"
    dest = AKASHA_DATA_DIR / "backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    return str(dest)

