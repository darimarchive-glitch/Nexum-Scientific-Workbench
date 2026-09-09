from __future__ import annotations
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw

class HomePage(Gtk.ScrolledWindow):
    def __init__(self,window):
        super().__init__();self.window=window;self.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        clamp=Adw.Clamp();clamp.set_maximum_size(1120);clamp.set_tightening_threshold(800)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=22);root.set_margin_top(44);root.set_margin_bottom(44);root.set_margin_start(24);root.set_margin_end(24)
        hero=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);ey=Gtk.Label(label='NEXUM SCIENTIFIC WORKBENCH',xalign=0);ey.add_css_class('caption-heading');title=Gtk.Label(label='Química computacional, sem atalhos.',xalign=0);title.add_css_class('large-title');sub=Gtk.Label(label='Calcule, modele, visualize estruturas e execute protocolos com modelos explícitos, unidades e limitações documentadas.',xalign=0);sub.add_css_class('dim-label');sub.set_wrap(True);hero.append(ey);hero.append(title);hero.append(sub);root.append(hero)
        actions=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10)
        for name,label,icon in [('calculators','Abrir calculadoras','accessories-calculator-symbolic'),('structures','Estruturas 3D','applications-science-symbolic'),('experiments','Experimentos','media-playback-start-symbolic')]:
            b=Gtk.Button(label=label,icon_name=icon);b.add_css_class('pill');b.connect('clicked',lambda _,n=name:self.window.stack.set_visible_child_name(n));actions.append(b)
        root.append(actions)
        grid=Gtk.Grid(column_spacing=14,row_spacing=14);grid.set_column_homogeneous(True)
        cards=[
            ('35 ferramentas','12 áreas científicas','Entradas livres, desenvolvimento, unidades e gráficos quando a variável depende de uma série.'),
            ('100 testes automáticos','Escopo científico declarado','Benchmarks independentes, identidades de conservação e regressões numéricas; cada ferramenta mostra se é quantitativa, modelo ou formal.'),
            ('3D molecular','PubChem + RCSB','Moléculas pequenas, macromoléculas, fitas, ligantes, profundidade e geração local de conformador quando necessário.'),
            ('Bancadas paramétricas','Estado calculado','Experimentos evoluem a partir das equações; a animação não inventa química.'),
        ]
        for i,(a,b,c) in enumerate(cards):
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);box.add_css_class('home-card');box.set_margin_top(4);box.set_margin_bottom(4);box.set_margin_start(4);box.set_margin_end(4)
            l1=Gtk.Label(label=a,xalign=0);l1.add_css_class('title-2');l2=Gtk.Label(label=b,xalign=0);l2.add_css_class('heading');l3=Gtk.Label(label=c,xalign=0);l3.add_css_class('dim-label');l3.set_wrap(True);box.append(l1);box.append(l2);box.append(l3);grid.attach(box,i%2,i//2,1,1)
        root.append(grid)
        note=Adw.PreferencesGroup(title='Como interpretar os resultados',description='Precisão numérica não é a mesma coisa que validade física fora das hipóteses do modelo.')
        for t,s in [('Quantitativo auditado','Equações e benchmarks automatizados dentro do domínio declarado.'),('Aproximação declarada','Modelo matematicamente coerente, mas com hipóteses como solução ideal, cₚ constante ou atividades≈concentrações.'),('Visualização','Geometria e animações ajudam a interpretar o estado calculado; não são dinâmica molecular ou cálculo eletrônico ab initio.')]:
            r=Adw.ActionRow(title=t,subtitle=s);r.set_subtitle_lines(2);note.add(r)
        root.append(note);clamp.set_child(root);self.set_child(clamp)
