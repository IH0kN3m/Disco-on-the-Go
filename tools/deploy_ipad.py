#!/usr/bin/env python3
"""Development-sign, install, and launch Disco on the Go on a configured iPad."""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

from disco_port.engine_project import set_app_bundle_identifier
from disco_port.device_assets import data_manifest, manifest_bytes
from disco_port.device_launch import launch_arguments, validate_launch, validate_ipad


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "artifacts/deployment"


def run(output, arguments, log_name):
    print(f"{log_name.removesuffix('.log')}…", flush=True)
    with (output / log_name).open("w") as log:
        result = subprocess.run(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}); inspect {output.relative_to(ROOT)}/{log_name}")


def deploy(config_path, mip_limit=0, lazy_scenes=True):
    engine=True
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
    output = ROOT / "artifacts/deployment-engine"
    output.mkdir(parents=True, exist_ok=True)
    run(output, ["xcrun", "devicectl", "device", "info", "details", "--device", device,
         "--timeout", "45", "--json-output", str(output / "device.json")], "device.log")
    result = json.loads((output / "device.json").read_text())["result"]
    model = validate_ipad(result)
    if model not in ('iPad16,5', 'iPad16,6'):
        print('Untested iPad model: native BC texture support and sufficient process memory are required.', flush=True)
    project = "artifacts/build/native-engine-ios/Unity-iPhone.xcodeproj"
    derived = "artifacts/build/signed-engine"
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
                raise ValueError('Staged assets changed; run tools/configure_ipad.py again')
    if not (ROOT / project).exists():raise ValueError("Build the game first with make port")
    bundle = config.get('bundle_id', 'org.discoport.engineprobe')
    if engine:
        bundle = config.get('bundle_id', bundle)
        project_file = ROOT / project / 'project.pbxproj'
        settings = plistlib.loads(project_file.read_bytes())
        set_app_bundle_identifier(settings, bundle)
        project_file.write_bytes(plistlib.dumps(settings))
    run(output, ["xcodebuild", "-project", project, "-scheme", "Unity-iPhone",
         "-configuration", "Debug", "-destination", "generic/platform=iOS", "-derivedDataPath",
         derived, "DEVELOPMENT_TEAM=" + team, "CODE_SIGN_STYLE=Automatic", "SDK_STAT_CACHE_ENABLE=NO",
         "-allowProvisioningUpdates", "build"], "build.log")
    app = ROOT / derived / "Build/Products/Debug-iphoneos" / "Disco on the Go.app"
    if plistlib.loads((app / 'Info.plist').read_bytes()).get('CFBundleIdentifier') != bundle:
        raise ValueError('Built app identifier differs from the selected deployment container')
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
                '--domain-type', 'appDataContainer', '--domain-identifier', bundle, '--timeout', '45'],
                stdout=log, stderr=subprocess.STDOUT)
        expected = (asset_root / 'ready.sha256').read_text()
        if result.returncode or not remote.exists() or remote.read_text() != expected:
            run(output, ['xcrun', 'devicectl', 'device', 'copy', 'to', '--device', device,
                '--source', str(asset_root / 'Data'), '--destination', 'Documents/DiscoPortAssets/Data',
                '--domain-type', 'appDataContainer', '--domain-identifier', bundle, '--timeout', '900'], 'asset-upload.log')
            for filename in ('device-assets.json', 'ready.sha256'):
                run(output, ['xcrun', 'devicectl', 'device', 'copy', 'to', '--device', device,
                    '--source', str(asset_root / filename), '--destination', 'Documents/DiscoPortAssets/' + filename,
                    '--domain-type', 'appDataContainer', '--domain-identifier', bundle, '--timeout', '45'], filename + '.log')
        else:
            print('Persistent asset manifest matches; upload skipped.', flush=True)
    run(output, launch_arguments(device, bundle, output / 'launch.json', mip_limit, lazy_scenes), 'launch.log')
    result = json.loads((output / "launch.json").read_text())["result"]
    validate_launch(result, mip_limit, lazy_scenes)
    print("Disco on the Go installed and launched. Confirm gameplay on the iPad.")


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
