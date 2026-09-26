"""Public counts come from registries, never duplicated UI literals."""
from .core.registry import TOOLS,GROUPS
from .core.experiments import EXPERIMENTS
ANALYSES=('Espectros e integração','Curva de calibração','Cinética: ordens 0, 1 e 2','Titulação poliprótica','Padrão isotópico')
from .lab import CAPABILITIES
from .identity import VERSION
def counts():
    return {'calculators':len(TOOLS),'areas':len({t[1] for t in TOOLS}),'experiments':len(EXPERIMENTS),'analyses':len(ANALYSES),'laboratory':len(CAPABILITIES)}

