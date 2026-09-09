"""Nexum advanced scientific backend (v6.5).

Numerical algorithms are independent of the UI. Advanced solvers return
convergence/residual diagnostics so a displayed number is always traceable to
an actual computation and its declared model.
"""
from .numerics import *
from .activities import *
from .eos import *
from .equilibrium import *
from .kinetics import *
from .electrochem import *
from .metrology import *
from .thermo import *
from .spectroscopy import *
from .engine import *
from .protocols import *
