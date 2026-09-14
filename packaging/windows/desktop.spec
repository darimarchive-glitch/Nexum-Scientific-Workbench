from pathlib import Path
root = Path(SPECPATH).parent.parent
analysis = Analysis([str(root/'packaging/desktop_entry.py')], pathex=[str(root)],
    datas=[(str(root/'nexum/assets/logo.svg'),'nexum/assets')],
    hiddenimports=['gi.repository.Gtk','gi.repository.Adw','gi.repository.Gdk','cairo','gi._gi_cairo'],
    excludes=['rdkit','gemmi'],
    hooksconfig={'gi': {'icons':['Adwaita','hicolor'], 'languages':['pt_BR','en_US'],
                       'module-versions':{'Gtk':'4.0','Gdk':'4.0'}}})
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='Nexum', icon=str(root/'build/icons/nexum.ico'), console=False)
coll = COLLECT(exe, analysis.binaries, analysis.datas, name='Nexum')

