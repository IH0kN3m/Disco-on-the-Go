#!/usr/bin/env python3
"""Install build dependencies; game builds themselves remain offline."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent

def setup(platform):
    if sys.platform!='darwin' or sys.version_info<(3,11):raise ValueError('Use macOS with Python 3.11 or newer')
    if platform=='android':
        sdk=Path(os.environ.get('ANDROID_HOME',Path.home()/'Library/Android/sdk'))
        manager=sdk/'cmdline-tools/latest/bin/sdkmanager'
        if not manager.is_file():raise ValueError('Install Android SDK Command-line Tools (latest); see docs/ANDROID.md')
        java=Path(subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip())
        env=dict(os.environ,JAVA_HOME=str(java))
        subprocess.run([str(manager),'platform-tools','platforms;android-36','build-tools;36.0.0','ndk;27.2.12479018'],env=env,check=True)
    subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    python=ROOT/'.venv/bin/python'
    subprocess.run([str(python),'-m','pip','install','--cache-dir',str(ROOT/'artifacts/cache/pip'),'-r',str(ROOT/'requirements.lock')],check=True)
    for tool in ['setup_unity']+(['setup_unity_android','setup_android_legacy','setup_glslang'] if platform=='android' else []):
        subprocess.run([sys.executable,str(ROOT/'tools'/f'{tool}.py')],check=True)
    print('Tools ready. Activate the Unity license if needed, then run make doctor'+(' PLATFORM=android' if platform=='android' else '')+'.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--platform',choices=['ipad','android'],default='ipad');a=p.parse_args()
    try:setup(a.platform)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:p.exit(1,f'Setup failed: {error}\n')
