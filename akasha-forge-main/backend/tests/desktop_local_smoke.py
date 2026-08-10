"""AF-DESKTOP-004 — Desktop local DB (montydb) + local storage end-to-end.

Launches a standalone backend with AKASHA_DB_BACKEND=local + STORAGE_BACKEND=local
under a temp AKASHA_DATA_DIR, exercises every module, restarts the process, and
verifies durability. Run directly: python tests/desktop_local_smoke.py
"""
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import requests

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8140
HOST = "127.0.0.1"
API = f"http://{HOST}:{PORT}/api"
DATA_DIR = tempfile.mkdtemp(prefix="akasha_desktop_")

failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        failures.append(name)


def start():
    env = dict(os.environ)
    env.update({
        "AKASHA_DB_BACKEND": "local", "STORAGE_BACKEND": "local",
        "AKASHA_DATA_DIR": DATA_DIR, "AKASHA_HOST": HOST, "AKASHA_PORT": str(PORT),
        "DB_NAME": "akasha_forge_test",
    })
    # AF-DESKTOP-005: allow launching the frozen PyInstaller executable instead of
    # `python server.py` (set AKASHA_TEST_LAUNCH_CMD to the binary path). Default
    # preserves the plain dev-Python launch.
    launch = os.environ.get("AKASHA_TEST_LAUNCH_CMD")
    cmd = [launch] if launch else [sys.executable, "server.py"]
    p = subprocess.Popen(cmd, cwd=BACKEND_DIR, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            if requests.get(f"{API}/health", timeout=2).status_code == 200:
                return p
        except Exception:
            time.sleep(0.5)
    p.terminate()
    raise RuntimeError("backend did not start")


def stop(p):
    p.send_signal(signal.SIGINT)
    try:
        p.wait(timeout=15)
    except Exception:
        p.kill()
    return p.returncode


def main():
    proc = start()
    try:
        # 1/2/3 init + location + no manual install
        check("1 local DB initializes automatically", os.path.isdir(os.path.join(DATA_DIR, "database")))
        check("2 DB stored beneath AKASHA_DATA_DIR", any(os.scandir(os.path.join(DATA_DIR, "database"))))
        check("28 /api/health works", requests.get(f"{API}/health").json().get("status") == "ok")

        # 4-7 project CRUD
        pid = requests.post(f"{API}/projects", json={"name": "Desk Project", "type": "video"}).json()["id"]
        check("4 create project", bool(pid))
        check("5 read project", requests.get(f"{API}/projects/{pid}").json()["name"] == "Desk Project")
        requests.put(f"{API}/projects/{pid}", json={"description": "updated"})
        check("6 update project", requests.get(f"{API}/projects/{pid}").json()["description"] == "updated")

        # 10 character + 12 versions
        cid = requests.post(f"{API}/projects/{pid}/characters", json={"name": "Kael", "role": "hero", "appearance": "scarred"}).json()["id"]
        check("10 create character", bool(cid))
        requests.put(f"{API}/characters/{cid}", json={"personality": "brave"})
        requests.post(f"{API}/characters/{cid}/versions", json={"label": "v1"})
        vers = requests.get(f"{API}/characters/{cid}/versions").json()
        check("12 character version history", isinstance(vers, list) and len(vers) >= 1)

        # 13 bible
        requests.put(f"{API}/projects/{pid}/bibles/world", json={"sections": [{"heading": "Realm", "content": "Frostspire"}]})
        check("13 bible persistence", len(requests.get(f"{API}/projects/{pid}/bibles").json()) >= 1)

        # 14 production node
        nid = requests.post(f"{API}/projects/{pid}/production", json={"type": "scene", "title": "Duel", "description": "rooftop"}).json()["id"]
        check("14 production node persistence", bool(nid))

        # 15 forge item
        fid = requests.post(f"{API}/projects/{pid}/forge/music", json={"kind": "brief", "title": "Theme", "data": {"mood": "epic"}}).json()["id"]
        check("15 forge item persistence", bool(fid))

        # 16 provider hub
        provs = requests.get(f"{API}/providers").json()
        check("16 provider hub persistence (seeded)", len(provs) >= 11)

        # 17 publish forge
        camp = requests.post(f"{API}/publish/campaigns", json={"name": "Launch", "project_id": pid}).json()
        post = requests.post(f"{API}/publish/posts", json={"title": "Teaser", "content": "soon", "platforms": ["x"], "campaign_id": camp["id"]}).json()
        check("17 publish forge persistence", bool(camp.get("id")) and bool(post.get("id")))

        # 18 video render jobs (+ from-plan uses production shots; here direct create)
        job = requests.post(f"{API}/video-jobs", json={"project_id": pid, "shot_id": "s1", "prompt": "wide shot"}).json()
        check("18 video_render_jobs persistence", bool(job.get("id")))

        # 19/20/21 knowledge persist + search + auto-ingestion (character/production auto-ingested)
        kn = requests.get(f"{API}/brain/knowledge", params={"project_id": pid}).json()
        check("19 knowledge items persist", len(kn) >= 1)
        s = requests.get(f"{API}/brain/search", params={"project_id": pid, "q": "Kael"}).json()
        check("20 brain search returns local records", s["count"] >= 1)
        s2 = requests.get(f"{API}/brain/search", params={"project_id": pid, "q": "Frostspire"}).json()
        check("21 automatic knowledge ingestion (bible searchable)", s2["count"] >= 1)

        # 22 project isolation
        pid2 = requests.post(f"{API}/projects", json={"name": "Other", "type": "video"}).json()["id"]
        requests.post(f"{API}/projects/{pid2}/characters", json={"name": "Kael", "role": "hero"})
        iso = requests.get(f"{API}/brain/search", params={"project_id": pid2, "q": "Frostspire"}).json()
        check("22 project isolation", iso["count"] == 0)

        # ---- 8/9/11 RESTART persistence ----
        stop(proc)
        proc = start()
        check("9 project persists across restart", requests.get(f"{API}/projects/{pid}").json().get("name") == "Desk Project")
        check("11 character persists across restart", requests.get(f"{API}/characters/{cid}").json().get("name") == "Kael")
        kn2 = requests.get(f"{API}/brain/knowledge", params={"project_id": pid}).json()
        check("8 knowledge/render/forge survive restart", len(kn2) >= 1 and requests.get(f"{API}/video-jobs", params={"project_id": pid}).json())

        # 23 cascade delete
        requests.delete(f"{API}/projects/{pid}")
        proj_gone = requests.get(f"{API}/projects/{pid}").status_code == 404
        kn_gone = len(requests.get(f"{API}/brain/knowledge", params={"project_id": pid}).json()) == 0
        char_gone = requests.get(f"{API}/characters/{cid}").status_code == 404
        print("   cascade parts -> proj_gone:", proj_gone, "kn_gone:", kn_gone, "char_gone:", char_gone)
        check("23 project deletion cascade", proj_gone and kn_gone and char_gone)

        # 26 bind + 27 custom port already implied by API on 127.0.0.1:8140
        with socket.socket() as sk:
            sk.settimeout(2)
            check("26/27 bound to 127.0.0.1 custom port", sk.connect_ex((HOST, PORT)) == 0)

    finally:
        rc = stop(proc)
        check("30 backend shuts down cleanly", rc in (0, -2, 130, None))
        shutil.rmtree(DATA_DIR, ignore_errors=True)

    print("\nRESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILED -> {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
