from pathlib import Path

try:
    from PIL import Image
except Exception as exc:
    raise SystemExit("Please install Pillow: pip install pillow") from exc


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "assets" / "images"

RULES = [
    (FRONTEND / "ui", 512),
    (FRONTEND / "projectiles", 512),
]


def optimize_folder(folder: Path, max_size: int) -> None:
    if not folder.exists():
        return
    for img_path in folder.rglob("*"):
        if img_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        with Image.open(img_path) as img:
            w, h = img.size
            if max(w, h) <= max_size:
                continue
            scale = max_size / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            resized = img.resize(new_size, Image.LANCZOS)
            resized.save(img_path, optimize=True)
            print(f"optimized: {img_path} -> {new_size}")


def main() -> None:
    for folder, max_size in RULES:
        optimize_folder(folder, max_size)
    print("done")


if __name__ == "__main__":
    main()
