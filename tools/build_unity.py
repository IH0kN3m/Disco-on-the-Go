#!/usr/bin/env python3
"""Export the staged diagnostic with the exact local Unity editor."""

import argparse
import json
import os
import plistlib
from pathlib import Path
import subprocess
from disco_port.unity_stage import modernize_ios_project, modernize_ios_trampoline, modernize_orientation_transition


ROOT = Path(__file__).resolve().parent.parent


def build(editor):
    project = ROOT / "artifacts/recovered-unity"
    if not (project / "staging.json").exists():
        raise ValueError("Run make stage-unity first")
    for source, staged in (("SceneProbe.cs", "SceneProbe.cs"), ("Editor/BuildProbe.cs", "Editor/BuildProbe.cs")):
        if (ROOT / "runtime/UnityHost" / source).read_bytes() != (project / "Assets" / staged).read_bytes():
            raise ValueError("Staged host code is outdated; run make stage-unity first")
    output = ROOT / "artifacts/build/unity-ios"
    log = ROOT / "artifacts/build/unity-editor.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment['DISCO_EMPTY_HOST'] = '1' if json.loads((project / "staging.json").read_text()).get('empty_host') is True else '0'
    environment["UNITY_IOS_OUTPUT"] = str(output)
    config = ROOT / "artifacts/local-ipad.json"
    if config.exists():
        environment["UNITY_DEVELOPMENT_TEAM"] = json.loads(config.read_text())["team_id"]
    print("Exporting the Unity 2020.3.12f1 local host…", flush=True)
    with (log.parent / "unity-process.log").open("w") as process_log:
        result = subprocess.run([str(editor), "-batchmode", "-nographics", "-quit", "-projectPath", str(project),
                                 "-buildTarget", "iOS", "-executeMethod", "BuildProbe.ExportIOS", "-logFile", str(log)],
                                cwd=ROOT, env=environment, stdout=process_log, stderr=subprocess.STDOUT)
    if result.returncode or not (output / "Unity-iPhone.xcodeproj").exists() or "Unity iOS diagnostic export succeeded" not in log.read_text():
        raise ValueError(f"Unity export failed ({result.returncode}); inspect artifacts/build/unity-editor.log")
    pbx = output / "Unity-iPhone.xcodeproj/project.pbxproj"
    pbx.write_text(modernize_ios_project(pbx.read_text()))
    trampoline = output / "Classes/UnityAppController.mm"
    adapter = (ROOT / "runtime/UnityHost/iOS/SceneLifecycle.mm").read_text()
    trampoline.write_text(modernize_ios_trampoline(trampoline.read_text(), adapter))
    handling = output / 'Classes/UI/UnityAppController+ViewHandling.mm'
    handling.write_text(modernize_orientation_transition(handling.read_text()))
    plist = output / "Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info["UIApplicationSceneManifest"] = {
        "UIApplicationSupportsMultipleScenes": False,
        "UISceneConfigurations": {"UIWindowSceneSessionRoleApplication": [{
            "UISceneConfigurationName": "Disco Unity Diagnostic",
            "UISceneDelegateClassName": "DiscoUnitySceneDelegate"
        }]}
    }
    plist.write_bytes(plistlib.dumps(info))
    print("Unity exported the iOS Xcode project under artifacts/build/unity-ios/; device compilation and execution remain separate checks.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--editor", type=Path)
    args = parser.parse_args()
    try:
        editor = args.editor or Path((ROOT / "artifacts/toolchains/unity-editor-path.txt").read_text().strip())
        build(editor.resolve())
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Unity build failed: {error}\n")


if __name__ == "__main__":
    main()
