from __future__ import annotations

import argparse
import json

from drive_governance.firestore_writer import firestore_client, write_governance_batch
from drive_governance.governance import evaluate_inventory
from drive_governance.inventory import build_inventory_from_firestore


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Drive Governance from Firestore inventory.")
    parser.add_argument("--project", default="capital-index-2026")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    client = firestore_client(args.project, args.database)
    inventory = build_inventory_from_firestore(
        client=client,
        limit=args.limit,
        fixture_id="firestore_inventory",
    )
    result = evaluate_inventory(inventory)
    result["inventory_source"] = "firestore"
    result["write"] = write_governance_batch(result, client=client, write_enabled=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
