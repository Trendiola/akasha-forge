"""AF-DESKTOP-007 — desktop secret vault (per-install secure secret storage).

A tiny abstraction with two backends:

- **keyring** (Windows production): OS-protected storage via the `keyring`
  library, backed by Windows Credential Manager (DPAPI). No custom crypto.
- **file** (Linux/Emergent DEV-ONLY fallback): a `0600` JSON file under
  ``<AKASHA_DATA_DIR>/vault/secrets.json``. This has **no OS-level protection**
  and must never be used in production — it exists only so the abstraction is
  exercisable where an OS keyring is unavailable (headless CI/dev).

Selection via ``AKASHA_VAULT_BACKEND=auto|keyring|file`` (default ``auto``):
- ``auto``  → use keyring if a working backend is available, else file fallback.
- ``keyring`` → require keyring; raise clearly if unavailable.
- ``file``  → force the dev file backend.

Rules: never log raw secret values; never return secrets to the frontend.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("akasha.vault")

_SERVICE = "com.akashaforge.desktop"


def _data_dir() -> Path:
    return Path(os.environ.get("AKASHA_DATA_DIR") or (Path(__file__).parent / "akasha-data"))


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #
class _KeyringVault:
    """OS keyring backend (Windows Credential Manager / DPAPI in production)."""

    kind = "keyring"

    def __init__(self):
        import keyring  # noqa: F401
        from keyring.errors import NoKeyringError  # noqa: F401

        self._keyring = keyring
        # Functional probe: the meta/chainer backend only reveals a missing OS
        # keyring at write time, so we round-trip a throwaway secret. Any failure
        # (e.g. no Secret Service / DPAPI) marks keyring unavailable so `auto`
        # can fall back to the dev file vault.
        probe = "__akasha_vault_probe__"
        try:
            keyring.set_password(_SERVICE, probe, "1")
            ok = keyring.get_password(_SERVICE, probe) == "1"
            try:
                keyring.delete_password(_SERVICE, probe)
            except Exception:
                pass
            if not ok:
                raise RuntimeError("keyring round-trip returned unexpected value")
            self._backend_name = type(keyring.get_keyring()).__name__
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"keyring backend unavailable: {exc}") from exc

    def get(self, name: str) -> Optional[str]:
        return self._keyring.get_password(_SERVICE, name)

    def set(self, name: str, value: str) -> None:
        self._keyring.set_password(_SERVICE, name, value)

    def delete(self, name: str) -> None:
        try:
            self._keyring.delete_password(_SERVICE, name)
        except Exception:
            # keyring raises PasswordDeleteError when absent — treat as no-op.
            pass

    def exists(self, name: str) -> bool:
        return self.get(name) is not None


class _FileVault:
    """DEV-ONLY fallback: 0600 JSON file. NOT OS-protected. Never for production."""

    kind = "file"

    def __init__(self):
        self._path = _data_dir() / "vault" / "secrets.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({})
        logger.warning(
            "Secret vault using DEV-ONLY file backend at %s — NOT OS-protected. "
            "Use a keyring/DPAPI backend for production Windows builds.",
            self._path,
        )

    def _read(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8") or "{}")
        except Exception:
            return {}

    def _write(self, data: dict) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except Exception:
            pass
        os.replace(tmp, self._path)
        try:
            os.chmod(self._path, 0o600)
        except Exception:
            pass

    def get(self, name: str) -> Optional[str]:
        return self._read().get(name)

    def set(self, name: str, value: str) -> None:
        data = self._read()
        data[name] = value
        self._write(data)

    def delete(self, name: str) -> None:
        data = self._read()
        if name in data:
            data.pop(name, None)
            self._write(data)

    def exists(self, name: str) -> bool:
        return name in self._read()


# --------------------------------------------------------------------------- #
# Backend selection (lazy singleton)
# --------------------------------------------------------------------------- #
_vault = None


def _select_backend():
    choice = (os.environ.get("AKASHA_VAULT_BACKEND") or "auto").strip().lower()
    if choice == "file":
        return _FileVault()
    if choice == "keyring":
        return _KeyringVault()  # raises clearly if unavailable
    # auto
    try:
        v = _KeyringVault()
        logger.info("Secret vault backend: keyring (%s)", getattr(v, "_backend_name", "?"))
        return v
    except Exception as exc:  # noqa: BLE001
        logger.info("Secret vault: keyring unavailable (%s) — using dev file fallback.", exc)
        return _FileVault()


def _get_vault():
    global _vault
    if _vault is None:
        _vault = _select_backend()
    return _vault


def backend_kind() -> str:
    """'keyring' or 'file' — for diagnostics/tests (never exposes secrets)."""
    return _get_vault().kind


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_secret(name: str) -> Optional[str]:
    return _get_vault().get(name)


def set_secret(name: str, value: str) -> None:
    _get_vault().set(name, value)


def delete_secret(name: str) -> None:
    _get_vault().delete(name)


def secret_exists(name: str) -> bool:
    return _get_vault().exists(name)


# Convenience secret-name builders (keeps naming consistent across the app).
MASTER_KEY_NAME = "akasha_master_key"


def provider_key_name(provider_id: str) -> str:
    return f"provider:{provider_id}:api_key"


def _reset_for_tests():
    """Test hook: drop the cached backend so a new AKASHA_DATA_DIR is picked up."""
    global _vault
    _vault = None
