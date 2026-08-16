"""Generate Windows/Tauri icon assets from the official Akasha Forge emblem source.

Source of truth: .github/branding/official-icon.jpg.b64
Brand: AKASHA FORGE — THE CREATIVE OPERATING SYSTEM — WHERE INFINITE IDEAS BECOME REALITY.
This script changes packaging assets only; it does not touch application logic.
"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_B64 = ROOT / ".github" / "branding" / "official-icon.jpg.b64"
TAURI_DIR = ROOT / "frontend" / "src-tauri"
ICONS = TAURI_DIR / "icons"
APP_ICON = TAURI_DIR / "app-icon.png"


def _decode_brand_asset() -> bytes:
    """Decode the repository branding payload and validate it before Pillow sees it.

    The original repository payload is a raw JPEG byte stream encoded as base64
    without the JPEG SOI marker. Restore that marker deterministically instead of
    allowing Pillow to fail with an opaque UnidentifiedImageError.
    """
    text = "".join(SOURCE_B64.read_text(encoding="utf-8").split())
    raw = base64.b64decode(text, validate=True)

    # Normal JPEG files begin FF D8 FF. The checked-in payload starts immediately
    # after the SOI marker, so restore FF D8 when necessary.
    if not raw.startswith(b"\xff\xd8"):
        raw = b"\xff\xd8" + raw

    if not raw.startswith(b"\xff\xd8\xff"):
        raise RuntimeError("Official Akasha Forge branding payload is not a valid JPEG stream")
    return raw


def main() -> None:
    raw = _decode_brand_asset()
    source = Image.open(BytesIO(raw))
    source.load()  # fail here during CI if the complete source image is corrupt
    source = source.convert("RGBA")

    if source.width != source.height:
        side = max(source.size)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 255))
        canvas.alpha_composite(source, ((side - source.width) // 2, (side - source.height) // 2))
        source = canvas

    source = source.resize((1024, 1024), Image.Resampling.LANCZOS)
    ICONS.mkdir(parents=True, exist_ok=True)

    source.resize((32, 32), Image.Resampling.LANCZOS).save(ICONS / "32x32.png", "PNG")
    source.resize((128, 128), Image.Resampling.LANCZOS).save(ICONS / "128x128.png", "PNG")
    source.resize((256, 256), Image.Resampling.LANCZOS).save(ICONS / "128x128@2x.png", "PNG")
    source.resize((512, 512), Image.Resampling.LANCZOS).save(APP_ICON, "PNG")

    source.save(
        ICONS / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    required = [
        ICONS / "32x32.png",
        ICONS / "128x128.png",
        ICONS / "128x128@2x.png",
        ICONS / "icon.ico",
        APP_ICON,
    ]
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Branding asset generation failed: {path}")

    print(f"Official Akasha Forge Windows branding assets generated successfully from {source.width}x{source.height} source.")


if __name__ == "__main__":
    main()
