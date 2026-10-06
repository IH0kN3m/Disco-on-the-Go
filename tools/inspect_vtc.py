#!/usr/bin/env python3
"""Validate all VTC2 containers; optionally export a bounded sample of Crunch pages."""

import argparse
import hashlib
import json
from pathlib import Path

from disco_port.binary import FormatError
from disco_port.vtc import PageFile, decode_crunch


ROOT = Path(__file__).resolve().parent.parent


def inspect(bundle, output, samples, planes):
    bundle, output = bundle.resolve(), output.resolve()
    if bundle == output or bundle in output.parents:
        raise FormatError("Output must be outside the reference app")
    if not output.is_relative_to(ROOT / "artifacts"):
        raise FormatError("Store generated texture data under ignored artifacts/")
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "layout": "Five-plane VTC2, raw page blocks",
              "scope": "Container validation and diagnostic BC/Crunch plane samples; virtual texture placement and shader interpretation pending",
              "files": [], "errors": []}
    for path in sorted((bundle / "Contents/Resources/Data/AmplifyTexture").glob("*.vtc2")):
        try:
            container = PageFile.open(path)
            with path.open("rb") as stream:
                source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            entry = {"file": path.name, "sha256": source_hash, "bytes": container.file_size,
                     "blocks": len(container.blocks), "pages": len(container.pages), "payload_offset": container.payload_offset,
                     "table_sha256": container.table_sha256, "samples": []}
            for page_id in sorted(container.pages)[:samples]:
                for plane in planes:
                    sample = {"page_index": page_id, "plane": plane}
                    try:
                        data = container.read_plane(path, page_id, plane)
                        info, pixels = decode_crunch(data)
                        from PIL import Image
                        filename = f"{path.stem}-{page_id:06}-plane{plane}.png"
                        Image.frombytes("RGBA", (info["width"], info["height"]), pixels, "raw", "BGRA").save(output / filename)
                        sample.update(info, asset=filename, sha256=hashlib.sha256(data).hexdigest())
                    except (ValueError, RuntimeError, OSError) as error:
                        sample["error"] = str(error)
                        report["errors"].append({"file": path.name, **sample})
                    entry["samples"].append(sample)
            report["files"].append(entry)
        except (ValueError, OSError) as error:
            report["errors"].append({"file": path.name, "error": str(error)})
    if not report["files"]:
        raise FormatError("No supported VTC2 containers found")
    (output / "vtc.json").write_text(json.dumps(report, indent=2) + "\n")
    pages = sum(f["pages"] for f in report["files"])
    decoded = sum("asset" in s for f in report["files"] for s in f["samples"])
    print(f"{len(report['files'])} containers, {pages} pages, {decoded} decoded plane samples, {len(report['errors'])} errors")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path("reference/Disco.app"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/amplify/inspection"))
    parser.add_argument("--sample-pages", type=int, default=0)
    parser.add_argument("--planes", type=int, nargs="+", default=[0], choices=range(5))
    args = parser.parse_args()
    if not 0 <= args.sample_pages <= 64:
        parser.error("--sample-pages must be 0..64")
    try:
        report = inspect(args.bundle, args.output, args.sample_pages, args.planes)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(1, f"VTC2 inspection failed: {error}\n")
    if report["errors"]:
        parser.exit(1, "Partial results saved; inspect vtc.json for unsupported streams or malformed containers.\n")


if __name__ == "__main__":
    main()
