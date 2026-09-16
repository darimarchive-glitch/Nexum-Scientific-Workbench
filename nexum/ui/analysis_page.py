"""Reproducible analysis of original data, simulations, fits and residuals."""
import copy,csv
import numpy as np
from gi.repository import Gtk,Adw,GLib
from nexum.core import data_analysis as core
from nexum.catalog import ANALYSES
from nexum import chemistry_worker
from .file_actions import choose,background
from .plot_widget import ScientificPlot

class AnalysisPage(Gtk.Box):
    def __init__(self,window):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        self.window=window;self.dataset=None;self.references=[];self.last_plot=None;self.timer=0;self.generation=0;self.fields={}
        controls=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        for side in ('top','bottom','start','end'):getattr(controls,'set_margin_'+side)(12)
        sw=Gtk.ScrolledWindow();sw.set_size_request(310,-1);sw.set_child(controls);self.append(sw)
        self.mode=Gtk.DropDown.new_from_strings(list(ANALYSES));controls.append(self.mode);self.mode.connect('notify::selected',self.change_mode)
        group=Adw.PreferencesGroup(title='Dados e parâmetros');controls.append(group)
        specs=[('name','Amostra / cenário','Amostra 1'),('xunit','Unidade de x','cm⁻¹'),('yunit','Unidade de y','Absorbância'),('prominence','Proeminência mínima dos picos','0.05'),('lower','Integrar de (vazio = início)',''),('upper','Integrar até (vazio = fim)',''),('sample','Sinal da amostra desconhecida','0.5'),('slope','Inclinação simulada','100'),('intercept','Intercepto simulado','0'),('c0','[A]₀ (mol/L)','1'),('k','k (unidade depende da ordem)','0.1'),('order','Ordem simulada: 0, 1 ou 2','1'),('duration','Duração (s)','50'),('noise','Ruído: desvio padrão em y','0.005'),('seed','Semente aleatória','42'),('pkas','pKa crescentes separados por ;','2.15;7.20;12.35'),('acid_c','Ácido (mol/L)','0.1'),('acid_ml','Volume ácido (mL)','25'),('base_c','Base (mol/L)','0.1'),('max_ml','Volume máximo base (mL)','100'),('formula','Fórmula da espécie iônica','C2H6O'),('charge','Carga inteira, sem adicionar adutos','1')]
        for key,title,value in specs:
            row=Adw.EntryRow(title=title);row.set_text(value);group.add(row);self.fields[key]=row
        self.baseline=Gtk.CheckButton(label='Subtrair base linear entre extremos');controls.append(self.baseline)
        for title,fn in [('Importar CSV experimental',self.import_csv),('Gerar dados simulados',self.simulate),('Analisar / calcular',self.analyze),('Guardar curva para comparação',self.pin),('Limpar comparações',self.clear_references),('Exportar dados originais CSV',self.export_csv),('Exportar gráfico SVG',lambda:self.export_plot('svg')),('Exportar gráfico PDF',lambda:self.export_plot('pdf')),('Reproduzir / pausar curva',self.play),('Avançar um ponto',self.step)]:
            button=Gtk.Button(label=title)
            def clicked(*_,action=fn):
                try:action()
                except Exception as exc:self.window.toast(str(exc),8)
            button.connect('clicked',clicked);controls.append(button)
        controls.append(Gtk.Label(label='Observações',xalign=0));self.notes=Gtk.TextView();self.notes.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);self.notes.set_size_request(-1,100);controls.append(self.notes)
        results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);results.set_margin_top(12);results.set_margin_end(12)
        scroll=Gtk.ScrolledWindow();scroll.set_hexpand(True);scroll.set_child(results);self.append(scroll)
        self.status=Gtk.Label(xalign=0);self.status.set_wrap(True);results.append(self.status)
        self.plot=ScientificPlot();self.secondary=ScientificPlot();self.tertiary=ScientificPlot()
        for chart in (self.plot,self.secondary,self.tertiary):results.append(chart)
        self.report=Gtk.Label(xalign=0);self.report.set_wrap(True);self.report.set_selectable(True);results.append(self.report)
        self.connect('unmap',lambda *_:self.pause());self.change_mode()
    def val(self,key,default=None):
        raw=self.fields[key].get_text().strip()
        if not raw and default is not None:return default
        value=float(raw.replace(',','.'))
        if not np.isfinite(value):raise ValueError('Valor não finito em '+key)
        return value
    def change_mode(self,*_):
        self.pause();self.generation+=1;mode=self.mode.get_selected();common={'name','xunit','yunit'}
        specific=[{'prominence','lower','upper'},{'sample','slope','intercept','noise','seed'},{'c0','k','order','duration','noise','seed'},{'pkas','acid_c','acid_ml','base_c','max_ml'},{'formula','charge'}][mode]
        for key,row in self.fields.items():row.set_visible(key in common|specific)
        self.baseline.set_visible(mode==0)
        xunit,yunit=[('cm⁻¹','Absorbância'),('mol/L','Absorbância'),('s','mol/L'),('mL','pH'),('m/z','Intensidade relativa (%)')][mode]
        self.fields['xunit'].set_text(xunit);self.fields['yunit'].set_text(yunit);self.dataset=None;self.last_plot=None
        for chart in (self.plot,self.secondary,self.tertiary):chart.set_plot(None)
        self.report.set_text('');self.status.set_text(ANALYSES[mode]+' — importe dados ou gere uma simulação.')
    def set_data(self,x,y,origin,method):
        x,y=core.xy_data(x,y);self.generation+=1
        self.dataset={'x':x.tolist(),'y':y.tolist(),'origin':origin,'method':method,'name':self.fields['name'].get_text(),'xunit':self.fields['xunit'].get_text(),'yunit':self.fields['yunit'].get_text()}
        self.status.set_text(f'{origin} · {len(x)} pontos · {method}');self.set_plot(x,y,'Dados originais',True)
    def set_plot(self,x,y,title,scatter=False,extra=None):
        self.last_plot={'title':title,'xlabel':self.fields['xunit'].get_text(),'ylabel':self.fields['yunit'].get_text(),'series':[{'name':self.fields['name'].get_text(),'points':list(zip(x,y)),'scatter':scatter}]+(extra or [])};self.show_references()
    def show_references(self):
        if not self.last_plot:return
        data=copy.deepcopy(self.last_plot)
        for ref in self.references:
            if ref['xlabel']==data['xlabel'] and ref['ylabel']==data['ylabel'] and ref['mode']==self.mode.get_selected():data['series']+=copy.deepcopy(ref['series'][:1])
        self.plot.set_plot(data)
    def import_csv(self):
        def opened(path):
            if path.stat().st_size>12000000:raise ValueError('CSV excede 12 MB.')
            x,y=core.read_csv(path.read_text(encoding='utf-8-sig'));self.fields['name'].set_text(path.stem);self.set_data(x,y,'Experimental importado',path.name+'; ordenado por x; sem suavização')
        choose(self.window,'Importar duas colunas CSV',opened)
    def simulate(self):
        mode=self.mode.get_selected()
        if mode==0:
            x=np.linspace(500,4000,701);y=.2+1.2*np.exp(-.5*((x-1700)/35)**2)+.65*np.exp(-.5*((x-3300)/120)**2);self.set_data(x,y,'Ilustração didática','Bandas gaussianas artificiais; não identificam uma substância.')
        elif mode==1:
            x,y=core.simulate_calibration(self.val('slope'),self.val('intercept'),self.val('noise'),int(self.val('seed')));self.set_data(x,y,'Simulado',f'Reta + ruído gaussiano; semente {int(self.val("seed"))}.')
        elif mode==2:
            order=int(self.val('order'))
            if order!=self.val('order') or order not in (0,1,2):raise ValueError('Ordem deve ser 0, 1 ou 2.')
            x,y=core.simulate_kinetics(self.val('c0'),self.val('k'),order,self.val('duration'),self.val('noise'),int(self.val('seed')));self.set_data(x,y,'Simulado',f'Ordem {order}; k={self.val("k"):g}; ruído={self.val("noise"):g}; semente={int(self.val("seed"))}.')
        else:self.analyze()
    def analyze(self):
        self.pause();self.generation+=1;mode=self.mode.get_selected();self.secondary.set_plot(None);self.tertiary.set_plot(None)
        if mode==3:
            pkas=[float(x.replace(',','.')) for x in self.fields['pkas'].get_text().split(';')];x,y=core.polyprotic_titration(pkas,self.val('acid_c'),self.val('acid_ml'),self.val('base_c'),self.val('max_ml'))
            self.set_data(x,y,'Calculado','Ácido de 1–3 prótons e base forte; equilíbrio ideal a 25 °C, Kw=10⁻¹⁴.')
            from nexum.core.titration_analysis import analyze_curve
            deriv=analyze_curve(list(zip(x,y)))
            for chart,key,label in [(self.secondary,'first_derivative','dpH/dV (mL⁻¹)'),(self.tertiary,'second_derivative','d²pH/dV² (mL⁻²)')]:chart.set_plot({'title':label,'xlabel':'mL','ylabel':label,'series':[{'name':'Diferenças divididas','points':deriv[key]}]})
            self.report.set_text('Equivalências estequiométricas: '+', '.join(f'{n*self.val("acid_c")*self.val("acid_ml")/self.val("base_c"):.5g} mL' for n in range(1,len(pkas)+1))+'. A resolução das etapas depende da separação dos pKa; derivadas não garantem que todos os pontos sejam observáveis.');return
        if mode==4:
            formula=self.fields['formula'].get_text();charge=int(self.val('charge'));generation=self.generation
            if charge!=self.val('charge'):raise ValueError('Carga deve ser inteira.')
            def work():return chemistry_worker.call('isotopes',formula,charge) if chemistry_worker.configured() else core.isotope_pattern(formula,charge)
            def done(points):
                if generation!=self.generation:return
                x,y=np.array(points).T;self.dataset={'x':x.tolist(),'y':y.tolist(),'origin':'Calculado','method':'Abundâncias naturais RDKit; massa do elétron corrigida; até 2048 combinações.','name':formula,'xunit':'m/z','yunit':'Intensidade relativa (%)'};self.set_plot(x,y,'Padrão isotópico teórico',True);self.status.set_text('Calculado · '+formula);self.report.set_text(self.dataset['method']+' Não prevê fragmentação ou largura instrumental. A fórmula deve incluir o aduto e todos os átomos da espécie iônica.')
            background(self.window,work,done);return
        if not self.dataset:raise ValueError('Importe dados ou gere uma simulação primeiro.')
        x=np.array(self.dataset['x']);y=np.array(self.dataset['y'])
        if mode==0:
            r=core.analyze_spectrum(x,y,'linear' if self.baseline.get_active() else 'none',self.val('prominence'),self.val('lower',x[0]),self.val('upper',x[-1]));self.set_plot(x,r['corrected'],'Espectro analisado',extra=[{'name':'Original preservado','points':list(zip(x,y))}]);self.report.set_text(f'Área: {r["area"]:.6g} ({self.fields["xunit"].get_text()} × {self.fields["yunit"].get_text()})\nPicos: '+', '.join(f'{p["x"]:.6g}' for p in r['peaks'][:50])+'\n'+r['method'])
        elif mode==1:
            r=core.calibration(x,y,self.val('sample'));self.set_plot(x,y,'Calibração',True,[{'name':'Ajuste linear','points':list(zip(x,r['fitted']))}]);self.residuals(x,[('Resíduos',r['residuals'])]);self.report.set_text(f'Inclinação: {r["slope"]:.6g} ± {r["slope_u"]:.2g}\nIntercepto: {r["intercept"]:.6g}\nConcentração: {r["estimate"]:.6g} ± {r["u"]:.2g} {self.fields["xunit"].get_text()} (u padrão)\n'+('EXTRAPOLAÇÃO: fora da faixa calibrada.\n' if r['extrapolation'] else '')+r['method'])
        else:
            generation=self.generation
            def done(results):
                if generation!=self.generation:return
                self.set_plot(x,y,'Comparação cinética',True,[{'name':f'Ordem {r["order"]}','points':list(zip(x,r['fitted']))} for r in results]);self.residuals(x,[(f'Ordem {r["order"]}',r['residuals']) for r in results]);self.report.set_text('\n'.join(f'Ordem {r["order"]}: k={r["k"]:.6g}; u(k)={r["k_u"]}; RMSE={r["rmse"]:.4g}; AIC={r["aic"]:.5g}' for r in results)+'\nMenor AIC primeiro; não prova mecanismo químico. Ajuste na concentração original, volume constante. Unidades de k: ordem 0, mol L⁻¹ s⁻¹; ordem 1, s⁻¹; ordem 2, L mol⁻¹ s⁻¹. Incerteza local pela covariância.')
            background(self.window,lambda:core.fit_kinetics(x,y),done)
    def residuals(self,x,series):self.secondary.set_plot({'title':'Resíduos: observado − ajustado','xlabel':self.fields['xunit'].get_text(),'ylabel':self.fields['yunit'].get_text(),'series':[{'name':name,'points':list(zip(x,y)),'scatter':True} for name,y in series]})
    def pin(self):
        if not self.last_plot:raise ValueError('Calcule primeiro.')
        if len(self.references)>=8:raise ValueError('Limite de oito referências; limpe as comparações.')
        ref=copy.deepcopy(self.last_plot);ref['mode']=self.mode.get_selected();ref['inputs']={k:w.get_text() for k,w in self.fields.items()};self.references.append(ref);self.window.toast('Curva e parâmetros guardados.')
    def clear_references(self):self.references=[];self.show_references()
    def export_csv(self):
        if not self.dataset:raise ValueError('Nenhum dado para exportar.')
        data=copy.deepcopy(self.dataset)
        def write(path):
            with path.open('w',encoding='utf-8',newline='') as stream:
                stream.write('# '+data['origin']+'; '+data['method'].replace('\n',' ')+'\n');writer=csv.writer(stream);writer.writerow([data['xunit'],data['yunit']]);writer.writerows(zip(data['x'],data['y']))
        choose(self.window,'Exportar dados originais',write,True,'dados.csv')
    def export_plot(self,kind):choose(self.window,'Exportar gráfico',lambda path:self.plot.export(path,kind),True,'grafico.'+kind)
    def pause(self):
        if self.timer:GLib.source_remove(self.timer);self.timer=0
    def step(self):
        if not self.last_plot:return
        self.progress=min(getattr(self,'progress',0)+1,len(self.last_plot['series'][0]['points']));data=copy.deepcopy(self.last_plot)
        for series in data['series']:series['points']=series['points'][:self.progress]
        self.plot.set_plot(data)
    def play(self):
        if self.timer:self.pause();return
        if not self.last_plot:raise ValueError('Gere uma curva primeiro.')
        self.progress=0
        def tick():
            self.step()
            if self.progress>=len(self.last_plot['series'][0]['points']):self.timer=0;return False
            return True
        self.timer=GLib.timeout_add(80,tick)
    def snapshot(self):
        self.pause();buf=self.notes.get_buffer()
        return {'mode':self.mode.get_selected(),'fields':{k:w.get_text() for k,w in self.fields.items()},'baseline':self.baseline.get_active(),'dataset':self.dataset,'references':self.references,'plot':self.last_plot,'secondary':self.secondary.data,'tertiary':self.tertiary.data,'report':self.report.get_text(),'notes':buf.get_text(buf.get_start_iter(),buf.get_end_iter(),True)}
    def restore(self,data):
        self.mode.set_selected(int(data.get('mode',0)));self.change_mode()
        for k,v in data.get('fields',{}).items():
            if k in self.fields:self.fields[k].set_text(str(v))
        self.baseline.set_active(bool(data.get('baseline',False)));self.dataset=data.get('dataset');self.references=data.get('references',[]);self.last_plot=data.get('plot');self.show_references();self.secondary.set_plot(data.get('secondary'));self.tertiary.set_plot(data.get('tertiary'));self.report.set_text(data.get('report',''));self.notes.get_buffer().set_text(data.get('notes',''));self.status.set_text('Sessão restaurada; dados e parâmetros preservados.')
