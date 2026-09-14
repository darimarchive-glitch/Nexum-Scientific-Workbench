"""Install an importable bytecode archive, compiled with the target SDK Python."""
from pathlib import Path
import compileall
import shutil
import zipfile

stage=Path('bytecode-stage')
shutil.copytree('nexum',stage/'nexum',dirs_exist_ok=True)
(stage/'__main__.py').write_text('from nexum.main import main\nraise SystemExit(main())\n')
if not compileall.compile_dir(stage,quiet=1,legacy=True,force=True):
    raise SystemExit('Falha ao compilar os módulos do aplicativo.')
target=Path('/app/share/nexum');target.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(target/'nexum.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in stage.rglob('*.pyc'):
        if '__pycache__' not in path.parts:
            archive.write(path,path.relative_to(stage))
    archive.write('nexum/assets/logo.svg','nexum/assets/logo.svg')
shutil.copyfile('LICENSE',target/'LICENSE')
shutil.copyfile('WHEELS.sha256',target/'WHEELS.sha256')

