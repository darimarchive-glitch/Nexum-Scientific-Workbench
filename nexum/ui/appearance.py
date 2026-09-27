"""One application-wide appearance preference, shared by native and GL views."""
import json
import weakref
from gi.repository import Adw, Gio, GLib

SCHEMES = {
    "system": Adw.ColorScheme.DEFAULT,
    "light": Adw.ColorScheme.FORCE_LIGHT,
    "dark": Adw.ColorScheme.FORCE_DARK,
}


class Appearance:
    def __init__(self, window, path):
        self.path = path
        self.style = Adw.StyleManager.get_default()
        try:
            choice = json.loads(path.read_text(encoding="utf-8")).get("appearance", "system")
        except (OSError, ValueError, AttributeError):
            choice = "system"
        if not isinstance(choice, str) or choice not in SCHEMES:
            choice = "system"
        self.action = Gio.SimpleAction.new_stateful("appearance", GLib.VariantType.new("s"), GLib.Variant("s", choice))
        self.action.connect("activate", self._activate)
        window.add_action(self.action)
        self.style.set_color_scheme(SCHEMES[choice])
        self.window = weakref.ref(window)

    def _activate(self, action, value):
        self.select(value.get_string())

    def select(self, choice, persist=True):
        if choice not in SCHEMES:
            raise ValueError("Tema desconhecido.")
        self.style.set_color_scheme(SCHEMES[choice])
        self.action.set_state(GLib.Variant("s", choice))
        if persist:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text(json.dumps({"appearance": choice}), encoding="utf-8")
                temporary.replace(self.path)
            except OSError:
                window = self.window()
                if window:
                    window.toast("Tema aplicado; não foi possível salvar a preferência.")

    def menu(self):
        menu = Gio.Menu()
        for title, choice in [("Seguir o sistema", "system"), ("Claro", "light"), ("Escuro", "dark")]:
            item = Gio.MenuItem.new(title, None)
            item.set_action_and_target_value("win.appearance", GLib.Variant("s", choice))
            menu.append_item(item)
        return menu


def follow_theme(view):
    """Weak signal connection: comparison windows must not retain GL widgets."""
    style = Adw.StyleManager.get_default()
    ref = weakref.ref(view)
    def update(*_):
        widget = ref()
        if widget is not None:
            widget.sync_theme()
    handler = style.connect("notify::dark", update)
    weakref.finalize(view, style.disconnect, handler)
    view.connect("map", update)
    update()
