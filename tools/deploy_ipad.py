#!/usr/bin/env python3
"""Development-sign, install, and launch a diagnostic on a configured M4 iPad."""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

from disco_port.device_assets import data_manifest, manifest_bytes
from disco_port.device_launch import launch_arguments, validate_launch


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "artifacts/deployment"


def run(output, arguments, log_name):
    print(f"{log_name.removesuffix('.log')}…", flush=True)
    with (output / log_name).open("w") as log:
        result = subprocess.run(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}); inspect {output.relative_to(ROOT)}/{log_name}")


def deploy(config_path, unity=False, runtime=False, engine=False, mip_limit=None, lazy_scenes=False):
    if lazy_scenes and not engine:
        raise ValueError('Lazy scenes require the original-runtime engine experiment')
    if mip_limit is not None and (not engine or mip_limit not in range(4)):
        raise ValueError('Texture mip limit requires the engine experiment and a value from 0 through 3')
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
    persistent = False
    if engine:
        info_path = ROOT / 'artifacts/build/native-engine-ios/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        persistent = info.get('DiscoPersistentAssets') is True
        if persistent:
            derived += '-persistent'
            asset_root = ROOT / 'artifacts/build/native-engine-ios'
            actual = manifest_bytes(data_manifest(asset_root / 'Data'))
            if actual != (asset_root / 'device-assets.json').read_bytes() or hashlib.sha256(actual).hexdigest() != info['DiscoAssetManifestSHA256']:
                raise ValueError('Staged assets changed; run tools/configure_engine_assets.py again')
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
    if persistent and (app / 'Data').exists():
        raise ValueError('Persistent build unexpectedly contains bundled Data')
    run(output, ["xcrun", "devicectl", "device", "install", "app", "--device", device, str(app),
         "--timeout", "900" if engine else "60", "--json-output", str(output / "install.json")], "install.log")
    if persistent:
        remote = output / 'device-ready.sha256'
        remote.unlink(missing_ok=True)
        with (output / 'asset-check.log').open('w') as log:
            result = subprocess.run(['xcrun', 'devicectl', 'device', 'copy', 'from', '--device', device,
                '--source', 'Documents/DiscoPortAssets/ready.sha256', '--destination', str(remote),
                '--domain-type', 'appDataContainer', '--domain-identifier', 'org.discoport.engineprobe', '--timeout', '45'],
                stdout=log, stderr=subprocess.STDOUT)
        expected = (asset_root / 'ready.sha256').read_text()
        if result.returncode or not remote.exists() or remote.read_text() != expected:
            run(output, ['xcrun', 'devicectl', 'device', 'copy', 'to', '--device', device,
                '--source', str(asset_root / 'Data'), '--destination', 'Documents/DiscoPortAssets/Data',
                '--domain-type', 'appDataContainer', '--domain-identifier', 'org.discoport.engineprobe', '--timeout', '900'], 'asset-upload.log')
            for filename in ('device-assets.json', 'ready.sha256'):
                run(output, ['xcrun', 'devicectl', 'device', 'copy', 'to', '--device', device,
                    '--source', str(asset_root / filename), '--destination', 'Documents/DiscoPortAssets/' + filename,
                    '--domain-type', 'appDataContainer', '--domain-identifier', 'org.discoport.engineprobe', '--timeout', '45'], filename + '.log')
        else:
            print('Persistent asset manifest matches; upload skipped.', flush=True)
    bundle = "org.discoport.engineprobe" if engine else "org.discoport.runtimeprobe" if runtime else "org.discoport.unityprobe" if unity else "org.discoport.lab"
    run(output, launch_arguments(device, bundle, output / 'launch.json', mip_limit, lazy_scenes), 'launch.log')
    result = json.loads((output / "launch.json").read_text())["result"]
    validate_launch(result, mip_limit, lazy_scenes)
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
    parser.add_argument('--mip-limit', type=int, choices=range(4), help='Diagnostic engine texture mip limit (0 keeps full resolution)')
    parser.add_argument('--lazy-scenes', action='store_true', help='Enable the experimental on-demand scene adapter')
    args = parser.parse_args()
    try:
        deploy(args.config, args.unity, args.runtime, args.engine, args.mip_limit, args.lazy_scenes)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Deployment failed: {error}\n")


if __name__ == "__main__":
    main()
