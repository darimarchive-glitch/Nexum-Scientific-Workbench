"""Select Windows OpenGL before importing GTK or PyOpenGL.

Probe in a separate process: a failed driver must not poison the application's
DLL/context state. Mesa is private to Nexum and never installed system-wide.
"""
import os
from pathlib import Path
import subprocess
import sys

_dll_handles = []


def configure(mode, bundle):
    if mode not in ('native', 'software'):
        raise ValueError('Modo gráfico inválido: ' + mode)
    os.environ['GDK_BACKEND'] = 'win32'
    # The viewer uses desktop GLSL 330 and PyOpenGL's WGL loader. ANGLE/GLES
    # cannot be enabled independently of both of these components.
    os.environ['GDK_DISABLE'] = 'egl,gles-api'
    os.environ['PYOPENGL_PLATFORM'] = 'win32'
    os.environ['NEXUM_GRAPHICS_ACTIVE'] = mode
    if mode == 'software':
        folder = Path(bundle) / 'mesa'
        driver = folder / 'opengl32.dll'
        if not driver.is_file():
            raise RuntimeError('O componente gráfico de compatibilidade não foi encontrado. Reinstale o Nexum.')
        import ctypes
        _dll_handles.append(os.add_dll_directory(str(folder)))
        # Load by absolute path before GTK/epoxy/PyOpenGL can load system GL.
        # Windows DLL search flags require a native absolute path. In MSYS2,
        # pathlib emits forward slashes; ALTERED_SEARCH_PATH then fails to
        # resolve Mesa's adjacent libgallium_wgl.dll. Use the modern loader
        # search with DLL_LOAD_DIR plus DEFAULT_DIRS instead.
        native_path = str(driver.resolve()).replace('/', '\\')
        mesa = ctypes.WinDLL(native_path, winmode=0x1100)
        _dll_handles.append(mesa)
        # PyOpenGL's find_library('opengl32') returns the SYSTEM DLL even
        # when Mesa is loaded. Bind its WGL functions to the same DLL as GTK
        # before importing any GL wrappers; mixing them has no current context.
        from OpenGL import platform
        from OpenGL.platform.win32 import Win32Platform
        binding = Win32Platform()
        binding.GL = mesa
        binding.install(vars(platform))
        os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
        os.environ['GSK_RENDERER'] = 'cairo'


def probe():
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk, Gdk
    if not Gtk.init_check():
        raise RuntimeError('Não foi possível iniciar a sessão gráfica.')
    context = Gdk.Display.get_default().create_gl_context()
    context.set_allowed_apis(Gdk.GLAPI.GL)
    context.set_required_version(3, 3)
    context.realize()
    context.make_current()
    try:
        from OpenGL import GL
        from OpenGL import platform
        if not platform.GetCurrentContext():
            raise RuntimeError('GTK e PyOpenGL não compartilham o contexto gráfico.')
        version = GL.glGetString(GL.GL_VERSION)
        renderer = GL.glGetString(GL.GL_RENDERER)
        if not version or not renderer:
            raise RuntimeError('O driver não respondeu à consulta OpenGL.')
        if os.environ['NEXUM_GRAPHICS_ACTIVE'] == 'software' and b'llvmpipe' not in renderer.lower():
            raise RuntimeError('O driver de compatibilidade não foi carregado: ' + repr(renderer))
        print('OpenGL:', version, 'Renderer:', renderer, flush=True)
    finally:
        Gdk.GLContext.clear_current()


def select_mode(executable, requested, log_dir, runner=subprocess.run):
    if requested not in ('auto', 'native', 'software'):
        raise ValueError('NEXUM_GRAPHICS deve ser auto, native ou software.')
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    modes = ('native', 'software') if requested == 'auto' else (requested,)
    for mode in modes:
        env = dict(os.environ, NEXUM_GRAPHICS_PROBE_LOG=str(log_dir / (mode + '.log')))
        try:
            result = runner([str(executable), '--graphics-probe', mode], env=env,
                            timeout=25, check=False, creationflags=0x08000000)
            if result.returncode == 0:
                (log_dir / 'selected.txt').write_text(mode + '\n', encoding='utf-8')
                return mode
        except (subprocess.TimeoutExpired, OSError) as error:
            (log_dir / (mode + '.log')).write_text(str(error), encoding='utf-8')
    raise RuntimeError('Não foi possível iniciar o visualizador 3D.\n'
                       'Atualize o driver de vídeo ou reinstale o Nexum.\n'
                       'Diagnóstico: ' + str(log_dir))
