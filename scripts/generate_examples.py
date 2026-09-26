"""Regenerate the bundled teaching projects and original CSV examples."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from nexum.lab.examples import example
from nexum.lab.project import write_project
from nexum.lab.datasets import export_csv
names=['uv-vis','kinetics','titration','factorial-design','process-balance','quality-control']
for i,name in enumerate(names):
    d=example(i);d['id']=f'{i+1:032x}';d['created']=d['modified']='2026-09-26T00:00:00+00:00'
    for j,s in enumerate(d['datasets']):s['id']=f'{i+1:04x}{j+1:028x}'
    # Investigation and project share the dataset object in these built-in examples.
    write_project(root/'examples/projects'/f'{name}.nexum7',d)
    for j,series in enumerate(d['datasets']):export_csv(series,root/'examples/data'/f'{name}-{j+1}.csv')
print('Seis projetos e quatro séries didáticas gerados.')
