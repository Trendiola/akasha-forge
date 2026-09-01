"""AF-DESKTOP-007 — secret vault + master-key lifecycle + migration tests.

Runs the real `core` module in subprocesses (it resolves the master key at
import) under a temp AKASHA_DATA_DIR with the DEV file vault backend, and
exercises `secret_vault` directly. No secret values are printed.
"""
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _base_env(data_dir, with_env_secret=None):
    env = dict(os.environ)
    # core.py calls load_dotenv(backend/.env) which would re-inject the dev
    # AKASHA_SECRET_KEY (dotenv override=False won't overwrite an existing var),
    # so we pin it to "" to force the vault path — mirroring the frozen desktop
    # bundle, which ships no .env beside it.
    env["AKASHA_SECRET_KEY"] = "" if with_env_secret is None else with_env_secret
    env.update({
        "AKASHA_DATA_DIR": str(data_dir),
        "AKASHA_DB_BACKEND": "local",
        "STORAGE_BACKEND": "local",
        "AKASHA_VAULT_BACKEND": "file",
        "DB_NAME": "akasha_vault_test",
    })
    return env


def _run_core(data_dir, code, with_env_secret=None):
    script = "import core\n" + code
    return subprocess.run(
        [sys.executable, "-c", script], cwd=str(BACKEND_DIR),
        env=_base_env(data_dir, with_env_secret), capture_output=True, text=True,
    )


def _vault_master(data_dir):
    f = Path(data_dir) / "vault" / "secrets.json"
    if not f.exists():
        return None
    return json.loads(f.read_text()).get("akasha_master_key")


@pytest.fixture
def data_dir():
    d = tempfile.mkdtemp(prefix="akasha_vault_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ------------------------------ vault ops ------------------------------ #
def test_vault_file_ops(data_dir):
    env = _base_env(data_dir)
    code = (
        "import secret_vault as v;"
        "print('KIND', v.backend_kind());"
        "print('EXISTS0', v.secret_exists('provider:p1:api_key'));"
        "v.set_secret('provider:p1:api_key','sk-abc');"
        "print('EXISTS1', v.secret_exists('provider:p1:api_key'));"
        "print('GET', v.get_secret('provider:p1:api_key'));"
        "v.delete_secret('provider:p1:api_key');"
        "print('EXISTS2', v.secret_exists('provider:p1:api_key'))"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(BACKEND_DIR),
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "KIND file" in out
    assert "EXISTS0 False" in out and "EXISTS1 True" in out and "EXISTS2 False" in out
    assert "GET sk-abc" in out
    # 0600 perms on the vault file
    vf = Path(data_dir) / "vault" / "secrets.json"
    if os.name != "nt":
        assert oct(vf.stat().st_mode & 0o777) == "0o600"


# --------------------- master-key lifecycle ---------------------------- #
def test_master_key_generated_and_persists_across_restart(data_dir):
    # launch 1: no env secret, no vault -> generate + store; encrypt a token
    r1 = _run_core(data_dir, "print('TOKEN', core.encrypt('hello-akasha'))")
    assert r1.returncode == 0, r1.stderr
    token = [l for l in r1.stdout.splitlines() if l.startswith("TOKEN ")][0].split(" ", 1)[1]
    key1 = _vault_master(data_dir)
    assert key1, "master key must be stored in vault on first launch"

    # launch 2 (restart): same data_dir -> reuse key, decrypt token from launch 1
    r2 = _run_core(data_dir, f"print('PLAIN', core.decrypt({token!r}))")
    assert r2.returncode == 0, r2.stderr
    assert "PLAIN hello-akasha" in r2.stdout
    assert _vault_master(data_dir) == key1, "master key must NOT be regenerated"


def test_env_secret_takes_precedence_and_skips_vault(data_dir):
    env_key = Fernet.generate_key().decode()
    r = _run_core(data_dir, "print('OK')", with_env_secret=env_key)
    assert r.returncode == 0, r.stderr
    # env path must not touch the vault at all
    assert _vault_master(data_dir) is None


# ------------------------------ migration ------------------------------ #
def test_migration_success_then_plaintext_removed(data_dir):
    # A provider key was encrypted earlier with the temp .akasha_secret key.
    old_key = Fernet.generate_key().decode()
    provider_token = Fernet(old_key.encode()).encrypt(b"sk-provider-123").decode()
    (Path(data_dir)).mkdir(parents=True, exist_ok=True)
    (Path(data_dir) / ".akasha_secret").write_text(old_key)

    r = _run_core(data_dir, f"print('PLAIN', core.decrypt({provider_token!r}))")
    assert r.returncode == 0, r.stderr
    # migrated key can still decrypt the pre-existing provider secret
    assert "PLAIN sk-provider-123" in r.stdout
    # vault now holds the migrated key, and the plaintext file is gone
    assert _vault_master(data_dir) == old_key
    assert not (Path(data_dir) / ".akasha_secret").exists()


def test_failed_migration_keeps_plaintext_untouched(data_dir):
    (Path(data_dir)).mkdir(parents=True, exist_ok=True)
    (Path(data_dir) / ".akasha_secret").write_text("not-a-valid-fernet-key")
    r = _run_core(data_dir, "print('OK')")
    assert r.returncode == 0, r.stderr
    # invalid file must be left untouched (never deleted on failed migration)
    assert (Path(data_dir) / ".akasha_secret").read_text() == "not-a-valid-fernet-key"


# ------------------------------ masking -------------------------------- #
def test_masking_preserved(data_dir):
    r = _run_core(data_dir, "print('MASK', core.mask_key('sk-1234567890abcd'))")
    assert r.returncode == 0, r.stderr
    line = [l for l in r.stdout.splitlines() if l.startswith("MASK ")][0]
    masked = line.split(" ", 1)[1]
    assert masked.startswith("sk-1") and masked.endswith("abcd") and "•" in masked
    assert "567890" not in masked  # middle is hidden


# ---------------------- no plaintext secret in source ------------------ #
def test_no_hardcoded_key_in_source():
    src = (BACKEND_DIR / "core.py").read_text() + (BACKEND_DIR / "secret_vault.py").read_text()
    # generation must be via cryptography, and there must be no os.environ[...] hard require
    assert "Fernet.generate_key()" in src
    assert 'os.environ["AKASHA_SECRET_KEY"]' not in src
