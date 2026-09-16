"""Frozen desktop entry point; never requires a Python install on the host."""
import os
from pathlib import Path
import sys

if sys.platform == 'win32':
    import contextlib
    import traceback
    from nexum.windows_graphics import configure, probe, select_mode
    bundle = Path(sys.executable).parent
    if '--graphics-probe' in sys.argv:
        log = Path(os.environ['NEXUM_GRAPHICS_PROBE_LOG'])
        with log.open('w', encoding='utf-8') as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                try:
                    configure(sys.argv[-1], bundle)
                    probe()
                except Exception:
                    traceback.print_exc()
                    raise SystemExit(1)
        raise SystemExit(0)
    try:
        logs = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Nexum' / 'graphics'
        mode = select_mode(sys.executable, os.environ.get('NEXUM_GRAPHICS', 'auto'), logs)
        configure(mode, bundle)
    except Exception as error:
        import ctypes
        if '--self-test' in sys.argv:
            Path(os.environ.get('NEXUM_SELF_TEST_LOG', str(Path.home() / 'nexum-self-test.log'))).write_text(str(error), encoding='utf-8')
        else:
            ctypes.windll.user32.MessageBoxW(None, str(error), 'Nexum — diagnóstico gráfico', 0x10)
        raise SystemExit(1)
    if getattr(sys, 'frozen', False):
        os.environ['NEXUM_CHEMISTRY_EXECUTABLE'] = str(bundle / 'chemistry' / 'NexumChemistry.exe')

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

