"""Frozen desktop entry point; never requires a Python install on the host."""
import os
from pathlib import Path
import sys

if sys.platform == 'win32':
    os.environ['GDK_BACKEND']='win32'
    os.environ['GDK_DISABLE']='egl,gles-api'
    os.environ['PYOPENGL_PLATFORM']='win32'
    if getattr(sys,'frozen',False):
        os.environ['NEXUM_CHEMISTRY_EXECUTABLE']=str(Path(sys.executable).parent/'chemistry'/'NexumChemistry.exe')

if '--self-test' in sys.argv:
    from nexum.windows_check import main
    main()
else:
    from nexum.main import main
    main()
