#!/usr/bin/env python3
import argparse
from pathlib import Path

from PIL import Image


def list_png_screenshots(input_dir: Path):
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.name.startswith("VRChat_")
        and path.suffix.lower() == ".png"
    )


def flatten_to_rgb(image: Image.Image, background: str) -> Image.Image:
    if image.mode in {"RGB", "L"}:
        return image.convert("RGB")

    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        base = Image.new("RGBA", rgba.size, background)
        base.alpha_composite(rgba)
        return base.convert("RGB")

    return image.convert("RGB")


def convert_png_to_jpg(input_dir: Path, output_dir: Path, quality: int, background: str, overwrite: bool):
    """
    Batch convert VRChat PNG screenshots into JPG files.
    """
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    converted_count = 0
    skipped_count = 0

    for file_path in list_png_screenshots(input_dir):
        output_file = output_dir / f"{file_path.stem}.jpg"

        if output_file.exists() and not overwrite:
            print(f"⚠️  Skipped (already exists): {output_file.name}")
            skipped_count += 1
            continue

        try:
            with Image.open(file_path) as img:
                jpg = flatten_to_rgb(img, background)
                jpg.save(output_file, "JPEG", quality=quality, optimize=True)

            print(f"✓ Converted: {file_path.name} -> {output_file.name}")
            converted_count += 1
        except Exception as e:
            print(f"✗ Error processing {file_path.name}: {e}")

    print(f"\nTotal converted: {converted_count}")
    print(f"Total skipped: {skipped_count}")
    print(f"Output folder: {output_dir.absolute()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert VRChat PNG screenshots into JPG files.")
    parser.add_argument(
        "--input",
        "--input-dir",
        "--source-dir",
        dest="input_dir",
        type=Path,
        default=Path("."),
        help="Directory containing source VRChat_*.png files.",
    )
    parser.add_argument(
        "--output",
        "--output-dir",
        dest="output_dir",
        type=Path,
        default=None,
        help="Directory where JPG files will be written. Defaults to INPUT.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        choices=range(1, 101),
        metavar="1-100",
        help="JPEG quality. Defaults to 95.",
    )
    parser.add_argument(
        "--background",
        default="white",
        help="Background color used when flattening transparent PNGs. Defaults to white.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing JPG files.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or args.input_dir
    convert_png_to_jpg(args.input_dir, output_dir, args.quality, args.background, args.overwrite)


if __name__ == "__main__":
    main()
