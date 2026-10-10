#!/usr/bin/env python3
"""Install the private Unity Android host and collect app-specific integration logs."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import shutil
import argparse
from disco_port.adb_devices import authorized_devices
ROOT=Path(__file__).resolve().parent.parent
PACKAGE='org.discoport.androidgame'


def deploy(config_path=None, output_path=None, install_only=False, launch_only=False):
    if install_only and launch_only:raise ValueError('Choose installation or launch, not both')
    config_path=Path(config_path) if config_path else ROOT/'artifacts/local-android.json'
    output=Path(output_path) if output_path else ROOT/'artifacts/android/game-device'
    for path in (config_path,output):
        if not path.resolve().is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Device selections and reports must stay under artifacts')
    config=json.loads(config_path.read_text());serial=config['device_identifier']
    def adb(*args,check=True,binary=False,timeout=120):
        return subprocess.run(['adb','-s',serial,*map(str,args)],capture_output=True,text=not binary,errors=None if binary else 'replace',check=check,timeout=timeout)
    if serial not in authorized_devices(subprocess.check_output(['adb','devices','-l'],text=True)):
        raise ValueError('Selected tablet is not connected/authorized')
    build=ROOT/'artifacts/android/build-game';apk=build/'disco-on-the-go.apk';report=json.loads((build/'build.json').read_text())
    if hashlib.file_digest(apk.open('rb'),'sha256').hexdigest()!=report['apk_sha256']:raise ValueError('APK does not match build report')
    output.mkdir(parents=True,exist_ok=True)
    installed_report=output/'installed.json'
    if launch_only:
        previous=json.loads(installed_report.read_text()) if installed_report.is_file() else {}
        if previous.get('apk_sha256')!=report['apk_sha256'] or previous.get('device_identifier')!=serial:
            raise ValueError('Install this build into the selected report directory before --launch-only')
    if not launch_only:
        installed=adb('install','--no-incremental','-r',apk,timeout=900);(output/'install.log').write_text(installed.stdout+installed.stderr)
        adb('shell','am','force-stop',PACKAGE)
        adb('shell','run-as',PACKAGE,'rm','-f','files/NativeOverride/libil2cpp.so')
    if report.get('obb') and not launch_only:
        obb=build/'main.1.org.discoport.androidgame.obb';digest=hashlib.file_digest(obb.open('rb'),'sha256').hexdigest()
        if digest!=report['obb_sha256']:raise ValueError('Expansion file does not match build report')
        directory='/sdcard/Android/obb/'+PACKAGE;destination=directory+'/'+obb.name
        adb('shell','mkdir','-p',directory)
        existing=adb('shell','sha256sum',destination,check=False,timeout=120).stdout.split()
        if not existing or existing[0]!=digest:
            transfer=adb('push',obb,destination,timeout=1800)
            (output/'obb-upload.log').write_text(transfer.stdout+transfer.stderr)
            actual=adb('shell','sha256sum',destination,timeout=120).stdout.split()
            if not actual or actual[0]!=digest:raise ValueError('Expansion upload hash mismatch')

    if not launch_only:installed_report.write_text(json.dumps({'device_identifier':serial,'apk_sha256':report['apk_sha256'],'obb_sha256':report.get('obb_sha256')})+'\n')

    if install_only:
        print('Private APK and expansion installed; game launch deferred until streaming assets are uploaded.')
        return
    # Do not block on ActivityManager's draw wait: a native failure can leave
    # Unity's reporter running without ever presenting its first frame.
    launched=adb('shell','am','start','-n',PACKAGE+'/.GameActivity')
    (output/'launch.log').write_text(launched.stdout+launched.stderr)
    for _ in range(12):
        time.sleep(1)
        if adb('shell','pidof',PACKAGE,check=False).returncode:break
    logs=adb('logcat','-d','-t','20000','-s','DiscoRuntime:I','DiscoUnity:I','DiscoScenes:I','DiscoGraphics:I','Unity:D','AndroidRuntime:E','*:S')
    (output/'runtime.log').write_text(logs.stdout)
    alive=adb('shell','pidof',PACKAGE,check=False).returncode==0
    print('Unity Android host process remains running:',alive)
    print('Private runtime log:',(output/'runtime.log').relative_to(ROOT))
    (output/'run.json').write_text(json.dumps({'process_alive':alive,'apk_sha256':report['apk_sha256'],'scope':'Unity integration run; process survival alone does not establish gameplay'},indent=2)+'\n')
    history=output/'history'/(time.strftime('%Y%m%d-%H%M%S')+'-'+report['apk_sha256'][:8])
    history.mkdir(parents=True,exist_ok=False)
    for name in ('run.json','runtime.log','launch.log','install.log'):
        shutil.copyfile(output/name,history/name)
    if not alive:raise ValueError('Game process stopped during launch; inspect the private runtime log')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,help='Private device selection')
    parser.add_argument('--output',type=Path,help='Separate private device report directory')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--install-only',action='store_true',help='Install without launching; use before the first streaming-asset upload')
    mode.add_argument('--launch-only',action='store_true',help='Launch the previously installed build after streaming-asset upload')
    args=parser.parse_args();deploy(args.config,args.output,args.install_only,args.launch_only)
