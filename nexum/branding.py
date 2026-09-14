"""Official logo, shared by the native application and packaged builds."""
from importlib.resources import files
from pathlib import Path
from .paths import cache_dir
APP_ID='io.github.nexum.ScientificWorkbench'

def icon_directory():
    logo=files('nexum').joinpath('assets/logo.svg').read_bytes()
    folder=cache_dir()/'icons'/'hicolor'/'scalable'/'apps'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(APP_ID+'.svg')
    if not target.exists() or target.read_bytes()!=logo:target.write_bytes(logo)
    (folder.parents[1]/'index.theme').write_text('[Icon Theme]\nName=Nexum\nComment=Official Nexum icon\nDirectories=scalable/apps\n\n[scalable/apps]\nSize=128\nType=Scalable\nMinSize=16\nMaxSize=512\nContext=Applications\n',encoding='utf-8')
    return folder.parents[2]

def install_icons():
    from gi.repository import Gtk,Gdk
    Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(icon_directory()))
    Gtk.Window.set_default_icon_name(APP_ID)
