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
    import contextlib
    import faulthandler
    import traceback
    log=Path(os.environ.get('NEXUM_SELF_TEST_LOG',str(Path.home()/'nexum-self-test.log')))
    # Windowed executables have no stdout/stderr. Keep a real file open for
    # both Python exceptions and native crash diagnostics throughout the test.
    with log.open('w',encoding='utf-8') as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            try:
                from nexum.windows_check import main
                main()
            except Exception:
                traceback.print_exc()
                raise SystemExit(1)
            finally:
                faulthandler.disable()
else:
    from nexum.main import main
    main()
