"""Native reusable controls for the scientific laboratory."""

import math
from gi.repository import Gtk, Adw
from nexum.core.structures import element_color


def label(text, heading=False):
    w = Gtk.Label(label=text, xalign=0)
    w.set_wrap(True)
    w.set_selectable(True)
    if heading:
        w.add_css_class("title-3")
    return w


def page(title, description):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("top", "bottom", "start", "end"):
        getattr(box, "set_margin_" + side)(18)
    box.append(label(title, True))
    box.append(label(description))
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_child(box)
    return scroll, box


def entry(box, title, text="", placeholder=None):
    row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    row.append(label(title))
    e = Gtk.Entry(text=str(text))
    e.set_hexpand(True)
    if placeholder:
        e.set_placeholder_text(placeholder)
    row.append(e)
    box.append(row)
    return e


def dropdown(box, title, items):
    box.append(label(title))
    d = Gtk.DropDown.new_from_strings(items)
    box.append(d)
    return d


def buttons(box, owner, items):
    row = Gtk.FlowBox()
    row.set_selection_mode(Gtk.SelectionMode.NONE)
    row.set_max_children_per_line(5)
    row.set_column_spacing(6)
    row.set_row_spacing(6)
    for title, fn in items:
        b = Gtk.Button(label=title)
        b.connect("clicked", lambda _, f=fn: owner.guard(f))
        row.append(b)
    box.append(row)
    return row


def textview(box, height=130, editable=True):
    v = Gtk.TextView()
    v.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    v.set_editable(editable)
    v.set_left_margin(10)
    v.set_right_margin(10)
    v.set_top_margin(10)
    v.set_bottom_margin(10)
    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(height)
    scroll.set_child(v)
    box.append(scroll)
    return v


def text(v):
    b = v.get_buffer()
    return b.get_text(b.get_start_iter(), b.get_end_iter(), True)


def settext(v, s):
    v.get_buffer().set_text(str(s))


def number(e):
    return float(e.get_text().strip().replace(",", "."))


