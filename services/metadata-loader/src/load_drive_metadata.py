"""CLI for building /files upsert payloads from normalized Drive events."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from metadata_loader.drive_metadata import load_metadata_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build metadata upsert payloads from normalized Drive events."
    )
    parser.add_argument("normalized_batch", type=Path, help="Path to normalized event batch JSON")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = load_metadata_batch(args.normalized_batch)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
