#!/usr/bin/env python3
import argparse
from pathlib import Path

from PIL import Image


def resize_screenshots(input_dir: Path, output_dir: Path):
    """
    Batch resize VRChat screenshots to 720p:
    - Landscape: height = 720, width scales proportionally
    - Vertical: width = 720, height scales proportionally
    """
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    # Create thumbnail directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    resized_count = 0

    for file_path in sorted(input_dir.glob("VRChat_*.png")):
        try:
            with Image.open(file_path) as img:
                width, height = img.size

                # Determine orientation and calculate new size
                if width > height:
                    # Landscape: height = 720, width scales proportionally
                    new_height = 720
                    new_width = int(width * (720 / height))
                    new_size = (new_width, new_height)
                    orientation = "landscape"
                else:
                    # Vertical: width = 720, height scales proportionally
                    new_width = 720
                    new_height = int(height * (720 / width))
                    new_size = (new_width, new_height)
                    orientation = "vertical"

                # Resize image
                resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save to thumbnail folder
                output_file = output_dir / file_path.name
                resized_img.save(output_file, "PNG", quality=95)

                print(f"✓ Resized ({orientation} {width}x{height} -> {new_size[0]}x{new_size[1]}): {file_path.name}")
                resized_count += 1

        except Exception as e:
            print(f"✗ Error processing {file_path.name}: {e}")

    print(f"\nTotal resized: {resized_count}")
    print(f"Output folder: {output_dir.absolute()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resize VRChat screenshots into thumbnail images.")
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
        help="Directory where resized thumbnails will be written. Defaults to INPUT/thumbnails.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or args.input_dir / "thumbnails"
    resize_screenshots(args.input_dir, output_dir)


if __name__ == "__main__":
    main()
