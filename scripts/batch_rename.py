#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def list_screenshots(input_dir: Path):
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.name.startswith("VRChat_")
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def rename_screenshots(input_dir: Path):
    """
    Batch rename VRChat screenshots in place by removing milliseconds and resolution.
    Example: VRChat_2026-06-04_22-35-28.329_3840x2160.jpg -> VRChat_2026-06-04_22-35-28.jpg
    """
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    # Pattern: VRChat_YYYY-MM-DD_HH-MM-SS.milliseconds_WIDTHxHEIGHT.(png|jpg|jpeg)
    pattern = re.compile(
        r"(VRChat_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.\d+_\d+x\d+(\.(?:png|jpe?g))$",
        re.IGNORECASE,
    )

    renamed_count = 0

    for file_path in list_screenshots(input_dir):
        filename = file_path.name

        match = pattern.match(filename)
        if match:
            new_name = match.group(1) + match.group(2)
            new_path = input_dir / new_name

            if new_path.exists():
                print(f"⚠️  Skipped (already exists): {filename} -> {new_name}")
            else:
                file_path.rename(new_path)
                print(f"✓ Renamed: {filename} -> {new_name}")
                renamed_count += 1
        else:
            print(f"⊘ Skipped (doesn't match pattern): {filename}")

    print(f"\nTotal renamed: {renamed_count}")
    print(f"Updated folder: {input_dir.absolute()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename VRChat screenshots in place by removing milliseconds and resolution."
    )
    parser.add_argument(
        "--input",
        "--input-dir",
        "--source-dir",
        dest="input_dir",
        type=Path,
        default=Path("."),
        help="Directory containing source VRChat_*.png/.jpg files.",
    )
    args = parser.parse_args()

    rename_screenshots(args.input_dir)


if __name__ == "__main__":
    main()
