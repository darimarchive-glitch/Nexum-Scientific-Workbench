import unittest,math
from pathlib import Path
from nexum.core.process_calculators import pipe_loss,exchanger,chromatography
from nexum.catalog import counts
from nexum.core.registry import TOOLS
from nexum.core.calculators import CALCS

class ProcessAndCatalog(unittest.TestCase):
    def test_laminar_poiseuille(self):
        d=dict(rho='1000',mu='.1',diam='.05',length='10',velocity='.1',rough='0')
        r=pipe_loss(d)
        self.assertAlmostEqual(r.data['pressure_drop_pa'],32*.1*10*.1/.05**2)
        d.update(mu='.001',velocity='.06')
        with self.assertRaises(ValueError):pipe_loss(d)
    def test_equal_terminal_differences(self):
        r=exchanger(dict(hot_in='100',hot_out='80',cold_in='20',cold_out='40',u='500',area='2'))
        self.assertAlmostEqual(r.data['lmtd_k'],60)
        self.assertAlmostEqual(r.data['duty_w'],60000)
        with self.assertRaises(ValueError):exchanger(dict(hot_in='nan',hot_out='80',cold_in='20',cold_out='40',u='500',area='2'))
    def test_chromatography(self):
        r=chromatography(dict(dead='1',first='4',second='5',w1='.5',w2='.5'))
        self.assertEqual(r.data['resolution'],2)
        self.assertAlmostEqual(r.data['selectivity'],4/3)
    def test_catalog_and_logo(self):
        self.assertEqual(counts()['calculators'],len(CALCS))
        self.assertEqual({t[0] for t in TOOLS},set(CALCS))
        root=Path(__file__).resolve().parents[1]
        self.assertEqual((root/'docs/logo-nexum.svg').read_bytes(),(root/'nexum/assets/logo.svg').read_bytes())
        self.assertIn(f"**{len(CALCS)} calculadoras",(root/'README.md').read_text(encoding='utf-8'))
