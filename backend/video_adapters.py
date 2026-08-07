"""AF-VIDEO-001 — Provider-neutral video adapter interface.

This module defines ONLY the abstract interface + a registry. No concrete
providers (Veo/Kling/Runway/Fal/Replicate) are implemented in this sprint.
All configuration must come from the Provider Hub at call time.
"""
from typing import Any, Dict, Optional


class VideoProviderAdapter:
    """Abstract interface every future video provider adapter must implement.

    Adapters are constructed with the provider's Provider Hub configuration
    (decrypted key, base_url, model, etc.). Nothing here calls the network.
    """

    provider_type = "video"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def validate_configuration(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def submit(self, job: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_status(self, provider_job_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def download_result(self, provider_job_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def cancel(self, provider_job_id: str) -> Dict[str, Any]:
        raise NotImplementedError


_REGISTRY: Dict[str, type] = {}


def register_video_adapter(name: str, adapter_cls: type) -> None:
    _REGISTRY[(name or "").strip().lower()] = adapter_cls


def get_video_adapter(name: str, config: Optional[Dict[str, Any]] = None) -> Optional[VideoProviderAdapter]:
    cls = _REGISTRY.get((name or "").strip().lower())
    return cls(config or {}) if cls else None


def has_video_adapter(name: str) -> bool:
    return (name or "").strip().lower() in _REGISTRY


# ===========================================================================
# AF-VIDEO-002 — Deterministic TEST/DEV adapter (NOT a real provider).
#
# Proves the full provider-neutral execution path (submit → status → progress →
# complete → download → storage → asset) without any paid API. It only activates
# for a Provider Hub provider explicitly marked kind="test"; it is NOT in the
# provider catalog, so it never appears to normal users as a real provider.
# Real Veo/Kling/Runway are intentionally NOT implemented here.
# ===========================================================================
# Tiny deterministic MP4 fixture (valid ftyp box header — enough to store/serve).
_MP4_FIXTURE = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    b"\x00\x00\x00\x08free" + b"AKASHA_TEST_CLIP\x00" * 4
)

# Poll-count state so a stateless get_status can advance deterministically
# (single-process desktop / test use only).
_TEST_POLLS: Dict[str, int] = {}


class TestVideoAdapter(VideoProviderAdapter):
    """Deterministic, network-free adapter for validating the execution engine.

    Failure/behavior is driven by the job's `model` field:
      - "fail-config"     → validate_configuration fails
      - "fail-submit"     → submit is rejected
      - "fail-processing" → first status poll reports failure
      - anything else     → submit → processing → (poll) → completed
    """

    provider_type = "video"

    async def validate_configuration(self) -> Dict[str, Any]:
        if not (self.config.get("api_key") or "").strip():
            return {"ok": False, "error_code": "PROVIDER_CONFIGURATION_INVALID",
                    "message": "Test provider requires an API key."}
        return {"ok": True, "message": "Test provider configuration valid."}

    async def submit(self, job: Dict[str, Any]) -> Dict[str, Any]:
        model = (job.get("model") or "").strip().lower()
        jid = job.get("id", "")
        if model == "fail-submit":
            return {"provider_job_id": "", "status": "failed",
                    "error_code": "PROVIDER_SUBMIT_REJECTED",
                    "error_message": "Test provider rejected the submission.",
                    "provider_metadata": {"adapter": "test"}}
        tag = "failproc" if model == "fail-processing" else "ok"
        provider_job_id = f"test-{tag}-{jid}"
        _TEST_POLLS.pop(provider_job_id, None)
        return {"provider_job_id": provider_job_id, "status": "processing", "progress": 5,
                "provider_metadata": {"adapter": "test", "model": model or "test-model"}}

    async def get_status(self, provider_job_id: str) -> Dict[str, Any]:
        if "failproc" in provider_job_id:
            return {"status": "failed", "progress": 0,
                    "error_code": "PROVIDER_PROCESSING_FAILED",
                    "error_message": "Test provider simulated a processing failure.",
                    "provider_metadata": {"adapter": "test"}}
        n = _TEST_POLLS.get(provider_job_id, 0) + 1
        _TEST_POLLS[provider_job_id] = n
        if n >= 2:
            return {"status": "completed", "progress": 100, "error_code": "", "error_message": "",
                    "provider_metadata": {"adapter": "test", "polls": n}}
        return {"status": "processing", "progress": 55, "error_code": "", "error_message": "",
                "provider_metadata": {"adapter": "test", "polls": n}}

    async def download_result(self, provider_job_id: str) -> Dict[str, Any]:
        return {"data": _MP4_FIXTURE, "mime_type": "video/mp4",
                "filename": f"{provider_job_id}.mp4",
                "provider_metadata": {"adapter": "test", "bytes": len(_MP4_FIXTURE)}}

    async def cancel(self, provider_job_id: str) -> Dict[str, Any]:
        _TEST_POLLS.pop(provider_job_id, None)
        return {"ok": True, "status": "cancelled", "provider_metadata": {"adapter": "test"}}


# Registered at import so the engine can resolve it; only reachable via a
# provider whose kind == "test".
register_video_adapter("test", TestVideoAdapter)
