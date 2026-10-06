#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from disco_port.binary import FormatError
from disco_port.index import build_index


def main():
    p = argparse.ArgumentParser(description="Build a local method index from Disco.app without executing it")
    p.add_argument("--bundle", type=Path, default=Path("reference/Disco.app"))
    p.add_argument("--output", type=Path, default=Path("artifacts/inspection"))
    args = p.parse_args()
    try:
        print(json.dumps(build_index(args.bundle, args.output), indent=2))
    except (OSError, ValueError, FormatError) as error:
        p.exit(1, f"Inspection failed: {error}\n")


if __name__ == "__main__":
    main()
