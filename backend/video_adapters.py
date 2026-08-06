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
