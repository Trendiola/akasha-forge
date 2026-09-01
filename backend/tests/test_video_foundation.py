"""AF-VIDEO-001 — One-Prompt Video Creator foundation backend tests."""
import os
import math
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
BRAIN = f"{BASE}/brain"

REQUIRED_SHOT_FIELDS = {
    "id", "scene_id", "order", "title", "duration_seconds", "visual_prompt", "negative_prompt",
    "camera", "lighting", "action", "characters", "location", "continuity_notes",
    "narration_text", "sound_notes", "status",
}


def _new_project():
    r = requests.post(f"{BASE}/projects", json={"name": f"TEST_VID_{uuid.uuid4().hex[:8]}", "type": "video"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _del_project(pid):
    requests.delete(f"{BASE}/projects/{pid}")


def _plan(pid, target=120, clip=8):
    return requests.post(f"{BASE}/video-projects/plan", json={
        "project_id": pid, "prompt": "A lone lighthouse keeper befriends a stranded sea creature during a storm.",
        "target_duration_seconds": target, "aspect_ratio": "16:9", "language": "en", "clip_duration_seconds": clip,
    })


def test_plan_generation_and_clip_count_and_fields():
    pid = _new_project()
    try:
        r = _plan(pid, target=120, clip=8)
        assert r.status_code == 200, r.text
        plan = r.json()
        if plan.get("status") == "needs_configuration":
            pytest.skip("Video planning requires an explicitly configured LLM provider")
        assert plan["status"] == "planned", plan
        expected = math.ceil(120 / 8)  # 15
        assert plan["estimated_total_clips"] == expected
        assert len(plan["shots"]) == expected  # duration determines clip count
        assert len(plan["acts"]) >= 1 and len(plan["scenes"]) >= 1
        # all required shot fields exist
        for shot in plan["shots"]:
            assert REQUIRED_SHOT_FIELDS.issubset(set(shot.keys())), set(shot.keys())
            assert shot["duration_seconds"] == 8

        # scenes + shots persisted in the existing production hierarchy
        prod = requests.get(f"{BASE}/projects/{pid}/production").json()
        assert prod, "production tree should not be empty"

        # planned nodes searchable in Brain (AF-005C)
        s = requests.get(f"{BRAIN}/search", params={"project_id": pid, "q": "lighthouse"}).json()
        assert s["count"] >= 1
    finally:
        _del_project(pid)


def test_clip_count_scales_without_arch_change():
    pid = _new_project()
    try:
        for target, clip in [(30, 8), (60, 8), (300, 10)]:
            r = _plan(pid, target=target, clip=clip)
            assert r.status_code == 200
            plan = r.json()
            if plan.get("status") == "needs_configuration":
                pytest.skip("Video planning requires an explicitly configured LLM provider")
            assert plan["estimated_total_clips"] == math.ceil(target / clip)
            assert len(plan["shots"]) == math.ceil(target / clip)
    finally:
        _del_project(pid)


def test_from_plan_one_job_per_shot_no_duplicates():
    pid = _new_project()
    try:
        plan = _plan(pid, target=32, clip=8).json()
        if plan.get("status") == "needs_configuration":
            pytest.skip("Video planning requires an explicitly configured LLM provider")
        n = plan["estimated_total_clips"]  # 4
        first = requests.post(f"{BASE}/video-jobs/from-plan", json={"project_id": pid})
        assert first.status_code == 200, first.text
        assert first.json()["created"] == n and first.json()["updated"] == 0
        jobs = requests.get(f"{BASE}/video-jobs", params={"project_id": pid}).json()
        assert len(jobs) == n

        # rerun -> no duplicates
        second = requests.post(f"{BASE}/video-jobs/from-plan", json={"project_id": pid})
        assert second.json()["created"] == 0 and second.json()["updated"] == n
        assert len(requests.get(f"{BASE}/video-jobs", params={"project_id": pid}).json()) == n
    finally:
        _del_project(pid)


def test_provider_resolution_and_missing_provider_draft():
    pid = _new_project()
    try:
        # No enabled video provider by default -> Draft job + warning
        r = requests.post(f"{BASE}/video-jobs", json={"project_id": pid, "shot_id": "s1", "prompt": "x"})
        assert r.status_code == 200
        job = r.json()
        assert job["status"] == "draft" and job["warning"]

        # Create + enable a video provider, then resolution should attach it
        p = requests.post(f"{BASE}/providers", json={"name": "TEST_VidProv", "category": "video", "default_model": "Veo 3.1", "enabled": True, "is_default": True})
        assert p.status_code == 200
        vp = p.json()
        try:
            r2 = requests.post(f"{BASE}/video-jobs", json={"project_id": pid, "shot_id": "s2", "prompt": "y"})
            assert r2.status_code == 200
            job2 = r2.json()
            assert job2["provider_id"] == vp["id"] and job2["warning"] == ""
        finally:
            requests.delete(f"{BASE}/providers/{vp['id']}")
    finally:
        _del_project(pid)


def test_queue_cancel_update_delete_protection():
    pid = _new_project()
    try:
        job = requests.post(f"{BASE}/video-jobs", json={"project_id": pid, "shot_id": "s1", "prompt": "x"}).json()
        jid = job["id"]

        # update works
        u = requests.put(f"{BASE}/video-jobs/{jid}", json={"prompt": "updated prompt", "progress": 10})
        assert u.status_code == 200 and u.json()["prompt"] == "updated prompt"

        # queue requires a provider; with a provider present it should queue
        p = requests.post(f"{BASE}/providers", json={"name": "TEST_VidProv2", "category": "video", "enabled": True, "is_default": True})
        vp = p.json()
        try:
            q = requests.post(f"{BASE}/video-jobs/{jid}/queue").json()
            assert q["queued"] is True and q["status"] == "queued"
        finally:
            requests.delete(f"{BASE}/providers/{vp['id']}")

        # delete protection: force to processing -> delete refused
        requests.put(f"{BASE}/video-jobs/{jid}", json={"status": "processing"})
        d = requests.delete(f"{BASE}/video-jobs/{jid}")
        assert d.status_code == 409

        # cancel then delete succeeds
        c = requests.post(f"{BASE}/video-jobs/{jid}/cancel").json()
        assert c["status"] == "cancelled"
        d2 = requests.delete(f"{BASE}/video-jobs/{jid}")
        assert d2.status_code == 200 and d2.json()["ok"] is True
        assert requests.get(f"{BASE}/video-jobs/{jid}").status_code == 404
    finally:
        _del_project(pid)
