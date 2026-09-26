"""Run the suite and record reproducible counts; skipped tests are not passes."""
from pathlib import Path
import importlib.metadata
import json
import platform
import sys
import time
import unittest
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from nexum.identity import VERSION
out=root/'build/validation';out.mkdir(parents=True,exist_ok=True)
start=time.monotonic()
with (out/'tests.txt').open('w',encoding='utf-8') as log:
    suite=unittest.defaultTestLoader.discover(str(root/'tests'))
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
packages={}
for name in ['numpy','scipy','rdkit','gemmi','Pillow','PyOpenGL']:
    try:packages[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:packages[name]=None
report={'version':VERSION,'platform':platform.platform(),'python':platform.python_version(),'dependencies':packages,
        'tests':result.testsRun,'passed':result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
        'skipped':[{'test':str(t),'reason':why} for t,why in result.skipped],
        'failures':len(result.failures),'errors':len(result.errors),'seconds':round(time.monotonic()-start,2)}
(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('dependencies','skipped')},ensure_ascii=False))
print('Ignorados:',len(result.skipped))
if not result.wasSuccessful():
    print((out/'tests.txt').read_text()[-8000:]);raise SystemExit(1)
