#!/usr/bin/env python3
"""Upload this project's private streaming assets without touching saved games."""
import json
from pathlib import Path
import subprocess
import argparse
from disco_port.adb_devices import authorized_devices
ROOT=Path(__file__).resolve().parent.parent

def upload(config=None,log=None):
    config=Path(config) if config else ROOT/'artifacts/local-android.json'
    log=Path(log) if log else ROOT/'artifacts/android/assets-upload.log'
    for path in (config,log):
        if not path.resolve().is_relative_to((ROOT/'artifacts').resolve()):raise ValueError('Device selections and logs must stay under artifacts')
    serial=json.loads(config.read_text())['device_identifier']
    if serial not in authorized_devices(subprocess.check_output(['adb','devices','-l'],text=True)):raise ValueError('Tablet unavailable')
    source=ROOT/'artifacts/android/game-data/external/GameFiles'
    if not (ROOT/'artifacts/android/game-data/manifest.json').is_file():raise ValueError('Complete staging manifest missing')
    destination='/sdcard/Android/data/org.discoport.androidgame/files/GameFiles'
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as output:
        subprocess.run(['adb','-s',serial,'shell','mkdir','-p',destination],check=True,stdout=output,stderr=subprocess.STDOUT)
        subprocess.run(['adb','-s',serial,'push','--sync',str(source)+'/.',destination+'/'],check=True,stdout=output,stderr=subprocess.STDOUT)
    print('Streaming assets uploaded to the game app directory.')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,help='Private device selection')
    parser.add_argument('--log',type=Path,help='Separate private transfer log')
    args=parser.parse_args();upload(args.config,args.log)
