#!/usr/bin/env python3
"""Fetch and unpack the pinned official Unity editor/iOS module under artifacts/."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
VERSION = "2020.3.12f1"
REVISION = "b3b2c6512326"
PACKAGES = (
    ("MacEditorInstaller", f"Unity-{VERSION}.pkg", 3614631949,
     "4004943e2ba4607b5e6c3ddd0203ab11686456df0eca55571d558ec32698ea06", "unity-editor-package", "Unity.pkg"),
    ("MacEditorTargetInstaller", f"UnitySetup-iOS-Support-for-Editor-{VERSION}.pkg", 555542528,
     "33c739fcc638836333cfd83210b50103e206f6ff806a53f497bb33c1fecbfe55", "unity-ios-package", "TargetSupport.pkg"),
)


def verify(path, size, digest):
    if path.stat().st_size != size:
        raise ValueError(f"Unexpected package size: {path.name}")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest:
        raise ValueError(f"Package hash mismatch: {path.name}")


def setup():
    base = ROOT / "artifacts/toolchains"
    downloads = base / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    payloads = []
    for directory, name, size, digest, expanded_name, component in PACKAGES:
        archive = downloads / name
        # Reuse the earlier local filename for the identical iOS package.
        legacy = downloads / f"UnitySetup-iOS-{VERSION}.pkg"
        if not archive.exists() and directory == "MacEditorTargetInstaller" and legacy.exists():
            archive = legacy
        if not archive.exists():
            url = f"https://download.unity3d.com/download_unity/{REVISION}/{directory}/{name}"
            partial = archive.with_suffix(".pkg.partial")
            print(f"Downloading official {name}…", flush=True)
            with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
                shutil.copyfileobj(response, output, 1024 * 1024)
            verify(partial, size, digest)
            partial.rename(archive)
        print(f"Verifying {name}…", flush=True)
        verify(archive, size, digest)
        expanded = base / expanded_name
        if not expanded.exists():
            print(f"Unpacking {name}…", flush=True)
            subprocess.run(["pkgutil", "--expand-full", str(archive), str(expanded)], check=True)
        candidates = [expanded / suffix / "Payload" for suffix in (component, component + ".tmp")]
        payload = next((p for p in candidates if p.is_dir()), None)
        if payload is None:
            raise ValueError(f"Unsupported package layout: {name}")
        payloads.append(payload)
    installation = payloads[0] / "Unity"
    editor = installation / "Unity.app/Contents/MacOS/Unity"
    support = payloads[1] / "iOSSupport"
    if not editor.is_file() or not support.is_dir():
        raise ValueError("Pinned package editor or iOS module is missing")
    destination = installation / "PlaybackEngines/iOSSupport"
    if not destination.exists():
        shutil.copytree(support, destination, symlinks=True)
    (base / "unity-editor-path.txt").write_text(str(editor) + "\n")
    print("Local Unity editor/iOS module ready. A valid Unity license and Rosetta are required to run this Intel editor.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        setup()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Unity setup failed: {error}\n")


if __name__ == "__main__":
    main()
