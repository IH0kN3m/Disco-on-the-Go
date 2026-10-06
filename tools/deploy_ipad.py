#!/usr/bin/env python3
"""Development-sign, install, and launch a diagnostic on a configured M4 iPad."""

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "artifacts/deployment"


def run(output, arguments, log_name):
    print(f"{log_name.removesuffix('.log')}…", flush=True)
    with (output / log_name).open("w") as log:
        result = subprocess.run(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}); inspect {output.relative_to(ROOT)}/{log_name}")


def deploy(config_path, unity=False, runtime=False, engine=False):
    config_path = config_path.resolve()
    if not config_path.is_relative_to(ROOT / "artifacts"):
        raise ValueError("Keep device/signing configuration under ignored artifacts/")
    config = json.loads(config_path.read_text())
    team, device = config["team_id"], config["device_identifier"]
    if not isinstance(team, str) or not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("Expected a 10-character Apple development team ID")
    if not isinstance(device, str) or not device or device.startswith("-"):
        raise ValueError("Expected a paired device identifier")
    output = ROOT / "artifacts/deployment-engine" if engine else ROOT / "artifacts/runtime-probe/deployment" if runtime else ROOT / "artifacts/deployment-unity" if unity else OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    run(output, ["xcrun", "devicectl", "device", "info", "details", "--device", device,
         "--timeout", "45", "--json-output", str(output / "device.json")], "device.log")
    result = json.loads((output / "device.json").read_text())["result"]
    # New CoreDevice JSON uses properties; support the previous details envelope.
    info = result.get("device", result)
    properties = info.get("properties", {})
    hardware = properties.get("hardware", info.get("hardwareProperties", {}))
    if hardware.get("productType") not in ("iPad16,5", "iPad16,6") or hardware.get("reality") != "physical":
        raise ValueError("Deployment target must be a physical 13-inch iPad Pro M4")
    project = "artifacts/build/native-engine-ios/Unity-iPhone.xcodeproj" if engine else "artifacts/build/unity-ios/Unity-iPhone.xcodeproj" if unity else "apps/ipad/DiscoPort.xcodeproj"
    derived = "artifacts/build/signed-engine" if engine else "artifacts/build/native-runtime" if runtime else "artifacts/build/signed-unity" if unity else "artifacts/build/signed-ipad"
    if not (ROOT / project).exists():
        raise ValueError("Missing engine project; run tools/prepare_engine_probe.py first" if engine else
                         "Missing Xcode project; export the Unity diagnostic first" if unity else "Missing harness project")
    extra = []
    if runtime:
        prepared = ROOT / "artifacts/runtime-probe"
        if not (prepared / "preparation.json").exists():
            raise ValueError("Run tools/prepare_runtime_probe.py first")
        extra = ["PRODUCT_BUNDLE_IDENTIFIER=org.discoport.runtimeprobe", "INFOPLIST_FILE=RuntimeProbe-Info.plist",
                 "SWIFT_ACTIVE_COMPILATION_CONDITIONS=DEBUG DISCO_NATIVE_RUNTIME_PROBE", "DISCO_RUNTIME_PROBE=YES",
                 "DISCO_RUNTIME_PROBE_ROOT=" + str(prepared), "ENABLE_USER_SCRIPT_SANDBOXING=NO"]
    run(output, ["xcodebuild", "-project", project, "-scheme", "Unity-iPhone" if unity or engine else "DiscoPort",
         "-configuration", "Debug", "-destination", "generic/platform=iOS", "-derivedDataPath",
         derived, "DEVELOPMENT_TEAM=" + team, "CODE_SIGN_STYLE=Automatic", "SDK_STAT_CACHE_ENABLE=NO",
         "-allowProvisioningUpdates", *extra, "build"], "build.log")
    app = ROOT / derived / "Build/Products/Debug-iphoneos" / ("DiscoGeometryLab.app" if unity or engine else "DiscoPort.app")
    run(output, ["xcrun", "devicectl", "device", "install", "app", "--device", device, str(app),
         "--timeout", "900" if engine else "60", "--json-output", str(output / "install.json")], "install.log")
    run(output, ["xcrun", "devicectl", "device", "process", "launch", "--device", device,
         "org.discoport.engineprobe" if engine else "org.discoport.runtimeprobe" if runtime else "org.discoport.unityprobe" if unity else "org.discoport.lab",
         "--terminate-existing", "--timeout", "45", "--json-output", str(output / "launch.json")], "launch.log")
    result = json.loads((output / "launch.json").read_text())["result"]
    if not result.get("process", {}).get("processIdentifier"):
        raise ValueError("Launch returned no process identifier")
    print("Original-runtime engine experiment installed and launched on the M4 iPad. Retrieve its log to establish results." if engine else
          "Native CPU probe installed and launched on the M4 iPad. Retrieve its runtime log to establish results." if runtime else
          "Unity geometry diagnostic installed and launched on the M4 iPad. Rendering still needs runtime verification."
          if unity else "Harness installed and launched on the M4 iPad. Gesture testing still requires physical interaction.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "artifacts/local-ipad.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--unity", action="store_true", help="Deploy the exported Unity geometry diagnostic")
    mode.add_argument("--runtime", action="store_true", help="Deploy the derived native CPU probe")
    mode.add_argument("--engine", action="store_true", help="Deploy the original-runtime Unity engine experiment")
    args = parser.parse_args()
    try:
        deploy(args.config, args.unity, args.runtime, args.engine)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Deployment failed: {error}\n")


if __name__ == "__main__":
    main()
