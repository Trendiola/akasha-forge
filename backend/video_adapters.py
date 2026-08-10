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
# Tiny deterministic MP4 fixture. When FFmpeg is available (desktop + this env)
# we lazily build a REAL, concat-safe 1s MP4 so the whole pipeline — including
# the final-master assembly and playback — can be validated with no paid API.
# If FFmpeg is missing we fall back to a minimal ftyp-box header (store/serve only).
_MP4_FALLBACK = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    b"\x00\x00\x00\x08free" + b"AKASHA_TEST_CLIP\x00" * 4
)
_REAL_MP4_CACHE: Dict[str, bytes] = {}


def _real_mp4_bytes() -> bytes:
    """Build once a real, playable, concat-safe MP4 via FFmpeg (cached)."""
    if "clip" in _REAL_MP4_CACHE:
        return _REAL_MP4_CACHE["clip"]
    import os
    import shutil
    import subprocess
    import tempfile

    ffmpeg = os.environ.get("AKASHA_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    data = _MP4_FALLBACK
    if ffmpeg:
        try:
            out = os.path.join(tempfile.mkdtemp(prefix="akasha_test_clip_"), "clip.mp4")
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=0x1a1030:s=320x180:d=1:r=24",
                 "-pix_fmt", "yuv420p", "-c:v", "libx264", "-t", "1", out],
                check=True, capture_output=True, timeout=30)
            with open(out, "rb") as fh:
                data = fh.read()
        except Exception:  # noqa: BLE001 — fall back to the header fixture
            data = _MP4_FALLBACK
    _REAL_MP4_CACHE["clip"] = data
    return data

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
        data = _real_mp4_bytes()
        return {"data": data, "mime_type": "video/mp4",
                "filename": f"{provider_job_id}.mp4",
                "provider_metadata": {"adapter": "test", "bytes": len(data)}}

    async def cancel(self, provider_job_id: str) -> Dict[str, Any]:
        _TEST_POLLS.pop(provider_job_id, None)
        return {"ok": True, "status": "cancelled", "provider_metadata": {"adapter": "test"}}


# Registered at import so the engine can resolve it; only reachable via a
# provider whose kind == "test".
register_video_adapter("test", TestVideoAdapter)
