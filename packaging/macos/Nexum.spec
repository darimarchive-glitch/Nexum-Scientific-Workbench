"""Native single-architecture macOS application; run on the target Mac."""
from pathlib import Path
import os
import platform
import sys
from PyInstaller.utils.hooks import collect_all
root=Path(SPECPATH).parent.parent
sys.path.insert(0,str(root))
from nexum.identity import APP_ID,VERSION
if sys.platform!='darwin':raise SystemExit('Build the macOS app on macOS.')
arch=platform.machine()
if arch not in ('arm64','x86_64'):raise SystemExit('Unsupported Mac architecture.')
rd_data,rd_bins,rd_hidden=collect_all('rdkit')
ge_data,ge_bins,ge_hidden=collect_all('gemmi')
a=Analysis([str(root/'packaging/desktop_entry.py')],pathex=[str(root)],
    datas=rd_data+ge_data+[(str(root/'nexum/assets/logo.svg'),'nexum/assets'),(str(root/'nexum/assets/nexum-analysis-symbolic.svg'),'nexum/assets'),(str(root/'LICENSE'),'.')],
    binaries=rd_bins+ge_bins,
    hiddenimports=rd_hidden+ge_hidden+['gi.repository.Gtk','gi.repository.Adw','gi.repository.Gdk','cairo','gi._gi_cairo','PIL.GifImagePlugin'],
    hooksconfig={'gi':{'icons':['Adwaita','hicolor'],'languages':['pt_BR','en_US'],'module-versions':{'Gtk':'4.0','Gdk':'4.0'}}})
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='Nexum',console=False,
        target_arch=arch,codesign_identity=os.environ.get('NEXUM_MAC_SIGN_IDENTITY') or None,
        entitlements_file=str(root/'packaging/macos/entitlements.plist'))
coll=COLLECT(exe,a.binaries,a.datas,name='Nexum')
app=BUNDLE(coll,name='Nexum.app',icon=str(root/'build/icons/nexum.icns'),bundle_identifier=APP_ID,
           version=VERSION.split('-')[0],info_plist={
               'CFBundleDisplayName':'Nexum','CFBundleName':'Nexum','CFBundleVersion':'70002',
               'CFBundleShortVersionString':VERSION.split('-')[0],
               'NSHighResolutionCapable':True,'NSSupportsAutomaticGraphicsSwitching':True,
               'LSApplicationCategoryType':'public.app-category.education','LSMinimumSystemVersion':'13.0'})
