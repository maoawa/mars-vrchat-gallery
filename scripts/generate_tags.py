#!/usr/bin/env python3
"""Generate src/data/tags.json templates for photos that have friends."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Union


DEFAULT_IMAGES = Path(__file__).resolve().parent.parent / "src/data/images.json"
DEFAULT_TAGS = Path(__file__).resolve().parent.parent / "src/data/tags.json"

JsonObject = dict[str, object]
JsonValue = Union[JsonObject, list[object], str, int, float, bool, None]


def read_json_array(path: Path, label: str) -> list[JsonObject]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise SystemExit(f"Expected a JSON array in {path} for {label}")

    if not all(isinstance(item, dict) for item in data):
        raise SystemExit(f"Expected every item in {path} to be an object")

    return data


def friend_ids(image: JsonObject) -> list[str]:
    friends = image.get("friend")

    if not isinstance(friends, list):
        return []

    seen: set[str] = set()
    ids: list[str] = []

    for friend in friends:
        if not isinstance(friend, str):
            continue

        friend_id = friend.strip()

        if not friend_id or friend_id in seen:
            continue

        seen.add(friend_id)
        ids.append(friend_id)

    return ids


def tag_points(count: int) -> list[tuple[float, float]]:
    if count <= 1:
        return [(50.0, 50.0)]

    left = 38
    right = 62
    step = (right - left) / (count - 1)

    return [(round(left + step * index, 1), 50.0) for index in range(count)]


def build_tag_templates(images: list[JsonObject], existing_tags: list[JsonObject]) -> list[JsonObject]:
    tagged_photo_ids = {
        tag_group.get("photo")
        for tag_group in existing_tags
        if isinstance(tag_group.get("photo"), int)
    }
    new_tag_groups: list[JsonObject] = []

    for image in images:
        photo_id = image.get("id")

        if not isinstance(photo_id, int) or photo_id in tagged_photo_ids:
            continue

        friends = friend_ids(image)

        if not friends:
            continue

        points = tag_points(len(friends))
        new_tag_groups.append(
            {
                "photo": photo_id,
                "tags": [
                    {
                        "friend": friend,
                        "x": x,
                        "y": y,
                    }
                    for friend, (x, y) in zip(friends, points)
                ],
            }
        )

    return sorted([*existing_tags, *new_tag_groups], key=lambda tag_group: int(tag_group.get("photo", 0)))


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
        description="Create tag templates for images that list friends but do not yet have tags."
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=DEFAULT_IMAGES,
        help="Path to images.json.",
    )
    parser.add_argument(
        "--tags",
        "--output",
        dest="tags",
        type=Path,
        default=DEFAULT_TAGS,
        help="Path to tags.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated tags JSON instead of writing it.",
    )
    args = parser.parse_args()

    images = read_json_array(args.images, "images")
    existing_tags = read_json_array(args.tags, "tags")
    tag_groups = build_tag_templates(images, existing_tags)
    payload = dump_json(tag_groups) + "\n"
    added_count = len(tag_groups) - len(existing_tags)

    if args.dry_run:
        print(payload, end="")
        return

    args.tags.parent.mkdir(parents=True, exist_ok=True)
    args.tags.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(tag_groups)} tag groups to {args.tags} ({added_count} added)")


if __name__ == "__main__":
    main()
