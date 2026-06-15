#!/usr/bin/env python3
"""Generate src/data/images.json templates from VRChat photo filenames."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union


PHOTO_PATTERN = re.compile(
    r"^VRChat_(?P<date>\d{4}-\d{2}-\d{2})_(?P<hour>\d{2})-(?P<minute>\d{2})-(?P<second>\d{2})\.(?:png|jpe?g)$",
    re.IGNORECASE,
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "src/data/images.json"


@dataclass(frozen=True)
class PhotoEntry:
    filename: str
    captured: str


JsonObject = dict[str, object]
JsonValue = Union[JsonObject, list[object], str, int, float, bool, None]


def parse_photo(filename: str) -> PhotoEntry | None:
    match = PHOTO_PATTERN.match(filename)
    if not match:
        return None

    captured = (
        f"{match.group('date')}T"
        f"{match.group('hour')}:{match.group('minute')}:{match.group('second')}"
    )
    return PhotoEntry(filename=filename, captured=captured)


def read_existing_images(output: Path) -> list[JsonObject]:
    if not output.exists():
        return []

    with output.open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise SystemExit(f"Expected a JSON array in {output}")

    return data


def list_photo_entries(photos_dir: Path) -> list[PhotoEntry]:
    entries = []

    for path in photos_dir.iterdir():
        if not path.is_file():
            continue

        entry = parse_photo(path.name)
        if entry:
            entries.append(entry)

    entries.sort(key=lambda entry: (entry.captured, entry.filename))
    return entries


def build_images(photos_dir: Path, existing_images: list[JsonObject]) -> list[JsonObject]:
    existing_filenames = {
        image.get("filename")
        for image in existing_images
        if isinstance(image.get("filename"), str)
    }
    next_id = max(
        (image.get("id") for image in existing_images if isinstance(image.get("id"), int)),
        default=0,
    ) + 1
    new_entries = [
        entry for entry in list_photo_entries(photos_dir) if entry.filename not in existing_filenames
    ]

    new_images: list[JsonObject] = [
        {
            "id": index,
            "filename": entry.filename,
            "captured": entry.captured,
            "world": "",
            "description_en": "",
            "description_zh": "",
            "friend": [""],
        }
        for index, entry in enumerate(new_entries, start=next_id)
    ]

    return [*existing_images, *new_images]


def dump_json(value: JsonValue, indent: int = 0) -> str:
    space = " " * indent
    child_space = " " * (indent + 2)

    if isinstance(value, dict):
        if not value:
            return "{}"

        lines = ["{"]
        items = list(value.items())
        for index, (key, item) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            lines.append(
                f"{child_space}{json.dumps(key, ensure_ascii=False)}: "
                f"{dump_json(item, indent + 2)}{comma}"
            )
        lines.append(f"{space}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"

        if all(not isinstance(item, (dict, list)) for item in value):
            return json.dumps(value, ensure_ascii=False)

        lines = ["["]
        for index, item in enumerate(value):
            comma = "," if index < len(value) - 1 else ""
            lines.append(f"{child_space}{dump_json(item, indent + 2)}{comma}")
        lines.append(f"{space}]")
        return "\n".join(lines)

    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create image metadata templates from public/photos/VRChat_*.png/.jpg files."
    )
    parser.add_argument(
        "--input",
        "--input-dir",
        "--photos-dir",
        dest="input_dir",
        type=Path,
        default=Path("public/photos"),
        help="Directory containing full-size VRChat screenshots.",
    )
    parser.add_argument(
        "--output",
        "--output-dir",
        dest="output",
        type=Path,
        default=None,
        help="Directory where images.json will be written. A .json path is also accepted.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Exact JSON file to write. Overrides --output when provided.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated JSON instead of writing it.",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output = args.output_file or DEFAULT_OUTPUT
    if args.output:
        output = args.output if args.output.suffix.lower() == ".json" else args.output / "images.json"
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    existing_images = read_existing_images(output)
    images = build_images(input_dir, existing_images)
    payload = dump_json(images) + "\n"
    added_count = len(images) - len(existing_images)

    if args.dry_run:
        print(payload, end="")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(images)} images to {output} ({added_count} added)")


if __name__ == "__main__":
    main()
