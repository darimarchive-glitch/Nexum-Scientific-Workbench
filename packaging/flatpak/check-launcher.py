"""Verify the installed host desktop entry, not only files inside the sandbox."""
import os
from pathlib import Path
import subprocess
from gi.repository import Gio
APP_ID='io.github.nexum.ScientificWorkbench'
location=Path(subprocess.check_output(['flatpak','info','--user','--show-location',APP_ID],text=True).strip())
entry=location/'export/share/applications'/f'{APP_ID}.desktop'
subprocess.run(['desktop-file-validate',str(entry)],check=True)
app=Gio.DesktopAppInfo.new(APP_ID+'.desktop')
assert app is not None, 'Nexum ausente da busca de aplicativos do sistema'
assert app.should_show(), 'Atalho oculto no ambiente desktop'
assert APP_ID in app.get_commandline() and 'flatpak' in app.get_commandline()
assert app.get_icon().to_string()==APP_ID
assert (location/'files/share/icons/hicolor/scalable/apps'/f'{APP_ID}.svg').is_file()
print('Atalho exportado, visibilidade no menu, comando e logo: OK')
