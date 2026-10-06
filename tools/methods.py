#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from disco_port.index import search


def main():
    p = argparse.ArgumentParser(description="Search recovered method names and unslid native addresses")
    p.add_argument("term")
    p.add_argument("--image")
    p.add_argument("--arch", choices=("arm64", "x86_64"), default="arm64")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--database", type=Path, default=Path("artifacts/inspection/methods.sqlite"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if not 1 <= args.limit <= 10000:
        p.error("limit must be between 1 and 10000")
    try:
        rows = search(args.database, args.term, args.image, args.arch, args.limit)
    except (OSError, ValueError) as error:
        p.exit(1, f"Search failed: {error}\n")
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            address = f"{row['address']:#x}" if row["address"] else row["status"]
            print(f"{row['id']:6}  {address:>18}  {row['image']}  {row['qualified_name']} ({row['parameter_count']} parameters)")
        print(f"{len(rows)} results; limit {args.limit}. Addresses are unslid, and method bodies are not recovered.")


if __name__ == "__main__":
    main()
