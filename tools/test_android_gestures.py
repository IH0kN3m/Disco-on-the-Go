#!/usr/bin/env python3
"""Deliver a bounded real two-finger gesture to the foreground game; retain private evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from disco_port.android_probe import authorized_devices

ROOT=Path(__file__).resolve().parent.parent
PACKAGE='org.discoport.androidprobe'


def main(config,output,gesture):
    for path in (config,output):
        if not path.resolve().is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Device selections and captures must stay under artifacts')
    serial=json.loads(config.read_text())['device_identifier']
    if serial not in authorized_devices(subprocess.check_output(['adb','devices'],text=True)):raise ValueError('Selected device unavailable')
    def adb(*args,binary=False):return subprocess.run(['adb','-s',serial,*map(str,args)],capture_output=True,text=not binary,errors=None if binary else 'replace',check=True,timeout=120)
    build=ROOT/'artifacts/android/build-capabilities';apk=build/'disco-android-probe.apk'
    if hashlib.sha256(apk.read_bytes()).hexdigest()!=json.loads((build/'build.json').read_text())['apk_sha256']:raise ValueError('Probe APK differs from build report')
    output.mkdir(parents=True,exist_ok=True)
    (output/'install.log').write_text(adb('install','--no-incremental','-r',apk).stdout)
    stamp=adb('shell',"date '+%m-%d %H:%M:%S.000'").stdout.strip()
    result=adb('shell','am','instrument','-w','-e','gesture',gesture,PACKAGE+'/.GestureInstrumentation')
    (output/'instrumentation.log').write_text(result.stdout+result.stderr)
    logs=adb('logcat','-d','-T',stamp).stdout
    (output/'all.log').write_text(logs)
    if 'INSTRUMENTATION_CODE: 0' not in result.stdout:raise ValueError('Gesture delivery failed; inspect private instrumentation.log and all.log')
    for name in ('before','during','after'):
        (output/(name+'.png')).write_bytes(adb('exec-out','run-as',PACKAGE,'cat','files/gesture-'+name+'.png',binary=True).stdout)
    logs=adb('logcat','-d','-T',stamp,'-s','DiscoScenes:I','DiscoUnity:I','DiscoRuntime:I','Unity:D','AndroidRuntime:E','*:S').stdout
    (output/'runtime.log').write_text(logs)
    print('Two-finger',gesture,'delivered. Camera diagnostics:')
    print('\n'.join(l for l in logs.splitlines() if 'gesture begin' in l or 'Android pinch' in l))
    print('Input delivery alone does not establish game behavior; inspect captures and logs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'artifacts/local-android.json')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/android/gesture-test')
    parser.add_argument('--gesture',choices=('pinch','hold'),required=True)
    args=parser.parse_args();main(args.config,args.output,args.gesture)
