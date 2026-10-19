#!/usr/bin/env python3
"""Generate src/data/photos.json templates from VRChat photo filenames."""

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
DEFAULT_INPUT = Path.home() / "Downloads"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "src/data/photos.json"


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
    return PhotoEntry(filename=f"{Path(filename).stem}.jpg", captured=captured)


def read_existing_photos(output: Path) -> list[JsonObject]:
    if not output.exists():
        return []

    with output.open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise SystemExit(f"Expected a JSON array in {output}")

    return data


def list_photo_entries(photos_dir: Path) -> list[PhotoEntry]:
    entries: dict[str, PhotoEntry] = {}

    for path in photos_dir.iterdir():
        if not path.is_file():
            continue

        entry = parse_photo(path.name)
        if entry:
            entries[Path(entry.filename).stem] = entry

    return sorted(entries.values(), key=lambda entry: (entry.captured, entry.filename))


def build_photos(photos_dir: Path, existing_photos: list[JsonObject]) -> list[JsonObject]:
    existing_stems = {
        Path(str(photo["filename"])).stem
        for photo in existing_photos
        if isinstance(photo.get("filename"), str)
    }
    next_id = max(
        (photo.get("id") for photo in existing_photos if isinstance(photo.get("id"), int)),
        default=0,
    ) + 1
    new_entries = [
        entry for entry in list_photo_entries(photos_dir) if Path(entry.filename).stem not in existing_stems
    ]

    new_photos: list[JsonObject] = [
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

    return [*existing_photos, *new_photos]


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
        description="Create photo metadata templates from VRChat screenshots in ~/Downloads."
    )
    parser.add_argument(
        "--input",
        "--input-dir",
        "--photos-dir",
        dest="input_dir",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Directory containing VRChat screenshots. Defaults to {DEFAULT_INPUT}.",
    )
    parser.add_argument(
        "--output",
        "--output-dir",
        dest="output",
        type=Path,
        default=None,
        help="Directory where photos.json will be written. A .json path is also accepted.",
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
    if args.output and not args.output_file:
        output = args.output if args.output.suffix.lower() == ".json" else args.output / "photos.json"
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    existing_photos = read_existing_photos(output)
    photos = build_photos(input_dir, existing_photos)
    payload = dump_json(photos) + "\n"
    added_count = len(photos) - len(existing_photos)

    if args.dry_run:
        print(payload, end="")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(photos)} photos to {output} ({added_count} added)")


if __name__ == "__main__":
    main()
