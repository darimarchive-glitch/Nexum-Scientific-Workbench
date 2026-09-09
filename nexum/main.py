from __future__ import annotations
import gi
gi.require_version("Gtk","4.0");gi.require_version("Adw","1")
from gi.repository import Adw,Gio
from .ui.main_window import MainWindow

class NexumApplication(Adw.Application):
    def __init__(self):super().__init__(application_id="io.github.nexum.ScientificWorkbench",flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
    def do_activate(self):
        win=self.props.active_window
        if win is None:win=MainWindow(self)
        win.present()

def main():
    import sys
    return NexumApplication().run(sys.argv)
if __name__=="__main__":raise SystemExit(main())
