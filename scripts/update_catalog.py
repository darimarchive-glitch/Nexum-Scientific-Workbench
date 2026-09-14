"""Keep the README summary synchronized with the public application catalog."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nexum.catalog import counts
path=Path(__file__).resolve().parents[1]/'README.md'
start='<!-- nexum-catalog:start -->';end='<!-- nexum-catalog:end -->'
c=counts();summary=f"**{c['calculators']} calculadoras · {c['areas']} áreas científicas · {c['experiments']} bancadas · {c['analyses']} ferramentas de análise de dados**"
text=path.read_text(encoding='utf-8');a=text.index(start)+len(start);b=text.index(end)
updated=text[:a]+'\n'+summary+'\n'+text[b:]
if '--check' in sys.argv:
    if updated!=text:raise SystemExit('Catálogo desatualizado: execute python scripts/update_catalog.py')
else:path.write_text(updated,encoding='utf-8')