class GraphCanvas(Gtk.DrawingArea):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.selected = None
        self.positions = []
        self.set_content_height(380)
        self.set_hexpand(True)
        self.set_draw_func(self.draw)
        click = Gtk.GestureClick.new()
        click.connect("released", self.click)
        self.add_controller(click)
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self.begin)
        drag.connect("drag-end", self.end)
        self.add_controller(drag)
        self.drag_origin = None

    def mapping(self, w, h):
        atoms = self.owner.project.data["graph"]["atoms"]
        if not atoms:
            return (w / 2, h / 2, 55.0)
        xs = [a.get("x", 0) for a in atoms]
        ys = [a.get("y", 0) for a in atoms]
        scale = min(
            55.0,
            max(1, w - 90) / max(1, max(xs) - min(xs)),
            max(1, h - 90) / max(1, max(ys) - min(ys)),
        )
        return (
            w / 2 - (max(xs) + min(xs)) / 2 * scale,
            h / 2 + (max(ys) + min(ys)) / 2 * scale,
            scale,
        )

    def draw(self, area, cr, w, h):
        dark = Adw.StyleManager.get_default().get_dark()
        cr.set_source_rgb(*((0.12, 0.15, 0.18) if dark else (0.97, 0.98, 1)))
        cr.paint()
        ox, oy, scale = self.mapping(w, h)
        g = self.owner.project.data["graph"]
        self.positions = [
            (ox + a.get("x", 0) * scale, oy - a.get("y", 0) * scale) for a in g["atoms"]
        ]
        cr.set_line_width(2)
        for i, j, order in g["bonds"]:
            x, y = self.positions[i]
            xx, yy = self.positions[j]
            angle = math.atan2(yy - y, xx - x)
            cr.set_source_rgb(*((0.8, 0.84, 0.88) if dark else (0.25, 0.32, 0.4)))
            count = 2 if order == 1.5 else max(1, int(order))
            for k in range(count):
                cr.set_dash([4, 3] if order == 1.5 and k == 1 else [])
                offset = (k - (count - 1) / 2) * 5
                dx = -math.sin(angle) * offset
                dy = math.cos(angle) * offset
                cr.move_to(x + dx, y + dy)
                cr.line_to(xx + dx, yy + dy)
                cr.stroke()
            cr.set_dash([])
        for i, (a, (x, y)) in enumerate(zip(g["atoms"], self.positions)):
            color = (
                (0.9, 0.64, 0.1) if i == self.selected else element_color(a["element"])
            )
            cr.set_source_rgb(*color)
            cr.arc(x, y, 18, 0, math.tau)
            cr.fill()
            cr.set_source_rgb(*((0.1, 0.15, 0.2) if sum(color) > 1.7 else (1, 1, 1)))
            cr.select_font_face("Sans", 0, 1)
            cr.set_font_size(14)
            cr.move_to(x - 7, y + 5)
            cr.show_text(
                a["element"] + (f"{a['charge']:+d}" if a.get("charge") else "")
            )
            cr.set_source_rgb(*((0.85, 0.85, 0.85) if dark else (0.2, 0.25, 0.3)))
            cr.set_font_size(10)
            cr.move_to(x + 17, y - 16)
            cr.show_text(str(i + 1))
        if not g["atoms"]:
            cr.set_source_rgb(0.4, 0.5, 0.6)
            cr.set_font_size(16)
            cr.move_to(30, 50)
            cr.show_text("Clique para adicionar o primeiro átomo.")

    def nearest(self, x, y):
        found = [
            (math.hypot(x - a, y - b), i) for i, (a, b) in enumerate(self.positions)
        ]
        return min(found)[1] if found and min(found)[0] < 22 else None

    def begin(self, gesture, x, y):
        if self.owner.editor_mode.get_selected() == 4:
            self.drag_origin = (
                self.nearest(x, y),
                self.mapping(self.get_width(), self.get_height())[2],
            )

    def end(self, gesture, dx, dy):
        if self.owner.editor_mode.get_selected() != 4 or not self.drag_origin:
            return
        i, scale = self.drag_origin
        self.drag_origin = None
        if i is None:
            return

        def change(d):
            a = d["graph"]["atoms"][i]
            a["x"] += dx / scale
            a["y"] -= dy / scale
            d["molecule"] = None

        self.owner.guard(lambda: self.owner.change("Mover átomo no desenho 2D", change))

    def click(self, gesture, n, x, y):
        self.owner.guard(lambda: self.clicked(x, y))

    def clicked(self, x, y):
        i = self.nearest(x, y)
        mode = self.owner.editor_mode.get_selected()
        ox, oy, scale = self.mapping(self.get_width(), self.get_height())
        element = self.owner.editor_element.get_selected_item().get_string()
        order = self.owner.editor_order.get_selected() + 1
        if mode in (0, 4):
            self.selected = i
            self.owner.select_editor_atom(i)
            self.queue_draw()
            return
        if mode == 3 and i is not None:

            def remove(d):
                g = d["graph"]
                g["atoms"].pop(i)
                g["bonds"] = [
                    [a - (a > i), b - (b > i), o]
                    for a, b, o in g["bonds"]
                    if a != i and b != i
                ]
                d["molecule"] = None

            self.selected = None
            self.owner.change("Excluir átomo", remove)
            return
        if mode == 5 and i is not None:

            def replace(d):
                d["graph"]["atoms"][i]["element"] = element
                d["molecule"] = None

            self.owner.change("Trocar elemento", replace)
            return
        if i is not None:
            if mode == 2 and self.selected is not None and self.selected != i:
                a = self.selected
                b = i

                def bond(d):
                    g = d["graph"]
                    g["bonds"] = [v for v in g["bonds"] if set(v[:2]) != {a, b}]
                    g["bonds"].append([a, b, order])
                    d["molecule"] = None

                self.owner.change("Definir ligação", bond)
            self.selected = i
            self.owner.select_editor_atom(i)
            self.queue_draw()
            return
        if mode != 1:
            return
        old = self.selected

        def add(d):
            g = d["graph"]
            index = len(g["atoms"])
            if index >= 200:
                raise ValueError("Limite de 200 átomos no editor.")
            g["atoms"].append(
                {
                    "element": element,
                    "charge": 0,
                    "x": (x - ox) / scale,
                    "y": -(y - oy) / scale,
                }
            )
            if old is not None and old < index:
                g["bonds"].append([old, index, order])
            d["molecule"] = None

        self.owner.change("Adicionar átomo", add)
        self.selected = len(self.owner.project.data["graph"]["atoms"]) - 1
        self.queue_draw()
