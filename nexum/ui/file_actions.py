"""Native file dialogs and background operations with visible errors."""
from pathlib import Path
import threading
import gi
gi.require_version("Gtk","4.0")
from gi.repository import Gtk, GLib

def choose(window,title,callback,save=False,name=None):
    dialog=Gtk.FileChooserNative.new(title,window,Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN,"Salvar" if save else "Abrir","Cancelar")
    if save and name:dialog.set_current_name(name)
    def response(d,result):
        try:
            if result==Gtk.ResponseType.ACCEPT:
                file=d.get_file()
                if not file or not file.get_path():raise ValueError("Escolha um arquivo local.")
                callback(Path(file.get_path()))
        except Exception as exc:window.toast(str(exc),timeout=8)
        finally:d.destroy()
    dialog.connect("response",response);dialog.show()
    return dialog

def background(window,work,done):
    def run():
        try:result=work()
        except Exception as exc:GLib.idle_add(window.toast,str(exc),8)
        else:
            def apply():
                try:done(result)
                except Exception as exc:window.toast(str(exc),timeout=8)
                return False
            GLib.idle_add(apply)
    threading.Thread(target=run,daemon=True).start()
