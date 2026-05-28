from __future__ import annotations

import argparse
import json
from pathlib import Path

from drive_governance.governance import evaluate_inventory


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Drive Governance inventory fixture.")
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.inventory.read_text(encoding="utf-8"))
    result = evaluate_inventory(payload)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
