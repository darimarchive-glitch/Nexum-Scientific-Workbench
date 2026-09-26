"""Integrated laboratory UI; calculations run outside the GTK main loop."""

from pathlib import Path
from dataclasses import asdict
import base64
import copy
import csv
import json
import tempfile
import uuid
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
from nexum.paths import data_dir
from nexum.lab.project import Project, read_project, write_project, fingerprint, now
from nexum.core.data_analysis import json_safe
from nexum.lab import (
    datasets,
    workflows,
    statistics,
    molecules,
    processes,
    investigations,
    reports,
    examples,
    extensions,
    reasoning,
)
from nexum.core.molecular_analysis import molecule_from_dict
from .lab_widgets import (
    label,
    page,
    entry,
    dropdown,
    buttons,
    textview,
    text,
    settext,
    number,
    GraphCanvas,
)
from .file_actions import choose, background
from .plot_widget import ScientificPlot


class Laboratory(Adw.Window):
    def __init__(self, main):
        super().__init__(
            transient_for=main,
            title="Nexum · Laboratório",
            default_width=1200,
            default_height=850,
        )
        self.main = main
        self.project = Project()
        self.path = None
        self.loading = True
        self.busy = False
        self.recovery = data_dir() / "recovery"
        self.recovery.mkdir(parents=True, exist_ok=True)
        self.notes_pending = False
        self.saved_revision = -1
        self.extension_info = None
        self.reference = None
        self.overlay = Adw.ToastOverlay()
        view = Adw.ToolbarView()
        self.overlay.set_child(view)
        self.set_content(self.overlay)
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="LABORATÓRIO · NEXUM 7"))
        for name, fn in [
            ("Abrir", self.open_project),
            ("Salvar", self.save_project),
            ("Desfazer", self.undo),
            ("Refazer", self.redo),
        ]:
            b = Gtk.Button(label=name)
            b.connect("clicked", lambda _, f=fn: self.guard(f))
            header.pack_end(b)
        view.add_top_bar(header)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        side = Gtk.StackSidebar()
        side.set_stack(self.stack)
        side.set_size_request(190, -1)
        body.append(side)
        body.append(self.stack)
        view.set_content(body)
        self.status = Gtk.Label(label="")
        self.status.set_wrap(True)
        view.add_bottom_bar(self.status)
        self.selectors = []
        self.project_page()
        self.data_page()
        self.builder_page()
        self.spectrum_page()
        self.workflow_page()
        self.design_page()
        self.quality_page()
        self.reasoning_page()
        self.process_page()
        self.investigation_page()
        self.scenes_page()
        self.extensions_page()
        self.loading = False
        self.refresh()
        self.timer = GLib.timeout_add_seconds(20, self.autosave)
        self.connect("close-request", self.close)

    def toast(self, message, timeout=5):
        t = Adw.Toast.new(str(message))
        t.set_timeout(timeout)
        self.overlay.add_toast(t)
        return False

    def guard(self, fn):
        try:
            if self.busy:
                raise ValueError("Aguarde o cálculo em andamento.")
            self.flush_notes()
            return fn()
        except Exception as exc:
            self.toast(str(exc), 8)

    def change(self, title, fn):
        self.flush_notes()
        self.project.edit(title, fn)
        self.refresh()

    def work(self, fn, done):
        self.flush_notes()
        if self.busy:
            raise ValueError("Aguarde o cálculo em andamento.")
        self.busy = True
        self.status.set_text("Calculando…")
        project_id = self.project.data["id"]
        revision = self.project.revision

        def worker():
            try:
                return True, fn()
            except Exception as exc:
                return False, str(exc)

        def finish(result):
            self.busy = False
            if (
                self.project.data["id"] != project_id
                or self.project.revision != revision
            ):
                self.toast("O projeto mudou; o resultado antigo foi descartado.")
                self.refresh()
                return
            if result[0]:
                self.guard(lambda: done(result[1]))
            else:
                self.toast(result[1], 8)
            self.refresh()

        background(self, worker, finish)

    def addpage(self, key, title, description):
        scroll, box = page(title, description)
        self.stack.add_titled(scroll, key, title)
        return box

    def dataset_selector(self, box, title="Série"):
        w = dropdown(box, title, ["Nenhuma série"])
        self.selectors.append(w)
        return w

    def dataset(self, selector=None):
        ds = self.project.data["datasets"]
        i = (selector or self.data_select).get_selected()
        if not ds or i >= len(ds):
            raise ValueError("Importe ou carregue uma série primeiro.")
        return ds[i]

    def result(self, kind, payload, source_ids=(), parameters=None):
        self.project.result(kind, payload, source_ids, parameters)
        self.refresh()

    def refresh(self):
        self.flush_notes()
        self.loading = True
        d = self.project.data
        self.project_title.set_text(d["title"])
        settext(self.notes, d["notes"])
        names = [s["name"] for s in d["datasets"]] or ["Nenhuma série"]
        for selector in self.selectors:
            old = selector.get_selected()
            selector.set_model(Gtk.StringList.new(names))
            selector.set_selected(min(old, len(names) - 1))
        self.canvas.queue_draw()
        self.flow_list.get_buffer().set_text(
            "\n".join(
                f"{i + 1}. {workflows.OPERATIONS[s['op']]} — {s.get('parameters', {})}"
                for i, s in enumerate(d["pipeline"])
            )
            or "Adicione as etapas na ordem de execução."
        )
        settext(
            self.process_list,
            "\n".join(
                f"{n['id']}: {processes.KINDS[n['kind']]} ← {', '.join(n.get('inputs', [])) or 'alimentação externa'}"
                for n in d["process"]
            ),
        )
        self.scene_select.set_model(
            Gtk.StringList.new([s["title"] for s in d["scenes"]] or ["Nenhuma cena"])
        )
        settext(
            self.assignment_list,
            "\n".join(
                f"{i + 1}. {a['range']} → átomos {', '.join(str(j + 1) for j in a['atom_indices'])}: {a['note']}"
                for i, a in enumerate(d["assignments"])
            )
            or "Nenhuma atribuição manual.",
        )
        settext(
            self.project_summary,
            f"{len(d['datasets'])} séries · {len(d['results'])} resultados · {len(d['scenes'])} cenas\n\n"
            + "\n".join(f"{r['at']} — {r['kind']}" for r in d["results"][-20:]),
        )
        self.status.set_text(
            f"{d['title']} · revisão {self.project.revision} · recuperação automática a cada 20 s após alterações"
        )
        self.loading = False
        self.preview_data()
        self.preview_spectrum()
        if self.project.data.get("molecule") is None:
            self.builder_info.set_text(
                "Desenho ainda sem geometria 3D atualizada. Gere ou associe uma estrutura antes de atribuir regiões espectrais."
            )
        self.refresh_design()
        self.refresh_case()
        self.process_diagram.queue_draw()

    def project_page(self):
        box = self.addpage(
            "project",
            "Projeto e caderno",
            "Organize dados originais, anotações, moléculas, análises e cenas em um arquivo .nexum7. O salvamento usa substituição atômica e verificação SHA-256.",
        )
        self.project_title = entry(box, "Título", "Novo projeto")
        self.notes = textview(box, 180)
        self.project_title.connect("changed", self.notes_changed)
        self.notes.get_buffer().connect("changed", self.notes_changed)
        buttons(
            box,
            self,
            [
                ("Registrar título e anotações", self.save_notes),
                ("Novo projeto", self.new_project),
                ("Recuperar última cópia", self.recover),
                ("Exportar relatório HTML", self.export_report),
            ],
        )
        self.example_select = dropdown(
            box, "Projetos didáticos — dados simulados", examples.NAMES
        )
        buttons(box, self, [("Abrir exemplo", self.load_example)])
        self.project_summary = textview(box, 160, False)
        box.append(
            label(
                "O relatório HTML é independente do aplicativo, inclui figuras SVG e pode ser impresso em PDF pelo navegador. Revise a interpretação antes de compartilhar."
            )
        )

    def notes_changed(self, *_):
        if not self.loading:
            self.notes_pending = True

    def flush_notes(self):
        if not self.notes_pending:
            return
        title = self.project_title.get_text().strip() or "Novo projeto"
        notes = text(self.notes)
        self.project.edit(
            "Atualizar caderno", lambda d: d.update(title=title, notes=notes)
        )
        self.notes_pending = False

    def save_notes(self):
        title = self.project_title.get_text().strip()
        notes = text(self.notes)
        if not title:
            raise ValueError("Dê um título ao projeto.")
        self.change("Atualizar caderno", lambda d: d.update(title=title, notes=notes))
        self.notes_pending = False

    def new_project(self):
        self.autosave(force=True)
        self.project = Project()
        self.conformer_results = []
        self.conformer_select.set_model(Gtk.StringList.new(["Nenhuma"]))
        self.path = None
        self.canvas.selected = None
        self.reference = None
        self.saved_revision = -1
        self.refresh()

    def load_example(self):
        self.autosave(force=True)
        self.project = Project(examples.example(self.example_select.get_selected()))
        self.conformer_results = []
        self.conformer_select.set_model(Gtk.StringList.new(["Nenhuma"]))
        self.path = None
        self.canvas.selected = None
        self.reference = None
        self.saved_revision = -1
        self.refresh()

    def autosave(self, force=False):
        if self.busy:
            return True
        self.flush_notes()
        if force or self.saved_revision != self.project.revision:
            try:
                write_project(
                    self.recovery / (self.project.data["id"] + ".nexum7"),
                    self.project.data,
                )
                self.saved_revision = self.project.revision
            except Exception as exc:
                self.toast("Falha na recuperação automática: " + str(exc), 8)
        return True

    def close(self, *_):
        if self.busy:
            self.toast("Aguarde a operação antes de fechar.")
            return True
        self.autosave(force=True)
        self.set_visible(False)
        return True

    def undo(self):
        self.project.undo()
        self.canvas.selected = None
        self.refresh()

    def redo(self):
        self.project.redo()
        self.canvas.selected = None
        self.refresh()

    def recover(self):
        paths = sorted(
            self.recovery.glob("*.nexum7"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidates = [p for p in paths if p.stem != self.project.data["id"]]
        if not candidates:
            raise ValueError("Nenhuma cópia anterior de outro projeto encontrada.")
        self.replace_project(candidates[0])
        self.toast("Recuperado: " + self.project.data["title"])

    def replace_project(self, path):
        data = read_project(path)
        if data.get("workspace"):
            from .session_actions import validate, restore, snapshot

            validate(data["workspace"])
            before = snapshot(self.main)
            try:
                restore(self.main, data["workspace"])
            except Exception:
                restore(self.main, before)
                raise
        self.autosave(force=True)
        self.project = Project(data)
        self.conformer_results = []
        self.conformer_select.set_model(Gtk.StringList.new(["Nenhuma"]))
        self.path = Path(path)
        self.canvas.selected = None
        self.reference = None
        self.saved_revision = -1
        self.refresh()

    def open_project(self):
        choose(self, "Abrir projeto Nexum 7", self.replace_project)

    def save_project(self):
        self.save_notes()
        from .session_actions import snapshot

        self.change(
            "Registrar estado do aplicativo",
            lambda d: d.update(
                workspace=json.loads(
                    json.dumps(snapshot(self.main), default=json_safe, allow_nan=False)
                )
            ),
        )

        def save(path):
            write_project(path, self.project.data)
            self.path = path
            self.toast("Projeto salvo com dados originais e estado do aplicativo.")

        if self.path and self.path.parent != self.recovery:
            save(self.path)
        else:
            choose(self, "Salvar projeto", save, True, "projeto.nexum7")

    def export_report(self):
        self.save_notes()
        choose(
            self,
            "Exportar relatório",
            lambda p: reports.report(self.project.data, p),
            True,
            "relatorio-nexum.html",
        )

    def data_page(self):
        box = self.addpage(
            "data",
            "Dados e importação",
            "Importe CSV/TSV numéricos e JCAMP XYPOINTS não comprimido. Colunas, separadores, unidades e origem ficam registrados. Não descartamos linhas inválidas silenciosamente.",
        )
        self.import_header = Gtk.CheckButton(
            label="Primeira linha contém nomes de colunas"
        )
        self.import_header.set_active(True)
        box.append(self.import_header)
        self.import_separator = dropdown(
            box, "Separador", ["Automático", "Ponto e vírgula", "Vírgula", "Tabulação"]
        )
        self.import_decimal = dropdown(
            box, "Decimal", ["Automático", "Vírgula", "Ponto"]
        )
        self.xcol = entry(box, "Coluna X (a partir de 1)", "1")
        self.ycol = entry(box, "Coluna Y (a partir de 1)", "2")
        self.xunit = entry(box, "Unidade X", "", "Ex.: s, mL, cm⁻¹")
        self.yunit = entry(box, "Unidade Y", "", "Ex.: Abs, pH, mg/L")
        buttons(
            box,
            self,
            [
                ("Importar arquivo", self.import_one),
                ("Importar lote", self.import_batch),
                ("Trazer dados de Análise", self.from_analysis),
            ],
        )
        self.data_select = self.dataset_selector(box)
        self.data_select.connect("notify::selected", lambda *_: self.preview_data())
        self.analysis_target = dropdown(
            box,
            "Método de destino na aba Análise",
            [
                "Espectro e integração",
                "Calibração linear",
                "Comparação de ordens cinéticas",
            ],
        )
        buttons(
            box,
            self,
            [
                ("Enviar para Análise", self.to_analysis),
                (
                    "Exportar CSV",
                    lambda: choose(
                        self,
                        "Exportar série",
                        lambda p: datasets.export_csv(self.dataset(), p),
                        True,
                        "dados.csv",
                    ),
                ),
            ],
        )
        self.data_plot = ScientificPlot()
        box.append(self.data_plot)
        self.data_info = label("")
        box.append(self.data_info)

    def read_dataset(self, path):
        raw = Path(path).read_bytes()
        if len(raw) > 12_000_000:
            raise ValueError("Arquivo excede 12 MB.")
        content = raw.decode("utf-8-sig")
        if Path(path).suffix.lower() in (".jdx", ".dx"):
            return datasets.import_jcamp(content, Path(path).stem, raw)
        parsed = datasets.table(
            content,
            ["auto", ";", ",", "\t"][self.import_separator.get_selected()],
            ["auto", ",", "."][self.import_decimal.get_selected()],
            self.import_header.get_active(),
        )
        return datasets.from_table(
            parsed,
            int(self.xcol.get_text()) - 1,
            int(self.ycol.get_text()) - 1,
            Path(path).stem,
            raw,
            self.xunit.get_text(),
            self.yunit.get_text(),
        )

    def import_one(self):
        choose(
            self, "Importar dados", lambda p: self.add_datasets([self.read_dataset(p)])
        )

    def import_batch(self):
        dialog = Gtk.FileChooserNative.new(
            "Importar lote com o mesmo formato",
            self,
            Gtk.FileChooserAction.OPEN,
            "Importar",
            "Cancelar",
        )
        dialog.set_select_multiple(True)

        def received(d, response):
            try:
                if response == Gtk.ResponseType.ACCEPT:
                    model = d.get_files()
                    paths = [
                        model.get_item(i).get_path() for i in range(model.get_n_items())
                    ]
                    if len(paths) > 32:
                        raise ValueError("Importe no máximo 32 arquivos por lote.")
                    self.guard(
                        lambda: self.add_datasets([self.read_dataset(p) for p in paths])
                    )
            finally:
                d.destroy()

        dialog.connect("response", received)
        dialog.show()

    def add_datasets(self, items):
        self.change(
            f"Importar {len(items)} séries", lambda d: d["datasets"].extend(items)
        )

    def from_analysis(self):
        ds = self.main.analysis.dataset
        if not ds:
            raise ValueError("Nenhum dado na aba Análise.")
        d = copy.deepcopy(ds)
        d.update(
            id=uuid.uuid4().hex,
            name=d.get("name", "Dados de Análise"),
            xunit=d.get("xunit", ""),
            yunit=d.get("yunit", ""),
            origin=d.get("origin", "Não informada"),
            source={"imported_from": "Aba Análise"},
        )
        d["x"] = list(map(float, d["x"]))
        d["y"] = list(map(float, d["y"]))
        self.add_datasets([d])

    def to_analysis(self):
        d = copy.deepcopy(self.dataset())
        self.main.analysis.mode.set_selected(self.analysis_target.get_selected())
        case = self.project.data.get("investigation")
        if case and case["dataset"]["id"] == d["id"] and case["kind"] == "calibration":
            self.main.analysis.fields["sample"].set_text(
                str(case["known"]["unknown_signal"])
            )
        for key in ("name", "xunit", "yunit"):
            self.main.analysis.fields[key].set_text(d.get(key, ""))
        self.main.analysis.dataset = d
        self.main.analysis.baseline.set_active(False)
        self.main.analysis.fields["lower"].set_text("")
        self.main.analysis.fields["upper"].set_text("")
        self.main.analysis.status.set_text(
            d.get("origin", "") + " · série do laboratório"
        )
        self.main.analysis.analyze()
        self.main.stack.set_visible_child_name("analysis")
        self.main.present()

    def preview_data(self):
        if self.loading:
            return
        try:
            d = self.dataset()
            self.data_plot.set_plot(
                {
                    "title": d["name"],
                    "xlabel": d.get("xunit", ""),
                    "ylabel": d.get("yunit", ""),
                    "series": [
                        {"name": d["name"], "points": list(zip(d["x"], d["y"]))}
                    ],
                }
            )
            self.data_info.set_text(
                f"{len(d['x'])} pontos · {d.get('origin', 'Não informada')}\nHash original: {d.get('source', {}).get('sha256', 'não importado')}"
            )
        except (ValueError, IndexError):
            self.data_plot.set_plot(None)
            self.data_info.set_text("Nenhuma série selecionada.")

    def builder_page(self):
        box = self.addpage(
            "builder",
            "Editor molecular",
            "Desenhe átomos e ligações, valide valências e gere geometria 3D com RDKit. MMFF94/UFF são campos de força; as energias não são resultados quânticos.",
        )
        self.smiles = entry(box, "SMILES", "CCO")
        buttons(
            box,
            self,
            [
                ("Carregar SMILES", self.load_smiles),
                ("Etanol", lambda: self.load_smiles("CCO")),
                ("Benzeno", lambda: self.load_smiles("c1ccccc1")),
                ("Cafeína", lambda: self.load_smiles("Cn1c(=O)c2c(ncn2C)n(C)c1=O")),
            ],
        )
        self.editor_mode = dropdown(
            box,
            "Ação",
            [
                "Selecionar",
                "Adicionar e ligar",
                "Definir ligação",
                "Excluir átomo",
                "Mover átomo",
                "Trocar elemento",
            ],
        )
        self.editor_mode.set_selected(1)
        self.editor_element = dropdown(
            box,
            "Elemento",
            [
                "C",
                "O",
                "N",
                "H",
                "S",
                "P",
                "F",
                "Cl",
                "Br",
                "I",
                "Na",
                "K",
                "Mg",
                "Ca",
                "Fe",
                "Zn",
            ],
        )
        self.editor_order = dropdown(
            box, "Ordem da ligação", ["Simples", "Dupla", "Tripla"]
        )
        self.canvas = GraphCanvas(self)
        box.append(self.canvas)
        self.formal_charge = entry(box, "Carga formal do átomo selecionado", "0")
        buttons(
            box,
            self,
            [
                ("Aplicar carga", self.charge_atom),
                ("Organizar desenho", self.organize_graph),
                (
                    "Limpar desenho",
                    lambda: self.change(
                        "Limpar desenho",
                        lambda d: d.update(
                            graph={"atoms": [], "bonds": []}, molecule=None
                        ),
                    ),
                ),
                ("Gerar e abrir em 3D", self.build_molecule),
                ("Usar estrutura 3D atual", self.use_current),
            ],
        )
        self.builder_info = label(
            "Clique em um átomo para selecioná-lo. Alterações no desenho exigem gerar novamente a geometria."
        )
        box.append(self.builder_info)
        self.conformer_count = entry(box, "Número de conformeros (1–20)", "6")
        self.conformer_select = dropdown(box, "Geometrias geradas", ["Nenhuma"])
        self.conformer_results = []
        buttons(
            box,
            self,
            [
                ("Gerar conformeros", self.make_conformers),
                ("Mostrar conformero", self.show_conformer),
                ("Fixar referência para RMSD", self.pin_reference),
            ],
        )
        self.mapping = entry(
            box,
            "Pares referência:atual (opcional, índices a partir de 1)",
            "",
            "Ex.: 1:1, 2:2, 3:3",
        )
        buttons(
            box,
            self,
            [
                ("Alinhar e calcular RMSD", self.align_molecules),
                ("Comparar lado a lado", lambda: self.main.struct.analysis.compare()),
            ],
        )

    def load_smiles(self, value=None):
        smiles = value if isinstance(value, str) else self.smiles.get_text()
        self.work(
            lambda: molecules.chemistry("smiles_graph", smiles),
            lambda graph: self.set_graph(graph),
        )

    def set_graph(self, graph):
        self.canvas.selected = None
        self.change(
            "Carregar desenho molecular", lambda d: d.update(graph=graph, molecule=None)
        )
        self.builder_info.set_text(
            "Desenho carregado. Gere a geometria 3D para aplicar as alterações."
        )

    def charge_atom(self):
        i = self.canvas.selected
        charge = int(self.formal_charge.get_text())
        if i is None or i >= len(self.project.data["graph"]["atoms"]):
            raise ValueError("Selecione um átomo.")
        if not -4 <= charge <= 4:
            raise ValueError("Carga formal entre −4 e +4 neste editor.")

        def change(d):
            d["graph"]["atoms"][i]["charge"] = charge
            d["molecule"] = None

        self.change("Alterar carga formal", change)

    def organize_graph(self):
        graph = copy.deepcopy(self.project.data["graph"])
        self.work(
            lambda: molecules.chemistry("builder", graph),
            lambda r: self.accept_molecule(r["molecule"], r["graph"]),
        )

    def build_molecule(self):
        graph = copy.deepcopy(self.project.data["graph"])
        self.work(
            lambda: molecules.chemistry("builder", graph),
            lambda r: self.accept_molecule(r["molecule"], r["graph"]),
        )

    def accept_molecule(self, molecule, graph=None):
        def change(d):
            d["molecule"] = molecule
            if graph is not None:
                d["graph"] = graph

        self.change("Atualizar estrutura 3D", change)
        self.main.struct._apply_molecule(molecule_from_dict(molecule))
        self.main.stack.set_visible_child_name("structures")
        self.main.present()
        meta = molecule.get("metadata", {})
        self.builder_info.set_text(
            f"{meta.get('formula', molecule.get('name', ''))} · {meta.get('geometry_method', 'Geometria importada')}\nEnergia: {meta.get('energy_kcal_mol', 'não calculada')} kcal/mol · convergência: {meta.get('optimization_converged', 'não avaliada')}"
        )

    def use_current(self):
        molecule = self.main.struct.viewer.molecule
        if not molecule:
            raise ValueError("Carregue uma estrutura em Estruturas 3D.")
        raw = asdict(molecule)
        graph = raw.get("metadata", {}).get("builder_graph")
        self.change(
            "Associar estrutura atual",
            lambda d: d.update(molecule=raw, **({"graph": graph} if graph else {})),
        )
        self.builder_info.set_text(
            "Estrutura associada para atribuições e comparação. Para editar uma estrutura sem desenho, carregue seu SMILES."
        )

    def select_editor_atom(self, index):
        if index is None:
            return
        if index < len(self.project.data["graph"]["atoms"]):
            self.formal_charge.set_text(
                str(self.project.data["graph"]["atoms"][index].get("charge", 0))
            )
        self.atom_ids.set_text(str(index + 1))
        m = self.project.data.get("molecule")
        v = self.main.struct.viewer
        if m and v.molecule and fingerprint(asdict(v.molecule)) == fingerprint(m):
            v.selection = {index}
            v.rebuild_scene()
            v.queue_render()
        matches = [
            i + 1
            for i, a in enumerate(self.project.data["assignments"])
            if m
            and a["molecule_sha256"] == fingerprint(m)
            and index in a["atom_indices"]
        ]
        if matches:
            self.builder_info.set_text(
                "Atribuições deste átomo: " + ", ".join(map(str, matches))
            )

    def make_conformers(self):
        graph = copy.deepcopy(self.project.data["graph"])
        count = int(self.conformer_count.get_text())

        def done(result):
            self.conformer_results = result
            self.conformer_select.set_model(
                Gtk.StringList.new(
                    [
                        f"{i + 1} · ΔE {r['relative_energy_kcal_mol']:.4g} kcal/mol"
                        for i, r in enumerate(result)
                    ]
                )
            )
            self.result(
                "Conformeros",
                {
                    "geometries": result,
                    "method": "ETKDGv3 e minimização MMFF94/UFF; energias relativas do mesmo sistema.",
                },
            )
            self.show_conformer()

        self.work(lambda: molecules.chemistry("conformers", graph, count), done)

    def show_conformer(self):
        i = self.conformer_select.get_selected()
        if i >= len(self.conformer_results):
            raise ValueError("Gere conformeros primeiro.")
        m = self.conformer_results[i]["molecule"]
        self.accept_molecule(m, m.get("metadata", {}).get("builder_graph"))

    def pin_reference(self):
        m = self.project.data.get("molecule")
        if not m:
            raise ValueError("Gere ou associe uma estrutura primeiro.")
        self.reference = copy.deepcopy(m)
        self.main.struct._apply_molecule(molecule_from_dict(m))
        self.main.struct.analysis.pin()
        self.toast("Referência fixada para alinhamento e comparação.")

    def align_molecules(self):
        if not self.reference or not self.project.data.get("molecule"):
            raise ValueError("Fixe a referência e gere ou associe a segunda estrutura.")
        pairs = None
        raw = self.mapping.get_text().strip()
        if raw:
            pairs = [
                tuple(int(n.strip()) - 1 for n in pair.split(":"))
                for pair in raw.split(",")
            ]
        reference = copy.deepcopy(self.reference)
        moving = copy.deepcopy(self.project.data["molecule"])

        def done(r):
            self.result("Alinhamento molecular", r)
            self.accept_molecule(r["molecule"])
            self.builder_info.set_text(
                f"RMSD = {r['rmsd_angstrom']:.6g} Å · {len(r['pairs'])} correspondências. Alinhamento rígido sem reflexão."
            )

        self.work(lambda: molecules.align(reference, moving, pairs), done)

    def spectrum_page(self):
        box = self.addpage(
            "spectrum",
            "Espectro e molécula",
            "Vincule regiões de dados a átomos da estrutura. Atribuições são manuais e permanecem ligadas à versão exata da molécula; não equivalem a uma identificação automática.",
        )
        self.spectrum_select = self.dataset_selector(box)
        self.spectrum_select.connect(
            "notify::selected", lambda *_: self.preview_spectrum()
        )
        self.spectrum_plot = ScientificPlot()
        self.spectrum_plot.on_point = self.spectrum_clicked
        box.append(self.spectrum_plot)
        self.peak_lower = entry(box, "Início da região", "0")
        self.peak_upper = entry(box, "Fim da região", "1")
        self.atom_ids = entry(
            box, "Átomos (índices a partir de 1, separados por vírgula)", "1"
        )
        self.assignment_note = entry(
            box,
            "Interpretação da atribuição",
            "",
            "Ex.: região associada ao grupo carbonila",
        )
        buttons(
            box,
            self,
            [
                ("Usar estrutura 3D atual", self.use_current),
                ("Registrar atribuição", self.add_assignment),
            ],
        )
        self.assignment_list = textview(box, 170, False)
        self.assignment_number = entry(box, "Número da atribuição para destacar", "1")
        buttons(
            box,
            self,
            [("Destacar na molécula e no espectro", self.highlight_assignment)],
        )

    def preview_spectrum(self):
        if self.loading:
            return
        try:
            d = self.dataset(self.spectrum_select)
            marks = [
                {"x": sum(a["range"]) / 2, "label": str(i + 1)}
                for i, a in enumerate(self.project.data["assignments"])
                if a["dataset_id"] == d["id"]
            ]
            self.spectrum_plot.set_plot(
                {
                    "title": d["name"],
                    "xlabel": d.get("xunit", ""),
                    "ylabel": d.get("yunit", ""),
                    "series": [
                        {"name": d["name"], "points": list(zip(d["x"], d["y"]))}
                    ],
                    "markers": marks,
                }
            )
        except (ValueError, IndexError):
            self.spectrum_plot.set_plot(None)

    def spectrum_clicked(self, x, y):
        d = self.dataset(self.spectrum_select)
        width = (d["x"][-1] - d["x"][0]) * 0.015
        self.peak_lower.set_text(f"{max(d['x'][0], x - width):.8g}")
        self.peak_upper.set_text(f"{min(d['x'][-1], x + width):.8g}")

    def add_assignment(self):
        m = self.project.data.get("molecule")
        if not m:
            raise ValueError("Gere ou associe a molécula primeiro.")
        ids = [int(v.strip()) - 1 for v in self.atom_ids.get_text().split(",")]
        a = molecules.assign(
            self.dataset(self.spectrum_select),
            m,
            number(self.peak_lower),
            number(self.peak_upper),
            ids,
            self.assignment_note.get_text(),
        )
        self.change(
            "Atribuição manual de espectro", lambda d: d["assignments"].append(a)
        )

    def highlight_assignment(self):
        index = int(self.assignment_number.get_text()) - 1
        if not 0 <= index < len(self.project.data["assignments"]):
            raise ValueError("Atribuição inexistente.")
        a = self.project.data["assignments"][index]
        m = self.project.data.get("molecule")
        if not m or fingerprint(m) != a["molecule_sha256"]:
            raise ValueError(
                "A estrutura mudou; esta atribuição pertence a outra versão."
            )
        ids = [d["id"] for d in self.project.data["datasets"]]
        self.spectrum_select.set_selected(ids.index(a["dataset_id"]))
        self.peak_lower.set_text(str(a["range"][0]))
        self.peak_upper.set_text(str(a["range"][1]))
        self.atom_ids.set_text(", ".join(str(i + 1) for i in a["atom_indices"]))
        self.main.struct._apply_molecule(molecule_from_dict(m))
        v = self.main.struct.viewer
        v.selection = set(a["atom_indices"])
        v.rebuild_scene()
        v.queue_render()
        self.main.stack.set_visible_child_name("structures")
        self.main.present()

    def workflow_page(self):
        box = self.addpage(
            "flow",
            "Fluxos de análise",
            "Monte uma sequência de etapas. Os dados originais ficam preservados e cada transformação registra método, parâmetros e hashes de entrada e saída.",
        )
        self.flow_select = self.dataset_selector(box)
        self.flow_op = dropdown(box, "Etapa", list(workflows.OPERATIONS.values()))
        self.flow_window = entry(box, "Suavização: janela ímpar / grau", "7 / 2")
        self.flow_bounds = entry(box, "Integração: início / fim", "0 / 1")
        self.flow_coeff = entry(box, "Calibração: inclinação / intercepto", "1 / 0")
        self.flow_unit = entry(box, "Unidade após calibração", "mg/L")
        buttons(
            box,
            self,
            [
                ("Adicionar etapa", self.add_step),
                (
                    "Remover última etapa",
                    lambda: self.change(
                        "Remover etapa",
                        lambda d: d["pipeline"].pop() if d["pipeline"] else None,
                    ),
                ),
                ("Executar na série", self.run_flow),
                ("Executar em todas as séries", lambda: self.run_flow(True)),
                ("Salvar fluxo", self.save_flow),
                ("Abrir fluxo", self.open_flow),
            ],
        )
        self.flow_position = entry(box, "Etapa a mover (número)", "1")
        buttons(
            box,
            self,
            [
                ("Mover para cima", lambda: self.move_step(-1)),
                ("Mover para baixo", lambda: self.move_step(1)),
            ],
        )
        self.flow_list = textview(box, 140, False)
        self.flow_plot = ScientificPlot()
        box.append(self.flow_plot)
        self.flow_info = label("")
        box.append(self.flow_info)

    def add_step(self):
        op = list(workflows.OPERATIONS)[self.flow_op.get_selected()]
        p = {}
        if op == "smooth":
            a, b = map(int, self.flow_window.get_text().split("/"))
            p = {"window": a, "degree": b}
        elif op == "integrate":
            a, b = (
                float(v.strip().replace(",", "."))
                for v in self.flow_bounds.get_text().split("/")
            )
            p = {"lower": a, "upper": b}
        elif op == "calibrate":
            a, b = (
                float(v.strip().replace(",", "."))
                for v in self.flow_coeff.get_text().split("/")
            )
            p = {"slope": a, "intercept": b, "unit": self.flow_unit.get_text()}
        self.change(
            "Adicionar etapa de análise",
            lambda d: d["pipeline"].append({"op": op, "parameters": p}),
        )

    def run_flow(self, batch=False):
        steps = copy.deepcopy(self.project.data["pipeline"])
        if not steps:
            raise ValueError("Adicione ao menos uma etapa.")
        sources = copy.deepcopy(
            self.project.data["datasets"] if batch else [self.dataset(self.flow_select)]
        )
        if not sources:
            raise ValueError("Importe dados primeiro.")

        def done(results):
            def change(d):
                for src, r in zip(sources, results):
                    out = {
                        "id": uuid.uuid4().hex,
                        "name": src["name"] + " · processado",
                        "x": r["x"],
                        "y": r["y"],
                        "xunit": src.get("xunit", ""),
                        "yunit": r["yunit"],
                        "origin": "Processado no Nexum",
                        "source": {
                            "parent_id": src["id"],
                            "sha256_input": r["source_sha256"],
                            "trace": r["trace"],
                        },
                    }
                    d["datasets"].append(out)
                    d["results"].append(
                        {
                            "id": uuid.uuid4().hex,
                            "kind": "Fluxo de análise",
                            "at": now(),
                            "sources": [src["id"]],
                            "parameters": {"steps": steps},
                            "payload": r,
                        }
                    )

            self.change("Executar fluxo de análise", change)
            r = results[-1]
            self.flow_plot.set_plot(
                {
                    "title": "Última série processada",
                    "series": [
                        {"name": "Resultado", "points": list(zip(r["x"], r["y"]))}
                    ],
                }
            )
            self.flow_info.set_text(
                f"{len(results)} séries processadas. Métricas da última: {r['metrics']}. Resultados disponíveis em Dados e no relatório."
            )

        self.work(lambda: [workflows.execute(s, steps) for s in sources], done)

    def save_flow(self):
        choose(
            self,
            "Salvar sequência",
            lambda p: p.write_text(
                json.dumps(
                    {"schema": 1, "steps": self.project.data["pipeline"]},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            ),
            True,
            "fluxo.nexumflow",
        )

    def open_flow(self):
        def read(path):
            if path.stat().st_size > 100000:
                raise ValueError("Fluxo muito grande.")
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema") != 1:
                raise ValueError("Formato de fluxo inválido.")
            self.change("Carregar fluxo", lambda d: d.update(pipeline=data["steps"]))

        choose(self, "Abrir sequência", read)

    def design_page(self):
        box = self.addpage(
            "design",
            "Planejamento experimental",
            "Fatorial completo 2^k, até cinco fatores, com réplicas, pontos centrais e ordem aleatorizada. Ajuste efeitos principais e interações de dois fatores; pontos centrais não permitem estimar termos quadráticos separados.",
        )
        box.append(
            label(
                "Fatores: uma linha por fator, nome; mínimo; máximo. Use ponto ou vírgula decimal."
            )
        )
        self.factors = textview(box, 100)
        settext(self.factors, "Temperatura; 20; 60\npH; 4; 8")
        self.replicates = entry(box, "Réplicas", "2")
        self.centers = entry(box, "Pontos centrais", "3")
        self.design_seed = entry(box, "Semente da ordem aleatória", "42")
        buttons(
            box,
            self,
            [
                ("Gerar planejamento", self.generate_design),
                ("Ajustar respostas", self.fit_design),
                ("Exportar tabela CSV", self.export_design),
            ],
        )
        box.append(
            label(
                "Preencha somente a última coluna (resposta), preservando a ordem dos ensaios."
            )
        )
        self.design_table = textview(box, 220)
        self.design_info = textview(box, 150, False)
        self.design_plot = ScientificPlot()
        box.append(self.design_plot)
        self.last_design_hash = None

    def generate_design(self):
        factors = []
        for line in text(self.factors).splitlines():
            if not line.strip():
                continue
            name, low, high = [v.strip() for v in line.split(";")]
            factors.append(
                {
                    "name": name,
                    "low": float(low.replace(",", ".")),
                    "high": float(high.replace(",", ".")),
                }
            )
        design = statistics.factorial(
            factors,
            int(self.replicates.get_text()),
            int(self.centers.get_text()),
            int(self.design_seed.get_text()),
        )
        self.change("Gerar planejamento fatorial", lambda d: d.update(design=design))

    def refresh_design(self):
        design = self.project.data["design"]
        key = fingerprint(design)
        if key == self.last_design_hash:
            return
        self.last_design_hash = key
        if not design:
            settext(self.design_table, "")
            return
        rows = [
            "ensaio;" + ";".join(f["name"] for f in design["factors"]) + ";resposta"
        ]
        rows.extend(
            f"{i + 1};"
            + ";".join(str(v) for v in r["values"])
            + ";"
            + ("" if r["response"] is None else str(r["response"]))
            for i, r in enumerate(design["runs"])
        )
        settext(self.design_table, "\n".join(rows))

    def design_responses(self):
        design = self.project.data["design"]
        if not design:
            raise ValueError("Gere um planejamento primeiro.")
        rows = list(csv.reader(text(self.design_table).splitlines(), delimiter=";"))[1:]
        if len(rows) != len(design["runs"]):
            raise ValueError("Não remova nem acrescente ensaios na tabela.")
        responses = []
        for i, (row, run) in enumerate(zip(rows, design["runs"])):
            if (
                len(row) != len(run["values"]) + 2
                or int(row[0]) != i + 1
                or [float(v.replace(",", ".")) for v in row[1:-1]] != run["values"]
            ):
                raise ValueError(
                    "A ordem ou os fatores foram alterados. Gere novamente o planejamento."
                )
            responses.append(float(row[-1].replace(",", ".")))
        return responses

    def fit_design(self):
        responses = self.design_responses()
        design = copy.deepcopy(self.project.data["design"])
        r = statistics.fit_design(design, responses)

        def change(d):
            for row, value in zip(d["design"]["runs"], responses):
                row["response"] = value

        self.change("Registrar respostas experimentais", change)
        self.result("Planejamento experimental", r, parameters=design)
        settext(
            self.design_info,
            "\n".join(
                f"{c['term']}: {c['value']:.6g} · IC95% {c['ci95']}"
                for c in r["coefficients"]
            )
            + f"\nR²: {r['r2']} · RMSE: {r['rmse']:.6g}\n"
            + r["method"],
        )
        self.design_plot.set_plot(
            {
                "title": "Resíduos do ajuste",
                "xlabel": "Ensaio",
                "ylabel": "Resíduo",
                "series": [
                    {
                        "name": "Resíduos",
                        "points": list(enumerate(r["residuals"], 1)),
                        "scatter": True,
                    }
                ],
            }
        )

    def export_design(self):
        choose(
            self,
            "Exportar planejamento",
            lambda p: p.write_text(text(self.design_table), encoding="utf-8-sig"),
            True,
            "planejamento.csv",
        )

    def quality_page(self):
        box = self.addpage(
            "quality",
            "Controle de qualidade",
            "Avalie precisão, viés e resultados individuais contra alvo e desvio de referência. Controle estatístico e especificação são critérios distintos; os limites devem ser definidos para o método.",
        )
        self.qc_select = self.dataset_selector(box)
        self.qc_target = entry(box, "Valor alvo", "100")
        self.qc_sigma = entry(box, "Desvio padrão de referência (σ)", "1")
        self.qc_lower = entry(box, "Especificação inferior (opcional)")
        self.qc_upper = entry(box, "Especificação superior (opcional)")
        buttons(box, self, [("Avaliar série Y", self.run_quality)])
        self.qc_plot = ScientificPlot()
        box.append(self.qc_plot)
        self.qc_info = textview(box, 140, False)
        self.recovery_values = entry(
            box,
            "Recuperação: original / fortificada / quantidade adicionada",
            "10 / 14.8 / 5",
        )
        buttons(box, self, [("Calcular recuperação", self.run_recovery)])

    def run_quality(self):
        d = self.dataset(self.qc_select)
        target = number(self.qc_target)
        sigma = number(self.qc_sigma)
        lower = number(self.qc_lower) if self.qc_lower.get_text().strip() else None
        upper = number(self.qc_upper) if self.qc_upper.get_text().strip() else None
        r = statistics.quality(d["y"], target, sigma, lower, upper)
        self.result(
            "Controle de qualidade", r, [d["id"]], {"target": target, "sigma": sigma}
        )
        series = [{"name": "Resultados", "points": list(enumerate(r["values"], 1))}]
        for name, value in [
            ("Alvo", target),
            ("Controle inferior", target - 3 * sigma),
            ("Controle superior", target + 3 * sigma),
            ("Especificação inferior", lower),
            ("Especificação superior", upper),
        ]:
            if value is not None:
                series.append(
                    {"name": name, "points": [(1, value), (len(r["values"]), value)]}
                )
        self.qc_plot.set_plot(
            {
                "title": "Carta de resultados individuais",
                "xlabel": "Resultado",
                "ylabel": d.get("yunit", ""),
                "series": series,
            }
        )
        settext(
            self.qc_info,
            f"Média: {r['mean']:.6g} · s: {r['sd']:.6g} · RSD: {r['rsd_percent']}% · viés: {r['bias']:.6g}\nFora do controle: {r['outside_control']}\nFora da especificação: {r['outside_specification']}\n"
            + r["method"],
        )

    def run_recovery(self):
        values = [
            float(v.strip().replace(",", "."))
            for v in self.recovery_values.get_text().split("/")
        ]
        r = statistics.recovery(*values)
        self.result(
            "Recuperação",
            {
                "percent": r,
                "values": values,
                "method": "100 × (fortificada − original) / adicionada; mesma unidade e base de diluição.",
            },
        )
        self.toast(f"Recuperação: {r:.4g}%")

    def process_page(self):
        box = self.addpage(
            "process",
            "Processos industriais",
            "Construa um fluxograma em regime estacionário. Unidades fixas: kg/h, °C e cp em kJ/(kg·K). Inclui mistura adiabática, divisão, aquecimento e conversão mássica 1:1. Sem reciclos ou equilíbrio de fases.",
        )
        self.process_kind = dropdown(box, "Operação", list(processes.KINDS.values()))
        self.process_id = entry(box, "Nome único da operação", "F1")
        self.process_inputs = entry(
            box,
            "Saídas anteriores de entrada (separadas por vírgula)",
            "",
            "Ex.: F1, F2. O divisor gera também nome:rest",
        )
        self.process_flow = entry(box, "Alimentação: vazão kg/h", "100")
        self.process_composition = entry(box, "Alimentação: frações mássicas", "água=1")
        self.process_temp = entry(box, "Alimentação/aquecedor: temperatura °C", "25")
        self.process_cp = entry(box, "Alimentação: cp kJ/(kg·K)", "4.18")
        self.process_fraction = entry(box, "Divisor/conversão: fração (0–1)", "0.5")
        self.process_reaction = entry(
            box, "Conversão mássica: reagente / produto", "A / B"
        )
        buttons(
            box,
            self,
            [
                ("Adicionar operação", self.add_process),
                (
                    "Remover última",
                    lambda: self.change(
                        "Remover operação",
                        lambda d: d["process"].pop() if d["process"] else None,
                    ),
                ),
                ("Calcular balanços", self.run_process),
                (
                    "Exportar fluxograma SVG",
                    lambda: choose(
                        self,
                        "Exportar fluxograma",
                        lambda p: p.write_text(
                            reports.process_svg(self.project.data["process"]),
                            encoding="utf-8",
                        ),
                        True,
                        "fluxograma.svg",
                    ),
                ),
            ],
        )
        self.process_list = textview(box, 160, False)
        self.process_info = textview(box, 200, False)
        self.process_diagram = Gtk.DrawingArea()
        self.process_diagram.set_content_height(300)
        self.process_diagram.set_draw_func(self.draw_process)
        box.append(self.process_diagram)

    def add_process(self):
        kind = list(processes.KINDS)[self.process_kind.get_selected()]
        name = self.process_id.get_text().strip()
        inputs = [
            v.strip() for v in self.process_inputs.get_text().split(",") if v.strip()
        ]
        p = {}
        if kind == "feed":
            composition = {}
            for pair in self.process_composition.get_text().split(";"):
                component, value = pair.split("=")
                composition[component.strip()] = float(value.strip().replace(",", "."))
            p = {
                "flow": number(self.process_flow),
                "temperature": number(self.process_temp),
                "cp": number(self.process_cp),
                "composition": composition,
            }
        elif kind == "heater":
            p = {"temperature": number(self.process_temp)}
        elif kind == "split":
            p = {"fraction": number(self.process_fraction)}
        elif kind == "convert":
            a, b = [v.strip() for v in self.process_reaction.get_text().split("/")]
            p = {
                "reactant": a,
                "product": b,
                "conversion": number(self.process_fraction),
            }
        node = {"id": name, "kind": kind, "inputs": inputs, "parameters": p}
        nodes = copy.deepcopy(self.project.data["process"]) + [node]
        processes.simulate(nodes)
        self.change("Adicionar operação de processo", lambda d: d.update(process=nodes))
        self.process_diagram.queue_draw()

    def run_process(self):
        nodes = copy.deepcopy(self.project.data["process"])
        r = processes.simulate(nodes)
        self.result("Balanço de processo", r, parameters={"nodes": nodes})
        settext(
            self.process_info,
            "\n".join(
                f"{name}: {s['flow_kg_h']:.5g} kg/h · {s['temperature_c']:.5g} °C · frações {s['fractions']}"
                for name, s in r["streams"].items()
            )
            + "\n\n"
            + "\n".join(
                f"{b['id']}: entrada {b['input_kg_h']:.5g}, saída {b['output_kg_h']:.5g} kg/h; Q={b['heat_kj_h']:.5g} kJ/h"
                for b in r["balances"]
            )
            + "\n\n"
            + r["method"],
        )
        self.process_diagram.queue_draw()

    def draw_process(self, area, cr, w, h):
        nodes = self.project.data["process"]
        height = max(300, len(nodes) * 65 + 20)
        if area.get_content_height() != height:
            area.set_content_height(height)
        dark = Adw.StyleManager.get_default().get_dark()
        cr.set_source_rgb(*((0.12, 0.15, 0.18) if dark else (0.97, 0.98, 1)))
        cr.paint()
        positions = {n["id"]: i for i, n in enumerate(nodes)}
        for i, node in enumerate(nodes):
            y = 15 + i * 65
            for source in node.get("inputs", []):
                parent = positions.get(source.split(":")[0])
                if parent is not None:
                    xx = 20 + 12 * (parent % 6)
                    cr.set_source_rgb(0.2, 0.6, 0.65)
                    cr.set_line_width(2)
                    cr.move_to(100, 45 + parent * 65)
                    cr.line_to(xx, 45 + parent * 65)
                    cr.line_to(xx, y + 20)
                    cr.line_to(100, y + 20)
                    cr.stroke()
            cr.set_source_rgb(0.12, 0.38, 0.5)
            cr.rectangle(100, y, max(160, w - 120), 45)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.set_font_size(13)
            cr.move_to(110, y + 27)
            cr.show_text(node["id"] + " · " + processes.KINDS[node["kind"]])

    def investigation_page(self):
        box = self.addpage(
            "case",
            "Investigações didáticas",
            "Problemas com dados simulados, ruído controlado e reprodução por semente. O gabarito fica no arquivo do projeto; este recurso é formativo e não é uma prova protegida.",
        )
        self.case_kind = dropdown(
            box, "Cenário", list(investigations.SCENARIOS.values())
        )
        self.case_seed = entry(box, "Semente", "42")
        self.case_noise = entry(box, "Desvio do ruído na unidade Y (0–0,1)", "0.01")
        buttons(box, self, [("Criar investigação", self.create_case)])
        self.case_question = label("")
        box.append(self.case_question)
        self.case_estimate = entry(box, "Sua estimativa", "0")
        box.append(label("Justificativa e limitações do método"))
        self.case_reason = textview(box, 120)
        buttons(
            box,
            self,
            [
                ("Registrar tentativa", self.submit_case),
                ("Revelar valor simulado", self.reveal_case),
            ],
        )
        self.case_feedback = textview(box, 140, False)

    def create_case(self):
        case = investigations.create(
            list(investigations.SCENARIOS)[self.case_kind.get_selected()],
            int(self.case_seed.get_text()),
            number(self.case_noise),
        )

        def change(d):
            d["investigation"] = case
            d["datasets"].append(case["dataset"])

        self.change("Criar investigação simulada", change)

    def refresh_case(self):
        c = self.project.data["investigation"]
        self.case_question.set_text(
            c["question"]
            + "\nDados fornecidos: "
            + str(c["known"])
            + "\nResposta na unidade: "
            + c["unit"]
            if c
            else "Crie uma investigação ou abra um exemplo."
        )
        if c:
            settext(
                self.case_feedback,
                "\n".join(
                    f"Estimativa: {a['estimate']:.6g} · erro relativo {a['relative_error_percent']:.3g}%\n{a['reasoning']}\n{a['feedback']}"
                    for a in c["attempts"]
                )
                + (
                    f"\nValor usado na simulação: {c['answer']:.8g} {c['unit']}"
                    if c["revealed"]
                    else ""
                ),
            )
        else:
            settext(self.case_feedback, "")

    def submit_case(self):
        case = self.project.data["investigation"]
        if not case:
            raise ValueError("Crie uma investigação primeiro.")
        result = investigations.submit(
            case, number(self.case_estimate), text(self.case_reason)
        )
        self.change(
            "Registrar tentativa didática",
            lambda d: d["investigation"]["attempts"].append(result),
        )

    def reveal_case(self):
        if not self.project.data["investigation"]:
            raise ValueError("Crie uma investigação primeiro.")
        self.change(
            "Revelar gabarito simulado",
            lambda d: d["investigation"].update(revealed=True),
        )

    def scenes_page(self):
        box = self.addpage(
            "scenes",
            "Cenas e apresentação",
            "Salve a orientação, representação e legenda da estrutura. Exporte imagens ou uma apresentação HTML que abre sem o Nexum. As superfícies e os controles avançados continuam disponíveis em Estruturas 3D.",
        )
        self.scene_title = entry(box, "Título da cena", "Estrutura molecular")
        self.scene_caption = entry(box, "Legenda e interpretação")
        self.scene_scale = entry(box, "Escala da imagem (1–3)", "2")
        buttons(
            box,
            self,
            [
                ("Abrir visualizador", self.show_viewer),
                ("Capturar cena", self.capture_scene),
                ("Exportar PNG", self.export_scene_png),
                ("Exportar rotação GIF", self.export_rotation),
                ("Exportar apresentação HTML", self.export_presentation),
            ],
        )
        self.scene_select = dropdown(box, "Cenas", ["Nenhuma cena"])
        buttons(
            box,
            self,
            [
                ("Restaurar cena", self.restore_scene),
                ("Excluir cena", self.delete_scene),
            ],
        )
        self.visual_preset = dropdown(
            box,
            "Aparência",
            ["Padrão", "Volume atômico em destaque", "Bastões e fundo escuro"],
        )
        buttons(box, self, [("Aplicar aparência", self.apply_visual_preset)])
        box.append(
            label(
                "Raios de van der Waals representam um modelo de volume atômico. Superfícies e cores de cargas parciais não são densidade eletrônica quântica. Para campos calculados externamente, importe um arquivo Cube no visualizador."
            )
        )

    def show_viewer(self):
        self.main.stack.set_visible_child_name("structures")
        self.main.present()

    def capture_scene(self):
        v = self.main.struct.viewer
        if not v.molecule:
            raise ValueError("Carregue uma estrutura primeiro.")
        scale = int(self.scene_scale.get_text())
        if not 1 <= scale <= 3:
            raise ValueError("Escala entre 1 e 3.")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scene.png"
            v.export_png(path, scale=scale)
            raw = path.read_bytes()
        if len(raw) > 6_000_000:
            raise ValueError("Imagem excede 6 MB; reduza a escala.")
        scene = {
            "title": self.scene_title.get_text().strip() or "Cena",
            "caption": self.scene_caption.get_text(),
            "state": json.loads(
                json.dumps(
                    self.main.struct.analysis.snapshot(),
                    default=json_safe,
                    allow_nan=False,
                )
            ),
            "png_base64": base64.b64encode(raw).decode(),
        }
        self.change("Capturar cena molecular", lambda d: d["scenes"].append(scene))

    def selected_scene(self):
        i = self.scene_select.get_selected()
        if i >= len(self.project.data["scenes"]):
            raise ValueError("Capture uma cena primeiro.")
        return i, self.project.data["scenes"][i]

    def restore_scene(self):
        from .molecular_tools import MolecularTools

        _, s = self.selected_scene()
        state = s["state"]
        self.main.struct._apply_molecule(molecule_from_dict(state["molecule"]))
        MolecularTools.restore_view(self.main.struct.viewer, state)
        self.show_viewer()

    def delete_scene(self):
        i, _ = self.selected_scene()
        self.change("Excluir cena", lambda d: d["scenes"].pop(i))

    def export_scene_png(self):
        scale = int(self.scene_scale.get_text())
        if not 1 <= scale <= 3:
            raise ValueError("Escala entre 1 e 3.")
        choose(
            self,
            "Exportar imagem",
            lambda p: self.main.struct.viewer.export_png(p, scale=scale),
            True,
            "estrutura.png",
        )

    def export_presentation(self):
        if not self.project.data["scenes"]:
            raise ValueError("Capture pelo menos uma cena.")
        choose(
            self,
            "Exportar apresentação",
            lambda p: reports.presentation(self.project.data, p),
            True,
            "apresentacao-nexum.html",
        )

    def apply_visual_preset(self):
        v = self.main.struct.viewer
        i = self.visual_preset.get_selected()
        v.show_influence = i == 1
        v.influence_opacity = 0.38 if i == 1 else 0.22
        if i == 2:
            v.set_dark(True)
            v.representation = "sticks"
        else:
            v.set_dark(Adw.StyleManager.get_default().get_dark())
            v.representation = "ball-stick"
        v.rebuild_scene()
        v.queue_render()
        self.show_viewer()

    def extensions_page(self):
        import sys

        box = self.addpage(
            "extensions",
            "Extensões Python",
            "Execute uma função run(payload) em um Python separado, com dados da série selecionada. Use somente código de confiança: o processo separado não impede acesso aos arquivos do computador.",
        )
        self.extension_select = self.dataset_selector(box)
        self.extension_python = entry(
            box,
            "Interpretador Python externo",
            sys.executable if not getattr(sys, "frozen", False) else "",
        )
        buttons(
            box,
            self,
            [
                ("Selecionar extensão .py", self.pick_extension),
                ("Salvar extensão de exemplo", self.save_extension_example),
            ],
        )
        self.extension_source = textview(box, 220, False)
        self.extension_trust = Gtk.CheckButton(
            label="Revisei este código e autorizo sua execução local"
        )
        box.append(self.extension_trust)
        buttons(box, self, [("Executar extensão", self.run_extension)])
        self.extension_output = textview(box, 160, False)

    def pick_extension(self):
        def picked(p):
            self.extension_info = extensions.inspect(p)
            self.extension_trust.set_active(False)
            settext(self.extension_source, self.extension_info["source"])

        choose(self, "Selecionar extensão Python", picked)

    def save_extension_example(self):
        source = '''"""Exemplo Nexum: estatística descritiva, sem dependências externas."""\nimport statistics\ndef run(payload):\n    values=payload["dataset"]["y"]\n    return {"n":len(values),"media":statistics.mean(values),"mediana":statistics.median(values),"metodo":"Estatística descritiva da série Y"}\n'''
        choose(
            self,
            "Salvar exemplo",
            lambda p: p.write_text(source, encoding="utf-8"),
            True,
            "estatistica_nexum.py",
        )

    def run_extension(self):
        if not self.extension_info or not self.extension_trust.get_active():
            raise ValueError(
                "Selecione, revise e autorize a extensão antes de executar."
            )
        info = copy.deepcopy(self.extension_info)
        dataset = copy.deepcopy(self.dataset(self.extension_select))
        python = self.extension_python.get_text().strip() or None

        def done(r):
            self.result("Extensão Python", r, [dataset["id"]])
            settext(self.extension_output, json.dumps(r, ensure_ascii=False, indent=2))

        self.work(
            lambda: extensions.run(
                info["path"], {"schema": 1, "dataset": dataset}, info["sha256"], python
            ),
            done,
        )

    def move_step(self, delta):
        i = int(self.flow_position.get_text()) - 1
        j = i + delta
        steps = self.project.data["pipeline"]
        if not 0 <= i < len(steps) or not 0 <= j < len(steps):
            raise ValueError("Etapa fora da sequência.")

        def change(d):
            d["pipeline"][i], d["pipeline"][j] = d["pipeline"][j], d["pipeline"][i]

        self.change("Reordenar fluxo de análise", change)
        self.flow_position.set_text(str(j + 1))

    def export_rotation(self):
        if not self.main.struct.viewer.molecule:
            raise ValueError("Carregue uma molécula primeiro.")
        choose(
            self,
            "Exportar rotação da estrutura",
            self.capture_rotation,
            True,
            "rotacao-nexum.gif",
        )

    def capture_rotation(self, path):
        from PIL import Image

        if self.busy:
            raise ValueError("Aguarde a operação em andamento.")
        self.busy = True
        self.show_viewer()
        v = self.main.struct.viewer
        angle = v.rot_y
        frames = []
        temp = tempfile.TemporaryDirectory(prefix="nexum-rotation-")
        index = 0

        def finish(error=None):
            v.rot_y = angle
            v.queue_render()
            temp.cleanup()
            self.busy = False
            self.refresh()
            self.toast(
                str(error)
                if error
                else "Animação GIF salva: rotação da câmera, sem dinâmica molecular.",
                8,
            )

        def frame():
            nonlocal index
            try:
                v.rot_y = angle + index * 10
                v.queue_render()
                p = Path(temp.name) / "frame.png"
                v.export_png(p, scale=1)
                with Image.open(p) as im:
                    im = im.convert("RGB")
                    im.thumbnail((960, 720))
                    frames.append(im.quantize(colors=128))
                index += 1
                self.status.set_text(f"Capturando rotação: {index}/36 quadros")
                if index < 36:
                    return True
                frames[0].save(
                    path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=90,
                    loop=0,
                    disposal=2,
                )
                finish()
                return False
            except Exception as exc:
                finish(exc)
                return False

        GLib.timeout_add(80, frame)

    def reasoning_page(self):
        box = self.addpage(
            "reasoning",
            "Modelos e incerteza",
            "Investigue quais entradas dominam a incerteza. Cada modelo declara suas unidades e hipóteses; mais casas decimais não tornam a medição mais precisa.",
        )
        self.reason_model = dropdown(
            box, "Modelo", list(reasoning.MODELS[k]["name"] for k in reasoning.MODELS)
        )
        self.reason_entries = []
        self.reason_errors = []
        self.reason_labels = []
        for i in range(3):
            caption = label("")
            box.append(caption)
            self.reason_labels.append(caption)
            self.reason_entries.append(entry(box, "Valor", "1"))
            self.reason_errors.append(
                entry(box, "Incerteza padrão u (mesma unidade)", "0.01")
            )
        self.reason_correlations = entry(
            box, "Correlações ρ₁₂ / ρ₁₃ / ρ₂₃", "0 / 0 / 0"
        )
        self.reason_seed = entry(box, "Semente Monte Carlo (20.000 amostras)", "42")
        self.reason_assumptions = label("")
        box.append(self.reason_assumptions)
        self.reason_model.connect("notify::selected", self.change_reason_model)
        self.change_reason_model()
        buttons(box, self, [("Propagar e comparar métodos", self.run_uncertainty)])
        self.reason_info = textview(box, 180, False)
        self.reason_plot = ScientificPlot()
        box.append(self.reason_plot)
        box.append(label("Distribuição de espécies de um ácido monoprótico", True))
        self.speciation_pka = entry(box, "pKa", "4.76")
        self.speciation_range = entry(box, "Faixa de pH: mínimo / máximo", "0 / 14")
        buttons(box, self, [("Explorar frações HA e A⁻", self.run_speciation)])
        self.speciation_plot = ScientificPlot()
        box.append(self.speciation_plot)
        box.append(
            label(
                "No pH=pKa, as duas formas têm a mesma fração no modelo ideal. O gráfico mostra a distribuição em um pH fornecido; não calcula sozinho o pH de uma solução real."
            )
        )

    def change_reason_model(self, *_):
        model = reasoning.MODELS[
            list(reasoning.MODELS)[self.reason_model.get_selected()]
        ]
        for i, (name, unit, value) in enumerate(model["inputs"]):
            self.reason_labels[i].set_text(f"{name} — {unit}")
            self.reason_entries[i].set_text(str(value))
            self.reason_errors[i].set_text(str(value * 0.01))
        self.reason_assumptions.set_text(model["assumptions"])

    def run_uncertainty(self):
        key = list(reasoning.MODELS)[self.reason_model.get_selected()]
        means = [number(e) for e in self.reason_entries]
        errors = [number(e) for e in self.reason_errors]
        a, b, c = [
            float(v.strip().replace(",", "."))
            for v in self.reason_correlations.get_text().split("/")
        ]
        corr = [[1, a, b], [a, 1, c], [b, c, 1]]
        seed = int(self.reason_seed.get_text())

        def done(r):
            self.result("Propagação de incerteza", r, parameters=r["parameters"])
            mc = r["monte_carlo"]
            settext(
                self.reason_info,
                f"Resultado nominal: {r['nominal']:.8g} {r['unit']}\nu combinado: {r['standard_uncertainty']:.3g}; U (k=2): {r['expanded_k2']:.3g}\nMonte Carlo: média {mc['mean']:.8g}, s {mc['sd']:.3g}; intervalo central de 95%: {mc['interval_95_percent']}\n\n"
                + r["assumptions"]
                + "\n"
                + r["method"],
            )
            self.reason_plot.set_plot(
                {
                    "title": "Efeito linear de aumentar cada entrada em uma incerteza padrão",
                    "xlabel": "Entrada 1, 2 ou 3",
                    "ylabel": r["unit"],
                    "series": [
                        {
                            "name": "∂f/∂x × u(x)",
                            "points": list(enumerate(r["effects_of_one_u"], 1)),
                            "scatter": True,
                        }
                    ],
                }
            )

        self.work(
            lambda: reasoning.uncertainty(key, means, errors, corr, 20000, seed), done
        )

    def run_speciation(self):
        lo, hi = [
            float(v.strip().replace(",", "."))
            for v in self.speciation_range.get_text().split("/")
        ]
        r = reasoning.speciation(number(self.speciation_pka), lo, hi)
        self.result(
            "Distribuição ácido–base ideal",
            r,
            parameters={"pka": r["pka"], "ph_min": lo, "ph_max": hi},
        )
        self.speciation_plot.set_plot(
            {
                "title": "Distribuição de espécies — modelo ideal",
                "xlabel": "pH",
                "ylabel": "Fração da concentração total",
                "series": [
                    {"name": "HA", "points": list(zip(r["ph"], r["acid_fraction"]))},
                    {"name": "A⁻", "points": list(zip(r["ph"], r["base_fraction"]))},
                ],
                "markers": [{"x": r["pka"], "label": "pKa"}],
            }
        )
