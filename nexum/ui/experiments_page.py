from __future__ import annotations

import math
import time

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from nexum.core.experiments import EXPERIMENTS
from nexum.core.experiment_session import CONFIGS, ExperimentSession, default_config, number
from .experiment_drawing import LaboratoryDrawing


class ExperimentsPage(Gtk.Box):
    """Native laboratory controls, driven by one validated experiment session."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.window = window
        self.exp = EXPERIMENTS[0]
        self.fields = {}
        self.config_rows = []
        self.exp_rows = []
        self.running = False
        self.elapsed = 0.0
        self.last_clock = None
        self.state = None
        self.speed = 1.0
        self.timer_id = 0
        self._ignore_selection = False
        self._loading = False
        self._syncing_timeline = False
        self.session = None
        self.metric_labels = []

        self._build_controls()
        self._build_center()
        self._build_metrics()
        self._select_experiment(0, sync_list=True)
        self.connect("unmap", self._on_unmap)

    # ------------------------------------------------------------------ layout
    def _build_controls(self):
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(244, -1)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)
        sw.set_propagate_natural_height(False)

        self.control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side, value in (("top", 14), ("bottom", 18), ("start", 14), ("end", 14)):
            getattr(self.control_box, f"set_margin_{side}")(value)

        head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        t = Gtk.Label(label="Experimentos", xalign=0)
        t.add_css_class("title-3")
        d = Gtk.Label(label="Escolha uma bancada e edite seus parâmetros.", xalign=0)
        d.add_css_class("dim-label")
        d.set_wrap(True)
        head.append(t)
        head.append(d)
        self.control_box.append(head)
        for label,index in (("Calibração e incerteza",1),("Comparar ordens cinéticas",2),("Titulação poliprótica",3)):
            button=Gtk.Button(label=label)
            button.connect("clicked",lambda _,i=index:self._open_analysis(i))
            self.control_box.append(button)

        self.exp_list = Gtk.ListBox()
        self.exp_list.add_css_class("boxed-list")
        self.exp_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.exp_list.set_activate_on_single_click(True)
        self.exp_list.connect("row-selected", self._experiment_row_selected)
        for i, exp in enumerate(EXPERIMENTS):
            row = Adw.ActionRow(title=exp.title)
            row.set_tooltip_text(exp.subtitle)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            self.exp_list.append(row)
            self.exp_rows.append(row)
        self.control_box.append(self.exp_list)

        self.config_group = Adw.PreferencesGroup(
            title="Parâmetros",
            description="Edite os parâmetros para preparar uma nova simulação.",
        )
        self.control_box.append(self.config_group)

        sw.set_child(self.control_box)
        self.control_sw = sw
        self.append(sw)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

    def _build_center(self):
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        center.set_hexpand(True)
        center.set_vexpand(True)
        center.set_margin_top(14)
        center.set_margin_bottom(14)
        center.set_margin_start(16)
        center.set_margin_end(16)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.title = Gtk.Label(xalign=0)
        self.title.add_css_class("title-2")
        self.subtitle = Gtk.Label(xalign=0)
        self.subtitle.add_css_class("dim-label")
        self.subtitle.set_wrap(True)
        titles.append(self.title)
        titles.append(self.subtitle)
        top.append(titles)
        top.append(Gtk.Box(hexpand=True))
        self.status = Gtk.Label(label="Pronto")
        self.status.add_css_class("status-pill")
        top.append(self.status)
        center.append(top)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.add_css_class("linked")
        self.start = Gtk.Button(label="Iniciar")
        self.start.add_css_class("suggested-action")
        self.start.connect("clicked", self._start)
        self.pause = Gtk.Button(label="Pausar")
        self.pause.connect("clicked", self._pause)
        self.step = Gtk.Button(label="Passo")
        self.step.connect("clicked", self._step)
        self.reset = Gtk.Button(label="Reiniciar")
        self.reset.connect("clicked", self._reset)
        for b in (self.start, self.pause, self.step, self.reset):
            toolbar.append(b)

        self.toolbar = toolbar
        speed = Gtk.DropDown.new_from_strings(["0,25×", "0,5×", "1×", "2×", "5×", "10×"])
        speed.set_selected(2)
        speed.set_tooltip_text("Velocidade de reprodução; não altera o modelo químico")
        speed.connect(
            "notify::selected",
            lambda w, *_: self._set_speed([0.25, 0.5, 1, 2, 5, 10][w.get_selected()]),
        )
        self.speed_control = speed
        toolbar.append(speed)
        self.live_label = Gtk.Label(label="Atualização ao editar os parâmetros")
        self.live_label.add_css_class("dim-label")
        toolbar.append(self.live_label)
        center.append(toolbar)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        center.append(self.progress)
        self.timeline_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.timeline_box.append(Gtk.Label(label="Explorar tempo"))
        self.timeline = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, .1)
        self.timeline.set_draw_value(False)
        self.timeline.set_hexpand(True)
        self.timeline.set_tooltip_text("Arraste para observar qualquer instante; a reprodução fica pausada.")
        self.timeline.connect("value-changed", self._seek)
        self.timeline_box.append(self.timeline)
        self.equivalence = Gtk.Button(label="Ir à equivalência")
        self.equivalence.connect("clicked", self._go_equivalence)
        self.timeline_box.append(self.equivalence)
        center.append(self.timeline_box)
        self.error_label = Gtk.Label(xalign=0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        center.append(self.error_label)

        content = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        content.set_hexpand(True)
        content.set_vexpand(True)
        content.set_resize_start_child(True)
        content.set_resize_end_child(True)
        content.set_shrink_start_child(True)
        content.set_shrink_end_child(True)

        bench_frame = Gtk.Frame()
        self.bench = Gtk.DrawingArea()
        self.bench.set_content_width(320)
        self.bench.set_content_height(260)
        self.bench.set_hexpand(True)
        self.bench.set_vexpand(True)
        self.bench.set_draw_func(self._draw_bench)
        bench_frame.set_child(self.bench)
        content.set_start_child(bench_frame)

        chart_frame = Gtk.Frame()
        self.chart = Gtk.DrawingArea()
        self.chart.set_content_height(190)
        self.chart.set_hexpand(True)
        self.chart.set_vexpand(True)
        self.chart.set_draw_func(self._draw_chart)
        chart_frame.set_child(self.chart)
        content.set_end_child(chart_frame)
        content.set_position(430)
        center.append(content)

        self.append(center)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

    def _build_metrics(self):
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(286, -1)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)
        sw.set_propagate_natural_height(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(14)
        box.set_margin_bottom(18)
        box.set_margin_start(14)
        box.set_margin_end(14)

        self.metrics_group = Adw.PreferencesGroup(title="Medições ao vivo")
        box.append(self.metrics_group)
        self.metric_rows = []

        observation_group = Adw.PreferencesGroup(title="O que observar")
        self.observation = Gtk.Label(xalign=0)
        self.observation.set_wrap(True)
        self.observation.set_selectable(True)
        observation_group.add(self.observation)
        box.append(observation_group)

        self.model_group = Adw.PreferencesGroup(title="Modelo científico")
        self.model_row = Adw.ActionRow()
        self.model_row.set_subtitle_lines(4)
        self.model_group.add(self.model_row)
        box.append(self.model_group)

        self.assumptions = Gtk.Label(xalign=0)
        self.assumptions.set_wrap(True)
        self.assumptions.add_css_class("dim-label")
        box.append(self.assumptions)

        sw.set_child(box)
        self.metrics_sw = sw
        self.append(sw)

        cfg_toggle = Gtk.ToggleButton(icon_name="sidebar-show-symbolic")
        cfg_toggle.set_active(True)
        cfg_toggle.set_tooltip_text("Mostrar/ocultar experimentos e parâmetros")
        cfg_toggle.connect("toggled", lambda b: self.control_sw.set_visible(b.get_active()))
        met_toggle = Gtk.ToggleButton(icon_name="view-list-symbolic")
        met_toggle.set_active(True)
        met_toggle.set_tooltip_text("Mostrar/ocultar medições")
        met_toggle.connect("toggled", lambda b: self.metrics_sw.set_visible(b.get_active()))
        self.toolbar.append(cfg_toggle)
        self.toolbar.append(met_toggle)

    def _experiment_row_selected(self, _listbox, row):
        if self._ignore_selection or row is None:
            return
        self._select_experiment(self.exp_rows.index(row))

    def _select_experiment(self, index, sync_list=False):
        self._pause(set_status=False)
        self._loading = True
        self.exp = EXPERIMENTS[max(0, min(len(EXPERIMENTS)-1, int(index)))]
        if sync_list:
            self._ignore_selection = True
            self.exp_list.select_row(self.exp_rows[index])
            self._ignore_selection = False
        for row in self.config_rows:
            self.config_group.remove(row)
        self.fields, self.config_rows = {}, []
        for key, label, default in CONFIGS[self.exp.id]:
            if isinstance(default, tuple):
                row = Adw.ComboRow(title=label)
                row.set_model(Gtk.StringList.new(list(default)))
                row.connect("notify::selected", self._parameters_changed)
            else:
                row = Adw.EntryRow(title=label)
                row.set_text(default)
                row.connect("notify::text", self._parameters_changed)
            self.fields[key] = row
            self.config_rows.append(row)
            self.config_group.add(row)
        self.title.set_text(self.exp.title)
        self.subtitle.set_text(self.exp.subtitle)
        self.model_row.set_title(self.exp.model_label)
        self.model_row.set_subtitle("O estado da bancada e o ponto no gráfico usam o mesmo cálculo.")
        self.assumptions.set_text("Hipóteses e limites\n• " + "\n• ".join(self.exp.assumptions))
        dynamic = self.exp.kind == "dynamic"
        for widget in (self.start, self.pause, self.step, self.reset, self.speed_control,
                       self.progress, self.timeline_box):
            widget.set_visible(dynamic)
        self.live_label.set_visible(not dynamic)
        self.equivalence.set_visible(self.exp.id == "titration")
        self.step.set_label("+ 0,05 mL" if self.exp.id == "titration" else "Passo")
        self.step.set_tooltip_text("Adicionar 0,05 mL de base" if self.exp.id == "titration" else "Avançar 1% da duração")
        self.config_group.set_description("Alterar um parâmetro reinicia o tempo e o gráfico." if dynamic else
                                          "A bancada e o gráfico atualizam ao editar os campos.")
        self._loading = False
        self._parameters_changed()

    def _read(self):
        data = default_config(self.exp.id)
        weak = "mode" in self.fields and self.fields["mode"].get_selected() == 1
        if "ka" in self.fields:
            self.fields["ka"].set_visible(weak)
        errors = []
        for key, row in self.fields.items():
            row.remove_css_class("error")
            if key == "ka" and not weak:
                continue
            if isinstance(row, Adw.ComboRow):
                if key == "mode":
                    data[key] = "weak-strong" if weak else "strong-strong"
                else:
                    item = row.get_selected_item()
                    data[key] = item.get_string() if item else ""
            else:
                try:
                    value = float(row.get_text().strip().replace(",", "."))
                    if not math.isfinite(value):
                        raise ValueError()
                    data[key] = value
                except ValueError:
                    row.add_css_class("error")
                    errors.append(row.get_title())
        if errors:
            raise ValueError("Informe um número válido em: " + ", ".join(errors))
        return data

    def _parameters_changed(self, *_):
        if self._loading or self.running:
            return
        try:
            # A new parameter set is a new run. Never reuse its predecessor's trace.
            session = ExperimentSession(self.exp.id, self._read())
        except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
            self.session = None
            self.error_label.set_text(str(exc))
            self.error_label.set_visible(True)
            self.status.set_text("Confira os campos")
            self.observation.set_text("Preencha os parâmetros para visualizar o experimento.")
            self._set_metrics([])
            self.progress.set_fraction(0)
            self.progress.set_text("Parâmetros incompletos")
        else:
            self.session = session
            self.error_label.set_visible(False)
            self.status.set_text("Pronto" if session.dynamic else "Atualização ao vivo")
            self._refresh()
        self._sync_controls()
        self.bench.queue_draw()
        self.chart.queue_draw()

    def _sync_controls(self):
        valid = self.session is not None
        self.start.set_sensitive(valid and not self.running)
        self.pause.set_sensitive(valid and self.running)
        self.step.set_sensitive(valid)
        self.reset.set_sensitive(valid)
        self.timeline.set_sensitive(valid)
        at_end = valid and self.session.complete
        self.start.set_label("Repetir" if at_end else "Retomar" if valid and self.session.elapsed > 0 else "Iniciar")
        self.config_group.set_sensitive(not self.running)
        if self.exp.id == "titration" and valid:
            self.equivalence.set_sensitive(self.session.state["equivalence_ml"] <= self.session.config["max_volume_ml"])
            self.equivalence.set_tooltip_text("Observar o volume estequiométrico no gráfico e no frasco" if self.equivalence.get_sensitive() else
                                             "O volume máximo de base não alcança a equivalência")
        else:
            self.equivalence.set_sensitive(False)

    def _set_speed(self, speed):
        # Accumulate time at the old speed before changing it.
        if self.running and self.last_clock is not None and self.session:
            now = time.monotonic()
            self.session.advance((now-self.last_clock)*self.speed)
            self.last_clock = now
        self.speed = speed

    def _start(self, *_):
        if not self.session or not self.session.dynamic or self.running:
            return
        if self.session.complete:
            self.session.seek(0)
        self.running = True
        self.last_clock = time.monotonic()
        self.status.set_text("Executando")
        if not self.timer_id:
            self.timer_id = GLib.timeout_add(33, self._tick)
        self._refresh()

    def _pause(self, *_, set_status=True):
        self.running = False
        self.last_clock = None
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = 0
        if hasattr(self, "config_group"):
            self.config_group.set_sensitive(True)
        if hasattr(self, "session") and self.session:
            if set_status:
                self.status.set_text("Concluído" if self.session.complete else
                                     "Pausado" if self.session.elapsed > 0 else "Pronto")
            self._sync_controls()
            self.bench.queue_draw()

    def _on_unmap(self, *_):
        self._pause()

    def _reset(self, *_):
        self._pause(set_status=False)
        if self.session:
            self.session.seek(0)
            self.status.set_text("Pronto")
            self._refresh()

    def _step(self, *_):
        self._pause(set_status=False)
        if self.session and self.session.dynamic:
            self.session.step()
            self.status.set_text("Concluído" if self.session.complete else "Passo manual")
            self._refresh()

    def _seek(self, slider):
        if self._syncing_timeline or not self.session:
            return
        self._pause(set_status=False)
        self.session.seek(slider.get_value()/100*self.session.duration)
        self.status.set_text("Concluído" if self.session.complete else "Explorando")
        self._refresh()

    def _go_equivalence(self, *_):
        if self.session and self.exp.id == "titration":
            self._pause(set_status=False)
            self.session.seek(self.session.state["equivalence_ml"]/self.session.config["flow_ml_s"])
            self.status.set_text("Na equivalência")
            self._refresh()

    def _tick(self):
        if not self.running or self.session is None:
            self.timer_id = 0
            return False
        now = time.monotonic()
        seconds = max(0., now-(self.last_clock if self.last_clock is not None else now))
        self.last_clock = now
        try:
            self.session.advance(seconds*self.speed)
            if self.session.complete:
                self.running = False
                self.last_clock = None
                self.timer_id = 0
                self.status.set_text("Concluído")
            self._refresh()
        except (ValueError, ArithmeticError, RuntimeError) as exc:
            self.running = False
            self.timer_id = 0
            self.last_clock = None
            self.status.set_text("Interrompido")
            self.error_label.set_text(str(exc))
            self.error_label.set_visible(True)
            self._sync_controls()
            return False
        return self.running

    def _refresh(self):
        session = self.session
        if session is None:
            return
        self.state = session.state
        self.elapsed = session.elapsed
        self._set_metrics(session.metrics)
        self.observation.set_text(session.guide)
        self.bench.set_tooltip_text(session.guide)
        self.chart.set_tooltip_text(session.xlabel+" · "+session.ylabel)
        if session.dynamic:
            fraction = min(1., session.elapsed/session.duration)
            self.progress.set_fraction(fraction)
            self.progress.set_text(number(session.elapsed)+" / "+number(session.duration)+" s")
            self._syncing_timeline = True
            self.timeline.set_value(fraction*100)
            self._syncing_timeline = False
        self._sync_controls()
        self.bench.queue_draw()
        self.chart.queue_draw()

    def _set_metrics(self, metrics):
        titles = [title for title, _ in metrics]
        if titles != [row.get_title() for row in self.metric_rows]:
            for row in self.metric_rows:
                self.metrics_group.remove(row)
            self.metric_rows, self.metric_labels = [], []
            for title, _ in metrics:
                row = Adw.ActionRow(title=title)
                label = Gtk.Label()
                label.add_css_class("numeric")
                label.set_selectable(True)
                row.add_suffix(label)
                self.metrics_group.add(row)
                self.metric_rows.append(row)
                self.metric_labels.append(label)
        for label, (_, value) in zip(self.metric_labels, metrics):
            label.set_text(value)

    def _draw_bench(self, _area, cr, width, height):
        LaboratoryDrawing(cr, Adw.StyleManager.get_default().get_dark()).bench(width, height, self.session, self.running)

    def _draw_chart(self, _area, cr, width, height):
        LaboratoryDrawing(cr, Adw.StyleManager.get_default().get_dark()).chart(width, height, self.session)


    def _open_analysis(self,index):
        self._pause()
        self.window.analysis.mode.set_selected(index)
        self.window.stack.set_visible_child_name("analysis")
