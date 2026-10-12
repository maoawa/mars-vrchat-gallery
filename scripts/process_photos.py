#!/usr/bin/env python3
"""One-tap VRChat screenshot processing for the gallery workflow.

Source screenshots stay in the input folder as PNG originals. Processed assets
are written to sibling ``full`` and ``thumbnail`` folders by default.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image

IMAGE_PATTERN = re.compile(
    r"^(VRChat_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.\d+_\d+x\d+\.(png|jpe?g)$",
    re.IGNORECASE,
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
DEFAULT_INPUT = Path.home() / "Downloads"
DEFAULT_FULL_NAME = "full"
DEFAULT_THUMBNAIL_NAME = "thumbnail"
FULL_QUALITY = 90
THUMBNAIL_QUALITY = 60
THUMBNAIL_MAX_SIZE = 640


def top_level_screenshots(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.name.startswith("VRChat_")
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def rename_screenshots(folder: Path, dry_run: bool) -> int:
    renamed = 0
    for path in top_level_screenshots(folder):
        match = IMAGE_PATTERN.match(path.name)
        if not match:
            continue

        destination = path.with_name(f"{match.group(1)}{path.suffix.lower()}")
        if destination == path:
            continue
        if destination.exists():
            raise SystemExit(f"Cannot rename {path.name}: {destination.name} already exists")

        print(f"✓ Rename: {path.name} -> {destination.name}")
        if not dry_run:
            path.rename(destination)
        renamed += 1

    return renamed


def flatten_to_rgb(image: Image.Image, background: str = "white") -> Image.Image:
    if image.mode in {"RGB", "L"}:
        return image.convert("RGB")

    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        base = Image.new("RGBA", rgba.size, background)
        base.alpha_composite(rgba)
        return base.convert("RGB")

    return image.convert("RGB")


def thumbnail_size(width: int, height: int, maximum: int) -> tuple[int, int]:
    longest_edge = max(width, height)
    if longest_edge <= maximum:
        return width, height

    scale = maximum / longest_edge
    return max(1, round(width * scale)), max(1, round(height * scale))


def source_pngs(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".png" and path.name.startswith("VRChat_"))


def process_images(folder: Path, full_dir: Path, thumbnail_dir: Path, dry_run: bool) -> tuple[int, int]:
    if not dry_run:
        full_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
    full_count = 0
    thumbnail_count = 0

    for source in source_pngs(folder):
        full_path = full_dir / f"{source.stem}.jpg"
        thumbnail_path = thumbnail_dir / f"{source.stem}.jpg"

        with Image.open(source) as image:
            rgb = flatten_to_rgb(image)
            width, height = rgb.size
            small_size = thumbnail_size(width, height, THUMBNAIL_MAX_SIZE)
            thumbnail = rgb if small_size == rgb.size else rgb.resize(small_size, Image.Resampling.LANCZOS)

            print(f"✓ Full: {source.name} -> {full_path}")
            print(f"✓ Thumbnail: {source.name} -> {thumbnail_path} ({small_size[0]}x{small_size[1]})")

            if not dry_run:
                rgb.save(full_path, "JPEG", quality=FULL_QUALITY, optimize=True)
                thumbnail.save(thumbnail_path, "JPEG", quality=THUMBNAIL_QUALITY, optimize=True)

        full_count += 1
        thumbnail_count += 1

    return full_count, thumbnail_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename and process VRChat PNG originals into full JPGs and 640px thumbnail JPGs."
    )
    parser.add_argument(
        "--input",
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Folder containing original PNG screenshots. Defaults to {DEFAULT_INPUT}.",
    )
    parser.add_argument(
        "--full-output",
        type=Path,
        default=None,
        help="Output folder for full JPGs. Defaults to INPUT/full.",
    )
    parser.add_argument(
        "--thumbnail-output",
        type=Path,
        default=None,
        help="Output folder for thumbnail JPGs. Defaults to INPUT/thumbnail.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print operations without writing files.")
    args = parser.parse_args()

    input_dir = args.input.expanduser().resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Input folder does not exist: {input_dir}")

    full_dir = (args.full_output or input_dir / DEFAULT_FULL_NAME).expanduser().resolve()
    thumbnail_dir = (args.thumbnail_output or input_dir / DEFAULT_THUMBNAIL_NAME).expanduser().resolve()

    renamed = rename_screenshots(input_dir, args.dry_run)
    full_count, thumbnail_count = process_images(input_dir, full_dir, thumbnail_dir, args.dry_run)

    print()
    print(f"Renamed: {renamed}")
    print(f"Full JPGs: {full_count} (quality {FULL_QUALITY}) -> {full_dir}")
    print(f"Thumbnail JPGs: {thumbnail_count} (quality {THUMBNAIL_QUALITY}, max {THUMBNAIL_MAX_SIZE}px) -> {thumbnail_dir}")
    if full_count == 0:
        print("No top-level VRChat PNG originals found.")


if __name__ == "__main__":
    main()
