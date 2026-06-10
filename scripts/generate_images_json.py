#!/usr/bin/env python3
"""Generate src/data/images.json templates from VRChat photo filenames."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


PHOTO_PATTERN = re.compile(
    r"^VRChat_(?P<date>\d{4}-\d{2}-\d{2})_(?P<hour>\d{2})-(?P<minute>\d{2})-(?P<second>\d{2})\.png$"
)


@dataclass(frozen=True)
class PhotoEntry:
    filename: str
    captured: str


JsonObject = dict[str, object]
JsonValue = JsonObject | list[object] | str | int | float | bool | None


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
            "description": "",
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
        description="Create image metadata templates from public/photos/VRChat_*.png files."
    )
    parser.add_argument(
        "--photos-dir",
        type=Path,
        default=Path("public/photos"),
        help="Directory containing full-size VRChat screenshots.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/images.json"),
        help="JSON file to write.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated JSON instead of writing it.",
    )
    args = parser.parse_args()

    photos_dir = args.photos_dir
    if not photos_dir.is_dir():
        raise SystemExit(f"Photos directory does not exist: {photos_dir}")

    existing_images = read_existing_images(args.output)
    images = build_images(photos_dir, existing_images)
    payload = dump_json(images) + "\n"
    added_count = len(images) - len(existing_images)

    if args.dry_run:
        print(payload, end="")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(images)} images to {args.output} ({added_count} added)")


if __name__ == "__main__":
    main()
