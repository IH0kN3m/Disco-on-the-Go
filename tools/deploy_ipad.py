#!/usr/bin/env python3
"""Development-sign, install, and launch the harness on a configured M4 iPad."""

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "artifacts/deployment"


def run(arguments, log_name):
    print(f"{log_name.removesuffix('.log')}…", flush=True)
    with (OUTPUT / log_name).open("w") as log:
        result = subprocess.run(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}); inspect artifacts/deployment/{log_name}")


def deploy(config_path):
    config_path = config_path.resolve()
    if not config_path.is_relative_to(ROOT / "artifacts"):
        raise ValueError("Keep device/signing configuration under ignored artifacts/")
    config = json.loads(config_path.read_text())
    team, device = config["team_id"], config["device_identifier"]
    if not isinstance(team, str) or not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("Expected a 10-character Apple development team ID")
    if not isinstance(device, str) or not device or device.startswith("-"):
        raise ValueError("Expected a paired device identifier")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run(["xcrun", "devicectl", "device", "info", "details", "--device", device,
         "--timeout", "45", "--json-output", str(OUTPUT / "device.json")], "device.log")
    result = json.loads((OUTPUT / "device.json").read_text())["result"]
    # New CoreDevice JSON uses properties; support the previous details envelope.
    info = result.get("device", result)
    properties = info.get("properties", {})
    hardware = properties.get("hardware", info.get("hardwareProperties", {}))
    if hardware.get("productType") not in ("iPad16,5", "iPad16,6") or hardware.get("reality") != "physical":
        raise ValueError("Deployment target must be a physical 13-inch iPad Pro M4")
    run(["xcodebuild", "-project", "apps/ipad/DiscoPort.xcodeproj", "-scheme", "DiscoPort",
         "-configuration", "Debug", "-destination", "generic/platform=iOS", "-derivedDataPath",
         "artifacts/build/signed-ipad", "DEVELOPMENT_TEAM=" + team, "CODE_SIGN_STYLE=Automatic",
         "-allowProvisioningUpdates", "build"], "build.log")
    app = ROOT / "artifacts/build/signed-ipad/Build/Products/Debug-iphoneos/DiscoPort.app"
    run(["xcrun", "devicectl", "device", "install", "app", "--device", device, str(app),
         "--timeout", "60", "--json-output", str(OUTPUT / "install.json")], "install.log")
    run(["xcrun", "devicectl", "device", "process", "launch", "--device", device, "org.discoport.lab",
         "--terminate-existing", "--timeout", "45", "--json-output", str(OUTPUT / "launch.json")], "launch.log")
    result = json.loads((OUTPUT / "launch.json").read_text())["result"]
    if not result.get("process", {}).get("processIdentifier"):
        raise ValueError("Launch returned no process identifier")
    print("Harness installed and launched on the M4 iPad. Gesture testing still requires physical interaction.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "artifacts/local-ipad.json")
    args = parser.parse_args()
    try:
        deploy(args.config)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Deployment failed: {error}\n")


if __name__ == "__main__":
    main()
