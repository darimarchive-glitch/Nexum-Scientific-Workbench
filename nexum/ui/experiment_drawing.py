"""Cairo laboratory diagrams shared by GTK and offline visual verification.

Only consumes calculated ExperimentSession data. Does not import GTK or keep
an independent animation clock. Motion freezes when the session stops.
"""
from __future__ import annotations

import math
from nexum.core.experiment_session import number

BLUE = (.18, .49, .87, 1.)
TEAL = (.12, .65, .58, 1.)
ORANGE = (.91, .48, .20, 1.)
PURPLE = (.60, .39, .85, 1.)


def flask_fill_height(fraction):
    """Height fraction for an idealized conical flask plus cylindrical neck.

    Integrates cross-sectional area, so equal added volumes do not imply equal
    height increments in the conical part of an Erlenmeyer.
    """
    fraction = max(0., min(1., fraction))
    slope = (.44-.10)/.75

    def volume(z):
        a = min(z, .75)
        return .44**2*a - .44*slope*a*a + slope*slope*a**3/3 + max(0., z-.75)*.10**2

    target = fraction*volume(1.)
    lo, hi = 0., 1.
    for _ in range(45):
        mid = (lo+hi)/2
        if volume(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


class LaboratoryDrawing:
    def __init__(self, cr, dark=False):
        self.cr = cr
        self.dark = dark
        self.fg = (.88, .90, .93, 1.) if dark else (.20, .25, .31, 1.)
        self.muted = (.60, .66, .73, 1.) if dark else (.42, .48, .55, 1.)
        self.edge = (.53, .64, .72, .8) if dark else (.41, .54, .63, .75)
        self.panel = (.55, .65, .77, .07)

    def color(self, color):
        self.cr.set_source_rgba(*color)

    def text(self, x, y, text, size=15, color=None, bold=False, width=None, align="left"):
        cr = self.cr
        cr.save()
        self.color(color or self.fg)
        cr.select_font_face("Sans", 0, 1 if bold else 0)
        cr.set_font_size(size)
        text = str(text)
        extent = cr.text_extents(text)
        if width and extent[2] > width:
            cr.set_font_size(max(9, size*width/extent[2]))
            extent = cr.text_extents(text)
        if align == "center":
            x -= extent[2]/2+extent[0]
        elif align == "right":
            x -= extent[2]+extent[0]
        cr.move_to(x, y)
        cr.show_text(text)
        cr.restore()

    def line(self, points, color=None, width=2, dash=()):
        cr = self.cr
        cr.save()
        self.color(color or self.edge)
        cr.set_line_width(width)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        cr.set_dash(dash)
        for i, (x, y) in enumerate(points):
            cr.move_to(x, y) if i == 0 else cr.line_to(x, y)
        cr.stroke()
        cr.restore()

    def rect(self, x, y, w, h, fill=None, stroke=None, radius=0):
        cr = self.cr
        cr.new_path()
        if radius:
            r = min(radius, abs(w)/2, abs(h)/2)
            for cx, cy, angle in ((x+w-r, y+r, -math.pi/2), (x+w-r, y+h-r, 0),
                                  (x+r, y+h-r, math.pi/2), (x+r, y+r, math.pi)):
                cr.arc(cx, cy, r, angle, angle+math.pi/2)
            cr.close_path()
        else:
            cr.rectangle(x, y, max(0, w), max(0, h))
        if fill:
            self.color(fill)
            cr.fill_preserve()
        if stroke:
            self.color(stroke)
            cr.set_line_width(2)
            cr.stroke_preserve()
        cr.new_path()

    def dot(self, x, y, r, color, outline=None):
        cr = self.cr
        cr.new_path()
        cr.arc(x, y, max(0, r), 0, math.tau)
        self.color(color)
        cr.fill_preserve()
        if outline:
            self.color(outline)
            cr.set_line_width(1.5)
            cr.stroke_preserve()
        cr.new_path()

    def arrow(self, start, end, color=None, width=2.5):
        self.line([start, end], color, width)
        angle = math.atan2(end[1]-start[1], end[0]-start[0])
        points = [(end[0]-8*math.cos(angle-.48), end[1]-8*math.sin(angle-.48)),
                  end, (end[0]-8*math.cos(angle+.48), end[1]-8*math.sin(angle+.48))]
        self.line(points, color, width)

    def value(self, x, y, label, value, color=BLUE, width=270):
        self.text(x, y, label, 13, self.muted, width=width)
        self.text(x, y+31, value, 26, color, bold=True, width=width)

    def glass(self, x, y, w, h, fraction=.65, liquid=(.20, .55, .9, .25)):
        self.rect(x+3, y+h*(1-fraction), w-6, h*fraction-3, fill=liquid)
        self.line([(x, y), (x, y+h-10), (x+8, y+h), (x+w-8, y+h), (x+w, y+h-10), (x+w, y)])
        self.line([(x+4, y+h*(1-fraction)), (x+w-4, y+h*(1-fraction))], liquid[:3]+(.65,), 1.5)
        self.line([(x+8, y+12), (x+8, y+h-16)], (1, 1, 1, .3), 3)
        for i in range(1, 5):
            self.line([(x+w-20, y+h*i/5), (x+w-7, y+h*i/5)], self.edge, 1)

    def flask(self, x, y, w, h, fraction, liquid):
        cr = self.cr

        def path():
            cr.new_path()
            cr.move_to(x+w*.4, y)
            cr.line_to(x+w*.4, y+h*.25)
            cr.line_to(x+w*.06, y+h)
            cr.line_to(x+w*.94, y+h)
            cr.line_to(x+w*.6, y+h*.25)
            cr.line_to(x+w*.6, y)
            cr.close_path()

        level = y+h*(1-flask_fill_height(fraction))
        cr.save()
        path()
        cr.clip()
        self.rect(x, y, w, h, fill=(.50, .76, .94, .035))
        self.rect(x, level, w, y+h-level, fill=liquid)
        self.line([(x, level), (x+w, level)], liquid[:3]+(.8,), 1.5)
        self.line([(x+w*.17, y+h*.88), (x+w*.43, y+h*.3)], (1, 1, 1, .45), 3)
        cr.restore()
        path()
        self.color(self.edge)
        cr.set_line_width(2.2)
        cr.stroke()
        self.line([(x+w*.36, y), (x+w*.64, y)], self.edge, 3)
        for f in (.3, .5, .7):
            yy = y+h*(1-flask_fill_height(f))
            self.line([(x+w*.62, yy), (x+w*.72, yy)], self.edge, 1)

    def bench(self, width, height, session, running=False):
        cr = self.cr
        cr.save()
        scale = min(width/800, height/430)
        cr.translate((width-800*scale)/2, (height-430*scale)/2)
        cr.scale(scale, scale)
        self.rect(16, 14, 768, 400, fill=self.panel, radius=14)
        if session is None:
            self.text(400, 205, "Confira os parâmetros para preparar a bancada.", 18, align="center", width=700)
            cr.restore()
            return
        method = getattr(self, "_"+session.exp.id)
        method(session, running)
        cr.restore()

    def _gas(self, session, running):
        s, c = session.state, session.config
        x, y, w, h = 98, 117, 570, 208
        lo, hi = sorted((c["volume_initial_l"], c["volume_final_l"]))
        f = (s["volume_l"]-lo)/(hi-lo) if hi > lo else .7
        px = x+w*(.18+.76*f)
        self.text(44, 48, "COMPRESSÃO / EXPANSÃO ISOTÉRMICA", 13, self.muted, True)
        self.rect(x, y, w, h, stroke=self.edge)
        self.rect(x, y, px-x, h, fill=(.18, .49, .87, .16))
        self.rect(px-5, y, 10, h, fill=self.fg)
        self.line([(px+5, y+h/2), (w+x+42, y+h/2)], self.edge, 9)
        self.value(102, 355, "Volume", number(s["volume_l"])+" L")
        self.value(430, 355, "Pressão", number(s["pressure_bar"])+" bar")

    def _titration(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "BURETA + ERLENMEYER", 13, self.muted, True)
        self.line([(111, 70), (111, 372)], self.edge, 5)
        self.rect(65, 372, 120, 8, fill=self.edge, radius=3)
        self.line([(111, 102), (278, 102)], self.edge, 4)
        self.rect(266, 58, 28, 121, stroke=self.edge, radius=3)
        fraction = s["remaining_base_ml"]/c["max_volume_ml"]
        self.rect(269, 62+113*(1-fraction), 22, 113*fraction, fill=(.27, .63, .90, .38))
        for i in range(6):
            yy = 63+22*i
            self.line([(282, yy), (292, yy)], self.edge, 1)
        self.line([(280, 180), (280, 196)], self.edge)
        self.line([(267, 184), (293, 184)], TEAL if running else self.edge, 3)
        if running and not session.complete:
            drop_y = 198+(session.elapsed*c["flow_ml_s"]/.05 % 1)*21
            self.dot(280, drop_y, 3, BLUE)
        capacity = next((v for v in (50, 100, 250, 500, 1000, 2000) if v >= (c["acid_v_ml"]+c["max_volume_ml"])/.8),
                        (c["acid_v_ml"]+c["max_volume_ml"])/.8)
        self.flask(185, 221, 190, 150, s["liquid_volume_ml"]/capacity, s["indicator"]["color"])
        self.text(304, 79, "Base forte", 14, bold=True)
        self.text(304, 100, number(c["base_c"])+" mol/L", 13, self.muted)
        self.text(304, 143, "Na bureta: "+number(s["remaining_base_ml"])+" mL", 13, self.muted, width=390)
        self.text(138, 218, "Ácido forte" if c["mode"] == "strong-strong" else "Ácido fraco HA", 13, bold=True, width=122)
        self.text(138, 241, number(c["acid_c"])+" mol/L", 12, self.muted, width=120)
        self.text(138, 262, number(c["acid_v_ml"])+" mL iniciais", 12, self.muted, width=111)
        self.text(280, 396, "Volume total: "+number(s["liquid_volume_ml"])+" mL", 15, align="center", width=365)
        self.value(468, 203, "pH da solução", number(s["ph"], 5), width=260)
        self.value(468, 279, c["indicator"], s["indicator"]["label"], PURPLE, width=250)
        self.text(468, 353, "Equivalência: "+number(s["equivalence_ml"])+" mL", 15, width=270)
        self.text(468, 377, "Cores ilustrativas do indicador", 12, self.muted, width=270)

    def _electro(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "CIRCUITO EXTERNO E PONTE SALINA", 13, self.muted, True)
        active = (running or session.elapsed > 0) and s["current_a"] > 0 and not s["exhausted"]
        self.line([(175, 187), (175, 91), (626, 91), (626, 187)], self.edge, 3)
        self.rect(350, 71, 100, 40, fill=(.15, .30, .35, .95), radius=6)
        self.text(400, 97, number(s["current_a"])+" A", 18, (0.5, 1., .77, 1), True, align="center")
        self.arrow((239, 125), (331, 125), BLUE)
        self.text(279, 149, "e⁻ → Cu", 12, BLUE, align="center")
        self.arrow((562, 125), (473, 125), ORANGE)
        self.text(518, 149, "I convencional", 12, ORANGE, align="center")
        if active:
            # Visual packets follow the wire, not a literal electron drift speed.
            for i in range(10):
                distance = ((i/10+s["time_s"]*(.08+.035*math.log1p(s["current_a"]))) % 1)*643
                if distance < 96:
                    x, y = 175, 187-distance
                elif distance < 547:
                    x, y = 175+distance-96, 91
                else:
                    x, y = 626, 91+distance-547
                if not (350 < x < 450 and y == 91):
                    self.dot(x, y, 4, BLUE)
        self.glass(104, 218, 184, 123, .73, (.55, .75, .87, .13))
        copper_fraction = max(0., min(1., s["cu_conc_m"]/c["cu_conc0"]))
        self.glass(511, 218, 184, 123, .73, (.16, .52, .88, .08+.34*copper_fraction))
        self.rect(162, 176, 26, 137, fill=(.52, .58, .64, 1.), radius=3)
        self.rect(613, 176, 26, 137, fill=(.76, .43, .25, 1.), radius=3)
        self.text(175, 204, "Zn", 14, (1, 1, 1, 1), True, align="center")
        self.text(626, 204, "Cu", 14, (1, 1, 1, 1), True, align="center")
        self.line([(260, 262), (260, 188), (535, 188), (535, 262)], self.edge, 15)
        self.line([(260, 262), (260, 188), (535, 188), (535, 262)], (.50, .81, .71, .8), 10)
        self.text(400, 177, "Ponte salina: fluxo de íons", 13, self.muted, align="center")
        if active:
            phase = (s["time_s"]*.25) % 1
            self.dot(450-phase*107, 186, 4, PURPLE)
            self.dot(346+phase*107, 191, 4, TEAL)
            self.text(317, 214, "ânions ←", 11, PURPLE)
            self.text(430, 214, "→ cátions", 11, TEAL)
            phase = (s["time_s"]*.6) % 1
            self.dot(194+phase*43, 292+math.sin(phase*math.pi)*12, 5, self.edge)
            self.dot(559+phase*43, 288, 5, BLUE)
        self.text(197, 367, "Zn → Zn²⁺ + 2 e⁻", 16, align="center")
        self.text(605, 367, "Cu²⁺ + 2 e⁻ → Cu", 16, align="center")
        self.text(197, 391, "Dissolvido: "+number(s["zinc_mass_lost_g"]*1000)+" mg", 13, self.muted, align="center", width=300)
        self.text(605, 391, "Depositado: "+number(s["copper_mass_deposited_g"]*1000)+" mg", 13, self.muted, align="center", width=300)
        self.text(400, 293, "E reversível", 12, self.muted, align="center")
        self.text(400, 319, number(s["e_rev_v"], 7)+" V", 21, TEAL, True, align="center", width=205)

    def _calorimetry(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "CALORÍMETRO COM RESISTÊNCIA ELÉTRICA", 13, self.muted, True)
        self.rect(141, 158, 239, 198, fill=(.45, .55, .65, .07), stroke=self.edge, radius=14)
        temp = s["temperature_c"]
        warm = max(0, min(1, (temp-20)/60))
        liquid = (.21+.67*warm, .60-.20*warm, .87-.62*warm, .40)
        self.glass(154, 172, 213, 170, .66, liquid)
        self.rect(131, 151, 259, 17, fill=self.edge, radius=5)
        self.line([(182, 85), (182, 280), (194, 290), (208, 268), (222, 290), (236, 268), (250, 290), (260, 280), (260, 85)],
                  ORANGE if c["heater_power_w"] > 0 and running else self.muted, 4)
        self.rect(157, 70, 123, 42, fill=(.16, .24, .3, 1), radius=6)
        self.text(219, 97, number(c["heater_power_w"])+" W", 17, (1, .78, .43, 1), True, align="center")
        self.rect(321, 74, 15, 225, fill=(.65, .70, .72, .14), stroke=self.edge, radius=6)
        curve = [p[1] for p in session.reference_curve]
        low, high = min(curve)-2, max(curve)+2
        top = 91+188*(1-(temp-low)/(high-low))
        self.rect(326, top, 5, 299-top, fill=ORANGE)
        self.dot(329, 301, 10, ORANGE)
        for i in range(5):
            yy = 91+i*47
            self.line([(338, yy), (344, yy)], self.edge, 1)
            self.text(351, yy+4, number(high-(high-low)*i/4, 3), 11, self.muted, width=65)
        self.text(329, 65, "°C", 13, self.muted, align="center")
        if running and c["heater_power_w"] > 0:
            for i in range(3):
                yy = 282-((s["time_s"]*.35+i/3) % 1)*64
                self.arrow((205+i*18, yy+16), (205+i*18, yy), ORANGE, 1.8)
        flow = s["heat_flow_w"]
        if flow != 0:
            for yy in (231, 256):
                self.arrow((384, yy) if flow > 0 else (452, yy),
                           (452, yy) if flow > 0 else (384, yy), ORANGE if flow > 0 else BLUE)
        self.value(476, 115, "Temperatura da amostra", number(temp, 5)+" °C", ORANGE)
        self.text(476, 184, "Ambiente: "+number(c["ambient_temp_k"]-273.15)+" °C", 15, self.muted, width=268)
        self.value(476, 245, "Troca com o ambiente", number(flow)+" W", TEAL)
        self.text(476, 323, "Entrada = armazenada + transferida", 13, width=270)
        self.text(476, 347, number(s["input_energy_j"])+" = "+number(s["stored_energy_j"])+" + "+number(s["heat_lost_j"])+" J", 14, self.muted, width=268)
        self.text(260, 389, "Cor = temperatura · nível constante", 13, self.muted, align="center", width=360)

    def _molecule(self, x, y, species):
        color = {"n_n2": BLUE, "n_h2": TEAL, "n_nh3": ORANGE}[species]
        if species == "n_nh3":
            for dx, dy in ((-6, 4), (6, 4), (0, -7)):
                self.dot(x+dx, y+dy, 2.8, TEAL)
            self.dot(x, y, 4.5, ORANGE)
        else:
            self.dot(x-3.5, y, 4, color)
            self.dot(x+3.5, y, 4, color)

    def _reactor(self, x, values, title, max_total):
        self.text(x+140, 118, title, 16, bold=True, align="center")
        self.rect(x, 135, 280, 175, fill=(.4, .5, .6, .07), stroke=self.edge, radius=32)
        self.rect(x+24, 125, 233, 13, fill=self.edge, radius=4)
        for dx in range(44, 252, 33):
            self.dot(x+dx, 131, 3, self.fg)
        total = sum(values.values())
        keys = ("n_n2", "n_h2", "n_nh3")
        cumulative = [values[keys[0]]/total, (values[keys[0]]+values[keys[1]])/total, 1.]
        count = max(1, round(45*total/max_total))
        for i in range(count):
            selector = (i+.5)/count
            species = next(k for k, threshold in zip(keys, cumulative) if selector <= threshold)
            position = (i*17) % 45
            self._molecule(x+28+(position%9)*28, 162+(position//9)*30, species)
        self.text(x+140, 337, "Total: "+number(total)+" mol", 14, self.muted, align="center")

    def _haber(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "N₂ + 3 H₂ ⇌ 2 NH₃", 22, bold=True)
        self.text(756, 47, number(c["temp_k"])+" K · "+number(c["pressure_bar"])+" bar", 15, self.muted, align="right", width=330)
        initial = {k: c[k] for k in ("n_n2", "n_h2", "n_nh3")}
        max_total = max(sum(initial.values()), s["total_moles"])
        self._reactor(58, initial, "Composição inicial", max_total)
        self._reactor(462, s["equilibrium_moles"], "No equilíbrio", max_total)
        self.arrow((362, 218), (438, 218), self.muted)
        self.text(400, 245, "Comparação", 11, self.muted, align="center")
        for x, species, label in ((235, "n_n2", "N₂"), (362, "n_h2", "H₂"), (488, "n_nh3", "NH₃")):
            self._molecule(x, 379, species)
            self.text(x+19, 384, label, 15)
        self.text(400, 407, "Partículas proporcionais e cores ilustrativas; valores exatos no gráfico.", 11, self.muted, align="center")

    def _spectro(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "FONTE → CUBETA → DETECTOR", 13, self.muted, True)
        self.rect(64, 183, 118, 95, fill=self.panel, stroke=self.edge, radius=10)
        self.dot(159, 231, 15, (1., .69, .23, .8) if c["incident"] > 0 else self.edge)
        self.text(123, 311, "Fonte", 16, bold=True, align="center")
        self.text(123, 338, "I₀ = "+number(c["incident"]), 14, self.muted, align="center", width=170)
        cubew = 88+68*min(1, c["path_length_cm"]/5)
        x = 400-cubew/2
        self.rect(x, 119, cubew, 204, stroke=self.edge, radius=3)
        self.rect(x+4, 153, cubew-8, 166, fill=(.37, .30, .80, .10+.65*(1-s["transmittance"])))
        self.line([(x+8, 127), (x+8, 306)], (1, 1, 1, .4), 3)
        self.rect(x-4, 105, cubew+8, 18, fill=self.edge, radius=3)
        self.rect(635, 171, 104, 110, fill=self.panel, stroke=self.edge, radius=10)
        self.rect(638, 203, 12, 54, fill=self.edge, radius=3)
        if c["incident"] > 0:
            incoming = .25+.7*c["incident"]/(1+c["incident"])
            self.rect(183, 220, x-183, 22, fill=(1, .67, .16, incoming))
            for i in range(50):
                fraction = 10**(-s["absorbance"]*i/50)
                self.rect(x+cubew*i/50, 220, cubew/50+1, 22, fill=(1, .67, .16, incoming*fraction))
            self.rect(x+cubew, 220, 635-x-cubew, 22, fill=(1, .67, .16, incoming*s["transmittance"]))
        self.text(686, 311, "Detector", 16, bold=True, align="center")
        self.text(686, 338, "I = "+number(s["transmitted"]), 14, self.muted, align="center", width=165)
        self.arrow((x, 353), (x+cubew, 353), self.muted, 1.5)
        self.text(400, 378, "b = "+number(c["path_length_cm"])+" cm", 14, self.muted, align="center")
        self.text(123, 145, "Luz incidente", 13, self.muted, align="center")
        self.text(686, 145, "Transmitida: "+number(100*s["transmittance"], 4)+" %", 13, self.muted, align="center", width=185)
        self.text(400, 400, "Cubeta: c = "+number(c["concentration_m"])+" mol/L", 13, self.muted, align="center")

    def _kinetics(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "A → B · VOLUME CONSTANTE", 13, self.muted, True)
        self.flask(65, 99, 292, 256, .62, (.15, .49, .86, .09+.56*s["fraction_remaining"]))
        self.text(211, 389, "A perde intensidade à medida que reage", 13, self.muted, align="center", width=340)
        self.text(462, 99, "População relativa de A e B", 16, bold=True, width=280)
        if c["concentration0_m"] > 0:
            for i in range(80):
                is_a = ((i*37) % 80+.5)/80 < s["fraction_remaining"]
                self.dot(471+i%10*25, 130+i//10*18, 4.6, BLUE if is_a else (.55, .61, .67, .33))
        else:
            self.text(585, 194, "Sem A na amostra", 17, self.muted, align="center")
        self.dot(468, 296, 5, BLUE)
        self.text(482, 301, "A: "+number(s["concentration_m"])+" mol/L", 14, width=250)
        self.dot(468, 327, 5, (.55, .61, .67, .33))
        self.text(482, 332, "B: "+number(s["product_m"])+" mol/L", 14, width=250)
        self.text(462, 379, "t½ = "+number(s["half_life_s"])+" s", 19, BLUE, True, width=270)

    def _nuclear(self, session, running):
        s, c = session.state, session.config
        self.text(44, 48, "POPULAÇÃO VIRTUAL · DECAIMENTO", 13, self.muted, True)
        self.rect(62, 89, 318, 278, fill=self.panel, stroke=self.edge, radius=12)
        if c["nuclei0"] > 0:
            for i in range(100):
                remaining = ((i*37) % 100+.5)/100 < s["fraction_remaining"]
                self.dot(91+i%10*29, 112+i//10*26, 7, PURPLE if remaining else (.55, .61, .67, .22))
        else:
            self.text(221, 231, "N₀ = 0", 24, self.muted, align="center")
        self.value(453, 124, "Núcleos restantes (esperado)", number(s["remaining"]), PURPLE)
        self.value(453, 218, "Núcleos transformados", number(s["decayed"]), TEAL)
        self.text(453, 323, number(session.elapsed/c["half_life_s"], 3)+" meias-vidas decorridas", 16, width=280)
        self.text(221, 395, "1 marca = 1% da população inicial", 13, self.muted, align="center", width=345)
        self.text(453, 379, "t½ = "+number(c["half_life_s"])+" s", 19, PURPLE, True, width=270)

    def chart(self, width, height, session):
        if session is None:
            self.text(24, 40, "O gráfico aparece com parâmetros válidos.", 14, self.muted, width=width-48)
            return
        if session.exp.id == "haber":
            self._composition_chart(width, height, session)
            return
        cr = self.cr
        left, top, right, bottom = 76., 46., max(115., width-25.), max(105., height-49.)
        points = session.reference_curve + ([session.point] if session.point else [])
        points = [(x, y) for x, y in points if math.isfinite(x) and math.isfinite(y)]
        if not points:
            return
        xmin, xmax = 0., max(x for x, _ in points)
        ymin, ymax = min(y for _, y in points), max(y for _, y in points)
        if session.exp.id == "titration":
            ymin, ymax = min(0., ymin), max(14., ymax)
        elif session.exp.id in ("kinetics", "nuclear", "spectro"):
            ymin = 0.
        xmax = max(1e-12, xmax)
        if ymax-ymin < max(1e-10, abs(ymax)*1e-10):
            span = max(1., abs(ymax)*.02)
            ymin -= span*.5
            ymax += span*.5
        elif session.exp.id != "titration":
            span = ymax-ymin
            ymax += span*.06
            if ymin != 0:
                ymin -= span*.06

        def project(x, y):
            return left+(x-xmin)/(xmax-xmin)*(right-left), bottom-(y-ymin)/(ymax-ymin)*(bottom-top)

        self.text(left, 21, session.ylabel, 12, self.muted, bold=True, width=width*.37)
        if width >= 580:
            items = [("Modelo", (.50, .57, .64, .75))]
            if session.dynamic:
                items.append(("Trajetória", BLUE))
            items.append(("Atual", ORANGE))
            for i, (label, color) in enumerate(items):
                lx = right-95*(len(items)-i)
                self.line([(lx, 17), (lx+13, 17)], color, 2.5)
                self.text(lx+19, 21, label, 11, self.muted)
        else:
            self.dot(right-60, 17, 3, ORANGE)
            self.text(right-50, 21, "Atual", 11, self.muted)
        ystep = (ymax-ymin)/4
        # Keep closely spaced Nernst voltages distinguishable on the axis.
        ydigits = max(4, min(12, math.ceil(math.log10(max(abs(ymin), abs(ymax), 1e-100)/ystep))+2))
        for i in range(5):
            y = ymin+(ymax-ymin)*i/4
            _, py = project(0, y)
            self.line([(left, py), (right, py)], (.5, .5, .5, .13), 1)
            self.text(left-10, py+4, number(y, ydigits), 11, self.muted, align="right", width=64)
            x = xmax*i/4
            px, _ = project(x, ymin)
            self.text(px, bottom+20, number(x, 3), 11, self.muted, align="center", width=max(30, (right-left)/4-10))
        self.text((left+right)/2, height-8, session.xlabel, 12, self.muted, align="center", width=width-60)
        cr.save()
        cr.rectangle(left, top, right-left, bottom-top)
        cr.clip()
        if session.exp.id == "titration" and session.state["indicator"]["range"]:
            lo, hi = session.state["indicator"]["range"]
            y1, y2 = project(0, hi)[1], project(0, lo)[1]
            self.rect(left, y1, right-left, y2-y1, fill=(.85, .30, .65, .10))
            self.text(right-8, (y1+y2)/2+4, "Faixa de viragem", 10, PURPLE, align="right")
        for x, label in session.markers:
            px, _ = project(x, ymin)
            self.line([(px, top), (px, bottom)], (.53, .44, .73, .48), 1, (4, 4))
            self.text(min(right-38, max(left+38, px)), top+13, label, 10, PURPLE, align="center", width=72)
        for curve, color, weight in ((session.reference_curve, (.50, .57, .64, .57), 1.8),
                                     (session.history, BLUE, 2.6)):
            if len(curve) > 1:
                self.line([project(x, y) for x, y in curve], color, weight)
        if session.point:
            px, py = project(*session.point)
            self.line([(px, bottom), (px, py)], ORANGE[:3]+(.38,), 1, (3, 4))
            self.dot(px, py, 5, ORANGE, (1., 1., 1., .85))
        cr.restore()
        self.line([(left, top), (left, bottom), (right, bottom)], self.edge, 1)

    def _composition_chart(self, width, height, session):
        c, eq = session.config, session.state["equilibrium_moles"]
        maximum = max([c[k] for k in eq] + list(eq.values())) or 1.
        self.text(24, 24, "Quantidade / mol · inicial e equilíbrio na mesma escala", 12, self.muted, True, width=width-48)
        left, right = 105, max(140, width-100)
        gap = max(43, (height-54)/3)
        for i, (key, label, color) in enumerate((("n_n2", "N₂", BLUE), ("n_h2", "H₂", TEAL), ("n_nh3", "NH₃", ORANGE))):
            y = 46+i*gap
            self.text(25, y+21, label, 17, bold=True)
            for j, (value, alpha) in enumerate(((c[key], .26), (eq[key], .9))):
                yy = y+17*j
                self.rect(left, yy, (right-left)*value/maximum, 12, fill=color[:3]+(alpha,), radius=2)
                self.text(left-7, yy+10, "inicial" if j == 0 else "eq.", 10, self.muted, align="right")
                self.text(right+10, yy+11, number(value)+" mol", 11, self.muted, width=85)
