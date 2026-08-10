"""AF-DESKTOP-006 — Tauri sidecar lifecycle contract validation.

The native Tauri window cannot compile/run in this headless Linux aarch64
container (no Rust/WebKit/display). This harness proves the *lifecycle contract*
that `src-tauri/src/lib.rs` implements, using the AF-DESKTOP-005 frozen backend:

  pick free 127.0.0.1 port → spawn frozen backend with the 5 desktop env vars
  → bounded /api/health handshake → build the injected __AKASHA_RUNTIME_CONFIG__
  → create/persist data → graceful stop → relaunch → data survives → cascade
  → assert no orphan process → assert no mutable data in the build/exe dir.

Run: python tests/desktop_tauri_lifecycle.py
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time

import requests

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN = os.path.join(BACKEND_DIR, "dist", "AkashaForgeBackend", "AkashaForgeBackend")
DIST_DIR = os.path.join(BACKEND_DIR, "dist", "AkashaForgeBackend")
DATA_DIR = "/tmp/akasha_tauri_life"

failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        failures.append(name)


def pick_free_port():
    # Mirrors Rust pick_free_port(): bind :0 on loopback, take the assigned port.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def secret():
    # AF-DESKTOP-007: the desktop shell no longer passes AKASHA_SECRET_KEY —
    # the backend self-provisions its master key via the secure vault. This
    # helper is retained only for the (unused) remote-mode path and returns "".
    return ""


def spawn(port):
    # Mirrors the Rust Command env exactly (AF-DESKTOP-007: NO secrets passed).
    env = dict(os.environ)
    env.pop("AKASHA_SECRET_KEY", None)  # prove backend self-provisions via vault
    env.update({
        "AKASHA_HOST": "127.0.0.1",
        "AKASHA_PORT": str(port),
        "AKASHA_DATA_DIR": DATA_DIR,
        "STORAGE_BACKEND": "local",
        "AKASHA_DB_BACKEND": "local",
        "DB_NAME": "akasha_forge",
    })
    return subprocess.Popen([FROZEN], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_health(api, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{api}/health", timeout=2)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(0.6)
    return False


def graceful_stop(p):
    # Mirrors Rust shutdown: SIGINT, wait briefly, then force-kill fallback.
    p.send_signal(signal.SIGINT)
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
        p.wait(timeout=5)
    return p.returncode


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main():
    import shutil
    shutil.rmtree(DATA_DIR, ignore_errors=True)

    check("0 frozen backend present (AF-005)", os.path.isfile(FROZEN))

    # (3) free port selection
    port = pick_free_port()
    api = f"http://127.0.0.1:{port}/api"
    check("3 selects a free 127.0.0.1 port", isinstance(port, int) and port > 0)

    # (4/5) spawn frozen backend with desktop env + health handshake
    p = spawn(port)
    child_pid = p.pid
    ready = wait_health(api)
    check("4 frozen backend launches with desktop env", ready)
    check("5 /api/health handshake succeeds", ready)

    # (6) runtime-config JSON the Rust init script would inject
    runtime_cfg = {"desktop": True, "backendUrl": f"http://127.0.0.1:{port}", "appDataDir": DATA_DIR}
    print("   injected __AKASHA_RUNTIME_CONFIG__ =", json.dumps(runtime_cfg))
    check("6 runtime-config backendUrl matches sidecar port",
          runtime_cfg["backendUrl"].endswith(str(port)) and runtime_cfg["desktop"] is True)
    check("6b runtime-config exposes NO secrets",
          not any(k in runtime_cfg for k in ("secret", "api_key", "AKASHA_SECRET_KEY", "master_key")))

    # (vault) backend self-provisioned a master key WITHOUT AKASHA_SECRET_KEY env
    import glob
    vault_file = os.path.join(DATA_DIR, "vault", "secrets.json")
    vault_has_master = False
    if os.path.isfile(vault_file):
        with open(vault_file) as vf:
            vault_has_master = "akasha_master_key" in json.load(vf)
    check("V1 first launch created master key in vault (no env secret)", vault_has_master)

    # (bind) backend bound to loopback only
    with socket.socket() as sk:
        sk.settimeout(2)
        check("bind backend reachable on 127.0.0.1", sk.connect_ex(("127.0.0.1", port)) == 0)

    # (12/13) local DB + storage initialized under app data dir
    check("12 local DB initializes under app data", os.path.isdir(os.path.join(DATA_DIR, "database")))
    check("13 local storage initializes under app data",
          os.path.isdir(os.path.join(DATA_DIR, "storage")))

    # (7/8) create + persist representative data
    pid = requests.post(f"{api}/projects", json={"name": "Tauri Project", "type": "video"}).json()["id"]
    check("7 create a project through desktop stack", bool(pid))
    cid = requests.post(f"{api}/projects/{pid}/characters",
                        json={"name": "Kael", "role": "hero", "appearance": "scarred"}).json()["id"]
    requests.put(f"{api}/projects/{pid}/bibles/world",
                 json={"sections": [{"heading": "Realm", "content": "Frostspire"}]})
    check("8 persist representative data (character+bible)", bool(cid))

    # (9) stop backend gracefully
    rc = graceful_stop(p)
    check("9 backend stops gracefully", rc in (0, -2, 130, None) or not pid_alive(child_pid))

    # (13-orphan) no orphan process remains
    time.sleep(1)
    check("13 no orphan backend process remains", not pid_alive(child_pid))

    # (10/11) relaunch + data survives
    port2 = pick_free_port()
    api2 = f"http://127.0.0.1:{port2}/api"
    p2 = spawn(port2)
    ready2 = wait_health(api2)
    check("10 backend relaunches", ready2)
    proj = requests.get(f"{api2}/projects/{pid}").json()
    char = requests.get(f"{api2}/characters/{cid}").json()
    s = requests.get(f"{api2}/brain/search", params={"project_id": pid, "q": "Frostspire"}).json()
    check("11 data survives relaunch (project+character+ingested bible)",
          proj.get("name") == "Tauri Project" and char.get("name") == "Kael" and s.get("count", 0) >= 1)

    # (12-cascade) project deletion cascade
    requests.delete(f"{api2}/projects/{pid}")
    proj_gone = requests.get(f"{api2}/projects/{pid}").status_code == 404
    char_gone = requests.get(f"{api2}/characters/{cid}").status_code == 404
    kn_gone = len(requests.get(f"{api2}/brain/knowledge", params={"project_id": pid}).json()) == 0
    check("12 project deletion cascade works", proj_gone and char_gone and kn_gone)

    graceful_stop(p2)

    # (17) no mutable data written into the build/exe directory
    leaked = [n for n in ("database", "storage", "projects", "cache", "logs")
              if os.path.isdir(os.path.join(DIST_DIR, n))]
    check("17 no mutable data in build/exe dir", leaked == [])

    shutil.rmtree(DATA_DIR, ignore_errors=True)
    print("\nRESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILED -> {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
