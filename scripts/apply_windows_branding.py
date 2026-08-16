"""Validate the checked-in Akasha Forge Windows/Tauri branding assets.

The previous build-time regeneration path depended on a corrupted base64 image
payload. Windows builds now use the binary icon assets already checked into
frontend/src-tauri/icons and fail fast if any required branding file is missing
or unreadable.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "frontend" / "src-tauri"
ICONS = TAURI_DIR / "icons"
APP_ICON = TAURI_DIR / "app-icon.png"


def _validate_raster(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Missing Akasha Forge branding asset: {path}")
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise RuntimeError(f"Invalid Akasha Forge branding asset {path}: {exc}") from exc


def main() -> None:
    required_pngs = [
        ICONS / "32x32.png",
        ICONS / "128x128.png",
        ICONS / "128x128@2x.png",
        APP_ICON,
    ]
    for path in required_pngs:
        _validate_raster(path)

    ico = ICONS / "icon.ico"
    _validate_raster(ico)

    print("Akasha Forge Windows branding assets validated successfully.")


if __name__ == "__main__":
    main()
