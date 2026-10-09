#!/usr/bin/env python3
"""Install the local Android probe and retrieve its capabilities; not gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from disco_port.android_probe import authorized_devices

ROOT=Path(__file__).resolve().parent.parent
PACKAGE='org.discoport.androidprobe'


def deploy(original=False, mapped=False):
    output=ROOT/'artifacts/android/device';output.mkdir(parents=True,exist_ok=True)
    def adb(arguments):
        result=subprocess.run(['adb',*arguments],capture_output=True,text=True,timeout=90)
        with (output/'adb.log').open('a') as log: log.write(result.stdout+result.stderr)
        if result.returncode: raise ValueError('ADB operation failed; inspect artifacts/android/device/adb.log')
        return result.stdout.strip()
    devices=authorized_devices(adb(['devices','-l']))
    config=ROOT/'artifacts/local-android.json'
    serial=json.loads(config.read_text()).get('device_identifier') if config.exists() else None
    if serial is None:
        if len(devices)!=1: raise ValueError('Connect and authorize exactly one tablet, or select it in artifacts/local-android.json')
        serial=devices[0]
    if serial not in devices: raise ValueError('Configured Android tablet is not authorized/connected')
    def shell(*args): return adb(['-s',serial,'shell',*args])
    properties={k:shell('getprop',k) for k in ('ro.product.model','ro.product.manufacturer','ro.product.cpu.abilist','ro.build.version.sdk','ro.kernel.qemu')}
    (output/'properties.json').write_text(json.dumps(properties,indent=2)+'\n')
    if properties['ro.kernel.qemu']=='1' or 'arm64-v8a' not in properties['ro.product.cpu.abilist'].split(',') or int(properties['ro.build.version.sdk'])<28:
        raise ValueError('Probe requires a physical ARM64 Android device on API 28+')
    # Initial automatic discovery is deliberately scoped to the requested tablet family.
    if not config.exists() and not properties['ro.product.model'].startswith('SM-X92'):
        raise ValueError('Connected device is not the requested Tab S10 Ultra family; explicitly select an intended tablet in artifacts/local-android.json')
    config.write_text(json.dumps({'device_identifier':serial},indent=2)+'\n')
    build=ROOT/'artifacts/android'/('build-mapped-runtime' if mapped else 'build-original-leaf' if original else 'build-capabilities')
    apk=build/'disco-android-probe.apk'
    report=json.loads((build/'build.json').read_text())
    if hashlib.sha256(apk.read_bytes()).hexdigest()!=report['apk_sha256'] or report['original_leaf'] is not original or report.get('mapped_runtime',False) is not mapped:
        raise ValueError('APK differs from its local build report')
    adb(['-s',serial,'install','-r',str(apk)])
    shell('am','force-stop',PACKAGE)
    shell('run-as',PACKAGE,'rm','-f','files/capabilities.json')
    launch=shell('am','start','-W','-n',PACKAGE+'/.ProbeActivity')
    (output/'launch.txt').write_text(launch+'\n')
    if 'Status: ok' not in launch: raise ValueError('Android did not report successful activity launch')
    data=None
    for _ in range(15):
        result=subprocess.run(['adb','-s',serial,'shell','run-as',PACKAGE,'cat','files/capabilities.json'],capture_output=True,text=True,timeout=10)
        if result.returncode==0:
            data=json.loads(result.stdout);break
        alive=subprocess.run(['adb','-s',serial,'shell','pidof',PACKAGE],capture_output=True,text=True,timeout=10)
        if alive.returncode: break
        time.sleep(1)
    log=adb(['-s',serial,'logcat','-d','-s','DiscoRuntime:I','*:S'])
    (output/'runtime-logcat.txt').write_text(log+'\n')
    if data is None:
        raise ValueError('Probe produced no report; inspect artifacts/android/device/runtime-logcat.txt')
    (output/'capabilities.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))
    if original and data.get('original_leaf_tests_passed') is not True:
        raise ValueError('Original ARM64 arithmetic did not pass on this device')
    if mapped:
        trial=data.get('mapped_runtime_trial',{})
        required=('passed','full_runtime_initialized','thread_bridge_passed','metadata_invocation_passed','gc_collection_returned','executable_bytes_unchanged')
        if any(trial.get(key) is not True for key in required) or trial.get('initializers_completed')!=10:
            raise ValueError('Mapped original runtime startup checks did not pass; inspect DiscoRuntime log')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-original-kernel',action='store_true')
    parser.add_argument('--with-mapped-runtime',action='store_true')
    args=parser.parse_args()
    try:deploy(args.with_original_kernel,args.with_mapped_runtime)
    except (ValueError,OSError,subprocess.SubprocessError) as error:parser.exit(1,f'Android deployment failed: {error}\n')
