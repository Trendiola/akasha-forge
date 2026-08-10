"""AF-PRODUCTION-001 — end-to-end production orchestrator + audio/subtitles + master."""
import os
import subprocess
import tempfile
import uuid

import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")).rstrip("/") + "/api"


def _project():
    return requests.post(f"{BASE_URL}/projects", json={"name": f"Prod {uuid.uuid4().hex[:6]}", "type": "video"}).json()["id"]


def _shot(pid, title):
    return requests.post(f"{BASE_URL}/projects/{pid}/production", json={"type": "shot", "title": title}).json()["id"]


def _provider(kind="test", enabled=True, api_key="k-123"):
    return requests.post(f"{BASE_URL}/providers", json={
        "name": f"P {uuid.uuid4().hex[:6]}", "category": "video", "kind": kind,
        "api_key": api_key, "default_model": "test-model", "enabled": enabled}).json()


def _clip(color, wd, name):
    p = os.path.join(wd, name)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x240:d=1",
                    "-r", "24", "-pix_fmt", "yuv420p", p], capture_output=True, check=True, timeout=60)
    return p


def _audio(freq, wd, name):
    p = os.path.join(wd, name)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=3",
                    "-c:a", "aac", p], capture_output=True, check=True, timeout=60)
    return p


def _upload(path, category):
    with open(path, "rb") as fh:
        return requests.post(f"{BASE_URL}/files/upload",
                             files={"file": (os.path.basename(path), fh, "application/octet-stream")},
                             data={"category": category}).json()["id"]


def _completed_job(pid, shot_id, asset_id, narration=""):
    j = requests.post(f"{BASE_URL}/video-jobs", json={
        "project_id": pid, "shot_id": shot_id, "prompt": "x", "duration_seconds": 1,
        "narration_text": narration}).json()
    requests.put(f"{BASE_URL}/video-jobs/{j['id']}",
                 json={"status": "completed", "progress": 100, "result_asset_id": asset_id})
    return j["id"]


def _cleanup(pids):
    for pid in pids:
        try:
            requests.delete(f"{BASE_URL}/providers/{pid}")
        except Exception:
            pass


def _ffprobe_streams(path, kind):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", kind,
                        "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True, timeout=30)
    return [l for l in r.stdout.strip().splitlines() if l.strip()]


# --- orchestration advancement + idempotency (test adapter, no export) ------ #
def test_orchestrator_advances_and_is_idempotent():
    prov = _provider()
    try:
        pid = _project()
        j1 = requests.post(f"{BASE_URL}/video-jobs", json={"project_id": pid, "provider_id": prov["id"], "prompt": "a", "shot_id": "s1"}).json()
        j2 = requests.post(f"{BASE_URL}/video-jobs", json={"project_id": pid, "provider_id": prov["id"], "prompt": "b", "shot_id": "s2"}).json()

        status = None
        for _ in range(6):
            status = requests.post(f"{BASE_URL}/video-projects/{pid}/produce",
                                   json={"auto_export": False}).json()
            if status["completed"] == 2:
                break
        assert status["completed"] == 2, status
        assert status["ready_for_export"] is True
        assert status["status"] == "ready_for_export"

        # snapshot completed jobs, then produce again -> must NOT re-render
        before = {x["id"]: (x["provider_job_id"], x.get("result_asset_id"))
                  for x in requests.get(f"{BASE_URL}/video-jobs", params={"project_id": pid}).json()}
        requests.post(f"{BASE_URL}/video-projects/{pid}/produce", json={"auto_export": False})
        after = {x["id"]: (x["provider_job_id"], x.get("result_asset_id"))
                 for x in requests.get(f"{BASE_URL}/video-jobs", params={"project_id": pid}).json()}
        assert before == after, "completed jobs must not be re-rendered on re-produce"
    finally:
        _cleanup([prov["id"]])


