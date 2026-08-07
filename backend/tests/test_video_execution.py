"""AF-VIDEO-002 — provider-neutral video execution path (deterministic test adapter).

Drives the full contract: create job -> queue -> execute (submit + provider_job_id)
-> refresh (progress) -> refresh (completed) -> stored clip + result_asset_id, plus
failure/retry/cancel, invalid transitions, and provider-resolution errors.
"""
import os
import uuid

import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")).rstrip("/") + "/api"


def _mk_project():
    r = requests.post(f"{BASE_URL}/projects", json={"name": f"VidExec {uuid.uuid4().hex[:6]}", "type": "video"})
    r.raise_for_status()
    return r.json()["id"]


def _mk_provider(enabled=True, kind="test", api_key="test-key-123", category="video"):
    r = requests.post(f"{BASE_URL}/providers", json={
        "name": f"TestVid {uuid.uuid4().hex[:6]}", "category": category, "kind": kind,
        "api_key": api_key, "default_model": "test-model", "enabled": enabled,
    })
    r.raise_for_status()
    return r.json()


def _mk_job(project_id, provider_id, model="test-model"):
    r = requests.post(f"{BASE_URL}/video-jobs", json={
        "project_id": project_id, "shot_id": f"shot-{uuid.uuid4().hex[:6]}",
        "provider_id": provider_id, "model": model, "prompt": "a neon city at dusk",
        "negative_prompt": "blurry", "duration_seconds": 8, "aspect_ratio": "16:9",
    })
    r.raise_for_status()
    return r.json()


def _cleanup(provider_ids):
    for pid in provider_ids:
        try:
            requests.delete(f"{BASE_URL}/providers/{pid}")
        except Exception:
            pass


# --------------------------- happy path -------------------------------- #
def test_full_execution_path_to_completed_asset():
    prov = _mk_provider()
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        assert job["status"] == "draft"

        # queue
        q = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue").json()
        assert q["status"] == "queued"

        # execute -> submitting -> processing, provider_job_id persisted
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute").json()
        assert ex["status"] == "processing", ex
        assert ex["provider_job_id"], "provider_job_id must persist after submit"
        pjid = ex["provider_job_id"]

        # refresh #1 -> still processing, progress persists
        r1 = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/refresh").json()
        assert r1["status"] == "processing" and r1["progress"] >= 0
        assert r1["provider_job_id"] == pjid  # survives (restart-resumable)

        # refresh #2 -> completed with a stored asset
        r2 = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/refresh").json()
        assert r2["status"] == "completed", r2
        assert r2["progress"] == 100
        assert r2["result_asset_id"], "result_asset_id must be linked"

        # the stored clip serves as video with correct MIME
        served = requests.get(f"{BASE_URL}/files/{r2['result_asset_id']}")
        assert served.status_code == 200
        assert served.headers.get("Content-Type", "").startswith("video/")
        assert len(served.content) > 0

        # completed is terminal: cannot re-execute or PUT back to processing
        re_ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        assert re_ex.status_code == 409
        put_back = requests.put(f"{BASE_URL}/video-jobs/{job['id']}", json={"status": "processing"})
        assert put_back.status_code == 409
    finally:
        _cleanup([prov["id"]])


# --------------------------- failure + retry --------------------------- #
def test_processing_failure_then_retry():
    prov = _mk_provider()
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"], model="fail-processing")
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue")
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute").json()
        assert ex["status"] == "processing"
        f = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/refresh").json()
        assert f["status"] == "failed"
        assert f["error_code"] == "PROVIDER_PROCESSING_FAILED"
        assert f["error_message"]

        # retry preserves creative inputs, resets transient state
        rt = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/retry").json()
        assert rt["status"] == "queued"
        assert rt["provider_job_id"] == "" and rt["progress"] == 0 and rt["error_code"] == ""
        assert rt["prompt"] == "a neon city at dusk"  # inputs preserved
    finally:
        _cleanup([prov["id"]])


def test_submit_rejected_marks_failed():
    prov = _mk_provider()
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"], model="fail-submit")
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue")
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute").json()
        assert ex["status"] == "failed"
        assert ex["error_code"] == "PROVIDER_SUBMIT_REJECTED"
    finally:
        _cleanup([prov["id"]])


# --------------------------- cancellation ------------------------------ #
def test_cancel_processing_job_stays_cancelled():
    prov = _mk_provider()
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue")
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        c = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/cancel").json()
        assert c["status"] == "cancelled"
        # a cancelled job cannot be refreshed into completion
        rf = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/refresh")
        assert rf.status_code == 409
    finally:
        _cleanup([prov["id"]])


# --------------------------- provider errors --------------------------- #
def test_provider_not_configured():
    project = _mk_project()
    # job points at a non-existent provider id
    r = requests.post(f"{BASE_URL}/video-jobs", json={
        "project_id": project, "provider_id": "does-not-exist", "prompt": "x"})
    job = r.json()
    ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
    assert ex.status_code == 422
    assert ex.json()["detail"]["code"] == "PROVIDER_NOT_CONFIGURED"


def test_provider_disabled():
    prov = _mk_provider(enabled=False)
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        assert ex.status_code == 422
        assert ex.json()["detail"]["code"] == "PROVIDER_DISABLED"
    finally:
        _cleanup([prov["id"]])


def test_provider_adapter_not_available():
    # kind 'veo' has no registered adapter (not implemented this sprint)
    prov = _mk_provider(kind="veo")
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue")
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        assert ex.status_code == 422
        assert ex.json()["detail"]["code"] == "PROVIDER_ADAPTER_NOT_AVAILABLE"
    finally:
        _cleanup([prov["id"]])


def test_provider_configuration_invalid():
    prov = _mk_provider(api_key="")  # test adapter requires a key
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        ex = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        assert ex.status_code == 422
        assert ex.json()["detail"]["code"] == "PROVIDER_CONFIGURATION_INVALID"
    finally:
        _cleanup([prov["id"]])


# --------------------------- isolation + secrets ----------------------- #
def test_project_isolation_and_no_secret_leak():
    prov = _mk_provider(api_key="super-secret-key-xyz")
    try:
        p1, p2 = _mk_project(), _mk_project()
        j1 = _mk_job(p1, prov["id"])
        _mk_job(p2, prov["id"])
        listed = requests.get(f"{BASE_URL}/video-jobs", params={"project_id": p1}).json()
        assert all(j["project_id"] == p1 for j in listed)
        assert any(j["id"] == j1["id"] for j in listed)
        # provider list never exposes the raw key
        provs = requests.get(f"{BASE_URL}/providers").json()
        blob = str(provs)
        assert "super-secret-key-xyz" not in blob
    finally:
        _cleanup([prov["id"]])


# --------------------------- queue processing -------------------------- #
def test_process_queue_advances_one():
    prov = _mk_provider()
    try:
        project = _mk_project()
        job = _mk_job(project, prov["id"])
        requests.post(f"{BASE_URL}/video-jobs/{job['id']}/queue")
        res = requests.post(f"{BASE_URL}/video-jobs/process-queue", params={"limit": 1}).json()
        # concurrency limit respected + at least one queued job advanced
        assert res["limit"] == 1
        assert 1 <= res["processed"] <= 1
        # our specific job advances when it is the one processed (execute directly proves the rest)
        direct = requests.post(f"{BASE_URL}/video-jobs/{job['id']}/execute")
        if direct.status_code == 200:
            assert direct.json()["status"] in ("processing", "completed")
    finally:
        _cleanup([prov["id"]])
