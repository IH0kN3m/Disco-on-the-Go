#!/usr/bin/env python3
"""Install the complete local game, including assets, on a selected device."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from disco_port.adb_devices import authorized_devices
ROOT=Path(__file__).resolve().parent.parent

def install(platform):
    def tool(name,*args):subprocess.run([sys.executable,str(ROOT/'tools'/f'{name}.py'),*args],cwd=ROOT,check=True)
    if platform=='ipad':
        if not (ROOT/'artifacts/local-ipad.json').is_file():raise ValueError('Create artifacts/local-ipad.json with your team, device and bundle ID; see docs/IPAD.md')
        tool('deploy_ipad')
    else:
        config=ROOT/'artifacts/local-android.json'
        if not config.is_file():
            devices=authorized_devices(subprocess.check_output(['adb','devices','-l'],text=True))
            if len(devices)!=1:raise ValueError('Connect one authorized Android device, or set device_identifier in artifacts/local-android.json')
            config.parent.mkdir(parents=True,exist_ok=True)
            config.write_text(json.dumps({'device_identifier':devices[0]})+'\n')
        print('Installing APK and core data; first installation also uploads streaming assets.',flush=True)
        tool('deploy_android_game','--install-only');tool('upload_android_assets');tool('deploy_android_game','--launch-only')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--platform',choices=['ipad','android'],default='ipad');a=p.parse_args()
    try:install(a.platform)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:p.exit(1,f'Installation failed: {error}\n')