def test_failed_shot_blocks_finalize():
    prov = _provider()
    try:
        pid = _project()
        # a failed job via the test adapter
        jf = requests.post(f"{BASE_URL}/video-jobs", json={"project_id": pid, "provider_id": prov["id"], "model": "fail-submit", "prompt": "x", "shot_id": "s1"}).json()
        requests.post(f"{BASE_URL}/video-jobs/{jf['id']}/queue")
        requests.post(f"{BASE_URL}/video-jobs/{jf['id']}/execute")
        st = requests.post(f"{BASE_URL}/video-projects/{pid}/produce", json={"auto_export": True}).json()
        assert st["failed"] >= 1
        assert st["ready_for_export"] is False
        assert st["final_asset_id"] == ""
        assert st["status"] == "failed"
    finally:
        _cleanup([prov["id"]])


# --- full master with real clips + audio + subtitles ------------------------ #
def test_full_master_with_audio_and_subtitles():
    wd = tempfile.mkdtemp()
    pid = _project()
    s0, s1, s2 = _shot(pid, "A"), _shot(pid, "B"), _shot(pid, "C")
    a0 = _upload(_clip("red", wd, "0.mp4"), "videos")
    a1 = _upload(_clip("green", wd, "1.mp4"), "videos")
    a2 = _upload(_clip("blue", wd, "2.mp4"), "videos")
    # jobs created in reverse; narration text set per shot
    _completed_job(pid, s2, a2, "Line C")
    _completed_job(pid, s0, a0, "Line A")
    _completed_job(pid, s1, a1, "Line B")
    narr = _upload(_audio(440, wd, "narr.m4a"), "audio")
    music = _upload(_audio(220, wd, "music.m4a"), "music")

    out = requests.post(f"{BASE_URL}/video-projects/{pid}/produce", json={
        "narration_asset_id": narr, "music_asset_id": music, "subtitles": True, "auto_export": True}).json()
    assert out["status"] == "completed", out
    assert out["final_asset_id"]
    assert out["subtitle_asset_id"], "an SRT should be produced"

    # production-status is derived from records (restart-safe reconstruction)
    st = requests.get(f"{BASE_URL}/video-projects/{pid}/production-status").json()
    assert st["status"] == "completed"
    assert st["final_asset_id"] == out["final_asset_id"]

    # final master has a valid audio + video stream, ~3s
    served = requests.get(f"{BASE_URL}/files/{out['final_asset_id']}")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(served.content)
        fp = tf.name
    assert len(_ffprobe_streams(fp, "v")) == 1
    assert len(_ffprobe_streams(fp, "a")) >= 1  # narration+music mixed
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", fp],
                         capture_output=True, text=True, timeout=30)
    assert 2.4 <= float(dur.stdout.strip()) <= 4.2
    os.unlink(fp)

    # SRT follows shot order A, B, C
    srt = requests.get(f"{BASE_URL}/files/{out['subtitle_asset_id']}").text
    ia, ib, ic = srt.find("Line A"), srt.find("Line B"), srt.find("Line C")
    assert -1 < ia < ib < ic, srt


def test_video_only_master():
    wd = tempfile.mkdtemp()
    pid = _project()
    s0, s1, s2 = _shot(pid, "A"), _shot(pid, "B"), _shot(pid, "C")
    for i, c in enumerate(("red", "green", "blue")):
        aid = _upload(_clip(c, wd, f"{i}.mp4"), "videos")
        _completed_job(pid, [s0, s1, s2][i], aid)
    out = requests.post(f"{BASE_URL}/video-projects/{pid}/produce", json={
        "subtitles": False, "auto_export": True}).json()
    assert out["status"] == "completed"
    served = requests.get(f"{BASE_URL}/files/{out['final_asset_id']}")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(served.content)
        fp = tf.name
    assert len(_ffprobe_streams(fp, "v")) == 1
    assert len(_ffprobe_streams(fp, "a")) == 0  # video-only master
    os.unlink(fp)


def test_no_render_jobs():
    pid = _project()
    r = requests.post(f"{BASE_URL}/video-projects/{pid}/produce", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "NO_RENDER_JOBS"
