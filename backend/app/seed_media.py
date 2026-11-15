"""生成演示用占位照片（离线、无外链依赖）。"""
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import settings

COLORS = [((196, 196, 194), (120, 120, 118)), ((214, 210, 204), (150, 146, 140)), ((178, 182, 184), (96, 100, 104))]


def ensure_seed_photos() -> None:
    out = Path(settings.upload_dir) / "seed"
    out.mkdir(parents=True, exist_ok=True)
    for idx, (bg, fg) in enumerate(COLORS, start=1):
        path = out / f"photo-{idx}.png"
        if path.exists():
            continue
        img = Image.new("RGB", (720, 720), bg)
        draw = ImageDraw.Draw(img)
        draw.rectangle([36, 36, 684, 684], outline=fg, width=6)
        draw.line([36, 540, 684, 540], fill=fg, width=3)
        draw.rectangle([90, 420, 300, 540], outline=fg, width=4)
        draw.ellipse([420, 120, 600, 300], outline=fg, width=4)
        draw.line([120, 120, 300, 380], fill=fg, width=3)
        img.save(path, "PNG", optimize=True)
