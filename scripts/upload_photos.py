#!/usr/bin/env python3
"""Upload processed gallery photo variants to the remote Cloudflare R2 bucket.

This is intentionally separate from process_photos.py: it never changes local
files. By default it reads the three output areas under ~/Downloads and uploads
objects to original/, full/, and thumbnail/ in R2.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INPUT = Path.home() / "Downloads"
DEFAULT_BUCKET = "mars-vrchat-gallery-photos"
DEFAULT_WORKERS = 4
DEFAULT_CACHE_CONTROL = "public, max-age=3600"
VARIANTS = ("original", "full", "thumbnail")


@dataclass(frozen=True)
class UploadTask:
    variant: str
    source: Path
    key: str
    content_type: str
    content_disposition: str | None = None


def list_files(folder: Path, suffixes: set[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in suffixes
    )


def build_upload_tasks(
    input_dir: Path,
    variants: set[str] | None = None,
    full_dir: Path | None = None,
    thumbnail_dir: Path | None = None,
) -> list[UploadTask]:
    selected = variants or set(VARIANTS)
    tasks: list[UploadTask] = []

    if "original" in selected:
        for path in list_files(input_dir, {".png"}):
            if not path.name.startswith("VRChat_"):
                continue
            tasks.append(
                UploadTask(
                    variant="original",
                    source=path,
                    key=f"original/{path.name}",
                    content_type="image/png",
                    content_disposition=f'attachment; filename="{path.name}"',
                )
            )

    if "full" in selected:
        for path in list_files(full_dir or input_dir / "full", {".jpg", ".jpeg"}):
            if not path.name.startswith("VRChat_"):
                continue
            tasks.append(
                UploadTask(
                    variant="full",
                    source=path,
                    key=f"full/{path.stem}.jpg",
                    content_type="image/jpeg",
                )
            )

    if "thumbnail" in selected:
        for path in list_files(thumbnail_dir or input_dir / "thumbnail", {".jpg", ".jpeg"}):
            if not path.name.startswith("VRChat_"):
                continue
            tasks.append(
                UploadTask(
                    variant="thumbnail",
                    source=path,
                    key=f"thumbnail/{path.stem}.jpg",
                    content_type="image/jpeg",
                )
            )

    return tasks


def wrangler_command(task: UploadTask, bucket: str, cache_control: str) -> list[str]:
    project_root = Path(__file__).resolve().parents[1]
    local_wrangler = project_root / "node_modules/.bin/wrangler"
    executable = str(local_wrangler) if local_wrangler.exists() else "npx"
    command = (
        [executable, "r2", "object", "put"]
        if executable != "npx"
        else [executable, "wrangler", "r2", "object", "put"]
    )
    command.extend(
        [
            f"{bucket}/{task.key}",
            "--remote",
            "--file",
            str(task.source),
            "--content-type",
            task.content_type,
            "--cache-control",
            cache_control,
            "--force",
        ]
    )
    if task.content_disposition:
        command.extend(["--content-disposition", task.content_disposition])
    return command


def upload_one(task: UploadTask, bucket: str, cache_control: str) -> tuple[UploadTask, str | None]:
    command = wrangler_command(task, bucket, cache_control)
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    if completed.returncode == 0:
        return task, None

    detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
    return task, detail


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload ~/Downloads photo variants to the remote Cloudflare R2 bucket."
    )
    parser.add_argument("--input", "--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--full-dir", type=Path, default=None)
    parser.add_argument("--thumbnail-dir", type=Path, default=None)
    parser.add_argument(
        "--only",
        action="append",
        choices=VARIANTS,
        help="Upload only this variant; repeat for multiple variants. Defaults to all three.",
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--cache-control", default=DEFAULT_CACHE_CONTROL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_dir = args.input.expanduser().resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Input folder does not exist: {input_dir}")
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    selected = set(args.only or VARIANTS)
    tasks = build_upload_tasks(
        input_dir,
        selected,
        args.full_dir.expanduser().resolve() if args.full_dir else None,
        args.thumbnail_dir.expanduser().resolve() if args.thumbnail_dir else None,
    )
    counts = {variant: sum(task.variant == variant for task in tasks) for variant in VARIANTS}
    print(f"Bucket: {args.bucket}")
    print(f"Input: {input_dir}")
    print("Planned uploads: " + ", ".join(f"{variant}={counts[variant]}" for variant in VARIANTS if variant in selected))

    missing = selected - {task.variant for task in tasks}
    for variant in sorted(missing):
        print(f"Warning: no {variant} files found", file=sys.stderr)
    if not tasks:
        raise SystemExit("No uploadable photo files found.")

    if args.dry_run:
        for task in tasks:
            print(f"DRY RUN: {task.source} -> {args.bucket}/{task.key}")
        return 0

    failures: list[tuple[UploadTask, str]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(upload_one, task, args.bucket, args.cache_control): task for task in tasks
        }
        for future in as_completed(futures):
            task, error = future.result()
            if error:
                failures.append((task, error))
                print(f"✗ {task.key}: {error}", file=sys.stderr)
            else:
                completed += 1
                print(f"✓ [{completed}/{len(tasks)}] {task.key}")

    if failures:
        print(f"\nUploaded {completed}/{len(tasks)} files; {len(failures)} failed.", file=sys.stderr)
        return 1

    print(f"\nUploaded {completed} files to {args.bucket}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
