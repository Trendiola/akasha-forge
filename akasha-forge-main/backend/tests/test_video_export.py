"""AF-VIDEO-003 — final multi-shot MP4 assembly (smallest real vertical slice)."""
import os
import subprocess
import tempfile
import uuid

import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")).rstrip("/") + "/api"


def _mk_project():
    r = requests.post(f"{BASE_URL}/projects", json={"name": f"Export {uuid.uuid4().hex[:6]}", "type": "video"})
    r.raise_for_status()
    return r.json()["id"]


def _mk_shot(project_id, title):
    r = requests.post(f"{BASE_URL}/projects/{project_id}/production",
                      json={"type": "shot", "title": title})
    r.raise_for_status()
    return r.json()["id"]


def _make_clip(color, workdir, name):
    path = os.path.join(workdir, name)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x240:d=1",
         "-r", "24", "-pix_fmt", "yuv420p", path],
        capture_output=True, check=True, timeout=60,
    )
    return path


def _upload(path):
    with open(path, "rb") as fh:
        r = requests.post(f"{BASE_URL}/files/upload",
                          files={"file": (os.path.basename(path), fh, "video/mp4")},
                          data={"category": "videos"})
    r.raise_for_status()
    return r.json()["id"]


def _completed_job(project_id, shot_id, asset_id):
    j = requests.post(f"{BASE_URL}/video-jobs", json={
        "project_id": project_id, "shot_id": shot_id, "prompt": "x", "duration_seconds": 1}).json()
    requests.put(f"{BASE_URL}/video-jobs/{j['id']}",
                 json={"status": "completed", "progress": 100, "result_asset_id": asset_id})
    return j["id"]


def test_full_video_export_orders_and_assembles():
    workdir = tempfile.mkdtemp()
    project = _mk_project()
    # shots created in film order -> orders 0,1,2
    s0 = _mk_shot(project, "Shot A")
    s1 = _mk_shot(project, "Shot B")
    s2 = _mk_shot(project, "Shot C")
    a0 = _upload(_make_clip("red", workdir, "a.mp4"))
    a1 = _upload(_make_clip("green", workdir, "b.mp4"))
    a2 = _upload(_make_clip("blue", workdir, "c.mp4"))
    # create jobs in REVERSE order to prove shot-order (not creation order) wins
    _completed_job(project, s2, a2)
    _completed_job(project, s0, a0)
    _completed_job(project, s1, a1)

    r = requests.post(f"{BASE_URL}/video-export", json={"project_id": project, "output_name": "My Movie"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "completed"
    assert out["clip_count"] == 3
    assert out["asset_id"] and out["filename"] == "My Movie.mp4"
    # order preserved by shot order, independent of job creation order
    assert out["clip_asset_ids"] == [a0, a1, a2]
    # duration ~= 3s (3 x 1s)
    assert 2.4 <= out["duration_seconds"] <= 3.8, out["duration_seconds"]

    # final movie is stored + served as video, and ffprobe-readable
    served = requests.get(f"{BASE_URL}/files/{out['asset_id']}")
    assert served.status_code == 200
    assert served.headers.get("Content-Type", "").startswith("video/")
    assert len(served.content) > 0
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(served.content)
        final_path = tf.name
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", final_path],
        capture_output=True, text=True, timeout=30)
    assert float(dur.stdout.strip()) > 0  # playable / probeable
    os.unlink(final_path)


def test_missing_clip_reports_clearly():
    workdir = tempfile.mkdtemp()
    project = _mk_project()
    s0 = _mk_shot(project, "Shot A")
    a0 = _upload(_make_clip("red", workdir, "a.mp4"))
    requests.delete(f"{BASE_URL}/files/{a0}")  # remove the underlying clip
    _completed_job(project, s0, a0)
    r = requests.post(f"{BASE_URL}/video-export", json={"project_id": project})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MISSING_CLIP"


def test_incomplete_job_blocks_export():
    workdir = tempfile.mkdtemp()
    project = _mk_project()
    s0 = _mk_shot(project, "Shot A")
    a0 = _upload(_make_clip("red", workdir, "a.mp4"))
    _completed_job(project, s0, a0)
    # add a still-processing job -> unsafe to export
    j = requests.post(f"{BASE_URL}/video-jobs", json={"project_id": project, "shot_id": "sX", "prompt": "y"}).json()
    requests.put(f"{BASE_URL}/video-jobs/{j['id']}", json={"status": "processing"})
    r = requests.post(f"{BASE_URL}/video-export", json={"project_id": project})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "EXPORT_BLOCKED_INCOMPLETE"


def test_no_jobs_reports_clearly():
    project = _mk_project()
    r = requests.post(f"{BASE_URL}/video-export", json={"project_id": project})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "NO_COMPLETED_JOBS"
