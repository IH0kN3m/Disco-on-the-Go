"""Original app identity and locally derived game icons. No artwork is bundled."""
import json
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess

from .binary import FormatError

APP_NAME = 'Disco on the Go'
IPAD_APP = APP_NAME + '.app'
APK_NAME = 'disco-on-the-go.apk'


def validate_icns(data):
    if len(data)<8 or data[:4]!=b'icns' or struct.unpack_from('>I',data,4)[0]!=len(data):
        raise FormatError('Invalid game icon container')
    at,count=8,0
    while at<len(data):
        if at+8>len(data): raise FormatError('Truncated game icon entry')
        size=struct.unpack_from('>I',data,at+4)[0]
        if size<8 or size>len(data)-at or count>=4096: raise FormatError('Invalid game icon bounds')
        at+=size;count+=1
    if not count: raise FormatError('Empty game icon container')


def source_icon(bundle):
    name=plistlib.loads((bundle/'Contents/Info.plist').read_bytes()).get('CFBundleIconFile')
    if not isinstance(name,str) or Path(name).name!=name or name in ('.','..'):
        raise FormatError('Unsupported game icon ownership')
    if not name.endswith('.icns'):name+='.icns'
    path=bundle/'Contents/Resources'/name
    if not path.resolve().is_relative_to(bundle.resolve()) or not path.is_file():
        raise FormatError('Game icon escapes the supplied bundle')
    validate_icns(path.read_bytes())
    return path


def prepare(root):
    from PIL import Image
    output=root/'artifacts/branding';output.mkdir(parents=True,exist_ok=True)
    iconset=output/'source.iconset'
    if iconset.exists():shutil.rmtree(iconset)
    subprocess.run(['iconutil','-c','iconset',str(source_icon(root/'reference/Disco.app')),'-o',str(iconset)],check=True,capture_output=True)
    original=iconset/'icon_512x512@2x.png'
    with Image.open(original) as icon:
        if icon.size!=(1024,1024):raise FormatError('Expected the supplied 1024px game icon')
        # iOS app icons must be opaque. Composite on black without JPEG loss.
        opaque=Image.new('RGBA',icon.size,'black');opaque.alpha_composite(icon.convert('RGBA'))
        opaque.convert('RGB').save(output/'app-icon.png')
        android=output/'android-res/drawable';android.mkdir(parents=True,exist_ok=True)
        icon.convert('RGBA').resize((192,192),Image.Resampling.LANCZOS).save(android/'disco_icon.png')
    return output


def name_ipad_project(xcode):
    objects=xcode['objects']
    apps=[v for v in objects.values() if v.get('isa')=='PBXNativeTarget' and v.get('name')=='Unity-iPhone']
    if len(apps)!=1:raise FormatError('Expected one owning iPad app target')
    app=apps[0];configurations=objects[app['buildConfigurationList']]['buildConfigurations']
    if not configurations or len(set(configurations))!=len(configurations):raise FormatError('Invalid app configurations')
    for owner in objects.values():
        if owner is not app and 'buildConfigurationList' in owner:
            if set(configurations)&set(objects[owner['buildConfigurationList']]['buildConfigurations']):
                raise FormatError('App branding settings are shared with another target')
    for config in configurations:
        settings=objects[config]['buildSettings']
        settings['PRODUCT_NAME']=APP_NAME
        settings['ASSETCATALOG_COMPILER_APPICON_NAME']='AppIcon'
    objects[app['productReference']]['path']=IPAD_APP


def configure_ipad(project, icon_root):
    from PIL import Image
    path=project/'Unity-iPhone.xcodeproj/project.pbxproj'
    xcode=plistlib.loads(path.read_bytes())
    name_ipad_project(xcode)
    path.write_bytes(plistlib.dumps(xcode))
    info_path=project/'Info.plist';info=plistlib.loads(info_path.read_bytes())
    info['CFBundleDisplayName']=APP_NAME;info['CFBundleName']=APP_NAME
    info_path.write_bytes(plistlib.dumps(info))
    catalog=project/'Unity-iPhone/Images.xcassets/AppIcon.appiconset'
    if not catalog.is_dir():raise FormatError('Unsupported iPad app icon catalog')
    slots=[('ipad',20,1),('ipad',20,2),('ipad',29,1),('ipad',29,2),
           ('ipad',40,1),('ipad',40,2),('ipad',76,1),('ipad',76,2),('ipad',83.5,2),('ios-marketing',1024,1)]
    images=[]
    with Image.open(icon_root/'app-icon.png') as source:
        for idiom,size,scale in slots:
            pixels=int(size*scale);name=f'icon-{pixels}.png'
            source.resize((pixels,pixels),Image.Resampling.LANCZOS).save(catalog/name)
            images.append({'idiom':idiom,'size':f'{size}x{size}','scale':f'{scale}x','filename':name})
    (catalog/'Contents.json').write_text(json.dumps({'images':images,'info':{'version':1,'author':'xcode'}},indent=2)+'\n')
