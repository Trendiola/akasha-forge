"""AF-FINAL-CLOSURE dev validation: exercises the exact endpoints Movie Studio
calls, end-to-end, using the internal deterministic TEST adapter. NOT shipped."""
import asyncio
import time

import httpx

from core import db, now_iso, new_id

BASE = "http://localhost:8001/api"
TEST_PROVIDER_ID = "ms-e2e-test-video-provider"


async def _seed_provider():
    # Create via the real API so the api_key is encrypted like a normal provider.
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{BASE}/providers", json={
            "name": "E2E Test Renderer", "category": "video", "kind": "test",
            "api_key": "k-e2e-123", "default_model": "ok", "enabled": True})
        pid = r.json()["id"]
    await db.providers.update_one({"id": pid}, {"$set": {"is_default": True, "priority": 1}})
    return pid


async def _cleanup(project_id, provider_id):
    await db.providers.delete_one({"id": provider_id})
    await db.production_nodes.delete_many({"project_id": project_id})
    await db.video_render_jobs.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id})


async def main():
    provider_id = await _seed_provider()
    pid = new_id()
    await db.projects.insert_one({"id": pid, "name": "MS E2E", "created_at": now_iso(), "updated_at": now_iso()})
    ok = True
    try:
        async with httpx.AsyncClient(timeout=90) as c:
            # 1. Plan
            r = await c.post(f"{BASE}/video-projects/plan", json={
                "project_id": pid, "prompt": "A lone lighthouse keeper during a storm",
                "target_duration_seconds": 24, "clip_duration_seconds": 8, "aspect_ratio": "16:9"})
            plan = r.json()
            print("PLAN:", plan.get("status"), "shots=", plan.get("estimated_total_clips"))
            assert plan.get("status") == "planned", plan
            assert len(plan.get("shots", [])) >= 1

            # 2. from-plan
            r = await c.post(f"{BASE}/video-jobs/from-plan", json={"project_id": pid, "aspect_ratio": "16:9"})
            fp = r.json()
            print("FROM-PLAN:", fp.get("created"), "created /", fp.get("shots"), "shots")
            assert fp.get("shots") == len(plan["shots"])

            # 3. produce loop (drives progress like the UI runner)
            status = None
            for i in range(40):
                r = await c.post(f"{BASE}/video-projects/{pid}/produce", json={"subtitles": True, "auto_export": True})
                status = r.json()
                print(f"  produce#{i}: status={status['status']} progress={status['progress']}% "
                      f"done={status['completed']}/{status['total_jobs']} final={bool(status['final_asset_id'])}")
                if status["status"] in ("completed", "failed", "empty"):
                    break
                time.sleep(0.3)

            assert status["status"] == "completed", status
            assert status["final_asset_id"], "no final asset"

            # 4. final master is served + playable
            r = await c.get(f"{BASE}/files/{status['final_asset_id']}")
            print("FINAL FILE:", r.status_code, r.headers.get("content-type"), len(r.content), "bytes")
            assert r.status_code == 200
            assert "video" in (r.headers.get("content-type") or "")

            # 5. production-status restores same terminal state (no mutation)
            r = await c.get(f"{BASE}/video-projects/{pid}/production-status")
            rs = r.json()
            assert rs["status"] == "completed" and rs["final_asset_id"] == status["final_asset_id"]
            print("RESTORE OK:", rs["status"], rs["progress"], "%")

            print("\n✅ MOVIE STUDIO E2E: ALL PASS")
    except Exception as e:  # noqa: BLE001
        ok = False
        print("\n❌ FAIL:", repr(e))
    finally:
        await _cleanup(pid, provider_id)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
