from __future__ import annotations
from nexum.paths import data_dir
import gi
gi.require_version("Gtk","4.0");gi.require_version("Adw","1")
from gi.repository import Gtk,Adw,Gdk

from nexum.history import HistoryStore
from .home_page import HomePage
from .calculators_page import CalculatorPage
from .structures_page import StructurePage
from .experiments_page import ExperimentsPage
from .history_page import HistoryPage

CSS=b"""
.numeric-result { font-size: 2rem; font-weight: 700; font-feature-settings: 'tnum' 1; padding: 10px 4px; }
.numeric { font-feature-settings: 'tnum' 1; font-family: monospace; }
.status-pill { padding: 5px 10px; border-radius: 999px; background: alpha(@accent_bg_color,0.14); color: @accent_color; font-weight: 600; }
.sidebar { background: alpha(@window_fg_color,0.035); }
.tool-button { min-height: 34px; padding-left: 10px; padding-right: 10px; }
.selected-tool { background: alpha(@accent_bg_color,0.14); color: @accent_color; font-weight: 600; }
.floating-toolbar { padding: 5px; border-radius: 12px; background: alpha(@window_bg_color,0.92); box-shadow: 0 3px 14px alpha(black,0.14); }
.caption-heading { font-size: .78rem; font-weight: 700; opacity: .62; letter-spacing: .03em; }
.monospace { font-family: monospace; }
.large-title { font-size: 2.35rem; font-weight: 750; letter-spacing: -.025em; }
.home-card { padding: 18px; border-radius: 14px; background: alpha(@window_fg_color,0.035); border: 1px solid alpha(@window_fg_color,0.08); }
"""

class MainWindow(Adw.ApplicationWindow):
    def __init__(self,application):
        super().__init__(application=application);self.set_title("Nexum");self.set_default_size(1440,900);self.set_size_request(860,600)
        provider=Gtk.CssProvider();provider.load_from_data(CSS);Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.history=HistoryStore(data_dir()/"history.sqlite3")
        self.overlay=Adw.ToastOverlay();toolbar=Adw.ToolbarView();self.overlay.set_child(toolbar);self.set_content(self.overlay)
        header=Adw.HeaderBar();brand=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);b=Gtk.Label(label="NEXUM",xalign=0);b.add_css_class("heading");sub=Gtk.Label(label="Scientific Workbench",xalign=0);sub.add_css_class("caption");brand.append(b);brand.append(sub);header.pack_start(brand)
        self.stack=Adw.ViewStack();self.stack.set_hexpand(True);self.stack.set_vexpand(True);switcher=Adw.ViewSwitcher();switcher.set_stack(self.stack);switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE);header.set_title_widget(switcher);toolbar.add_top_bar(header)
        self.home=HomePage(self);self.calc=CalculatorPage(self,self.history);self.struct=StructurePage(self);self.exp=ExperimentsPage(self);self.hist=HistoryPage(self.history)
        self.stack.add_titled_with_icon(self.home,"home","Início","go-home-symbolic")
        self.stack.add_titled_with_icon(self.calc,"calculators","Calculadoras","accessories-calculator-symbolic")
        self.stack.add_titled_with_icon(self.struct,"structures","Estruturas 3D","applications-science-symbolic")
        self.stack.add_titled_with_icon(self.exp,"experiments","Experimentos","media-playback-start-symbolic")
        self.stack.add_titled_with_icon(self.hist,"history","Histórico","document-open-recent-symbolic")
        toolbar.set_content(self.stack)
        keys=Gtk.EventControllerKey();keys.connect("key-pressed",self._key);self.add_controller(keys)
    def toast(self,text,timeout=4):
        t=Adw.Toast.new(str(text));t.set_timeout(timeout);self.overlay.add_toast(t);return False
    def _key(self,controller,keyval,keycode,state):
        if keyval==Gdk.KEY_Escape and getattr(self.struct,"_fullscreen",False):self.struct._toggle_fullscreen();return True
        return False
