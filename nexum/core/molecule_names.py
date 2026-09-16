"""Curated Brazilian names. Exact aliases resolve; fuzzy matches only suggest."""
from .search import norm, dist

# CID, Brazilian name, molecular formula, unambiguous aliases.
COMPOUNDS = [
    ('962', 'Água', 'H2O', ('water', 'oxidane', '7732-18-5')),
    ('702', 'Etanol', 'C2H6O', ('ethanol', 'álcool etílico')),
    ('887', 'Metanol', 'CH4O', ('methanol', 'álcool metílico')),
    ('180', 'Acetona', 'C3H6O', ('acetone', 'propanona')),
    ('176', 'Ácido acético', 'C2H4O2', ('acetic acid', 'ácido etanoico')),
    ('2519', 'Cafeína', 'C8H10N4O2', ('caffeine',)),
    ('2244', 'Ácido acetilsalicílico', 'C9H8O4', ('aspirin', 'aspirina')),
    ('1983', 'Paracetamol', 'C8H9NO2', ('acetaminophen', 'paracetamol')),
    ('5234', 'Cloreto de sódio', 'NaCl', ('sodium chloride', 'sal de cozinha')),
    ('280', 'Dióxido de carbono', 'CO2', ('carbon dioxide', 'gás carbônico')),
    ('222', 'Amônia', 'H3N', ('ammonia', 'NH3')),
    ('784', 'Peróxido de hidrogênio', 'H2O2', ('hydrogen peroxide',)),
    ('241', 'Benzeno', 'C6H6', ('benzene',)),
    ('1140', 'Tolueno', 'C7H8', ('toluene', 'metilbenzeno')),
    ('297', 'Metano', 'CH4', ('methane',)),
    ('6324', 'Etano', 'C2H6', ('ethane',)),
    ('6334', 'Propano', 'C3H8', ('propane',)),
    ('5988', 'Sacarose', 'C12H22O11', ('sucrose', 'açúcar de mesa')),
    ('1118', 'Ácido sulfúrico', 'H2SO4', ('sulfuric acid',)),
    ('944', 'Ácido nítrico', 'HNO3', ('nitric acid',)),
    ('313', 'Ácido clorídrico', 'ClH', ('hydrochloric acid', 'HCl')),
]
BY_CID = {row[0]: row for row in COMPOUNDS}
# Most molecular formulas identify several isomers, so only selected simple
# formulas are direct aliases. Other formulas remain suggestions to select.
DIRECT_FORMULAS = {'H2O','NaCl','CO2','H3N','H2O2','CH4','C2H6','C3H8','H2SO4','HNO3','ClH'}
ALIASES = {norm(alias): row for row in COMPOUNDS for alias in (row[1], *row[3])}
ALIASES.update({norm(row[2]):row for row in COMPOUNDS if row[2] in DIRECT_FORMULAS})

def exact_compound(term):
    raw = str(term).strip()
    return BY_CID.get(raw) or ALIASES.get(norm(raw))

def local_candidates(term, limit=4):
    q = norm(term)
    if not q or limit <= 0:
        return []
    exact = exact_compound(term)
    if exact:
        return [exact]
    ranked = {}
    entries=list(ALIASES.items())+[(norm(row[2]),row) for row in COMPOUNDS]
    for alias, row in entries:
        score = 1 if alias.startswith(q) else 2 if len(q) >= 4 and dist(q, alias) <= 1 else None
        if score is not None:
            ranked[row[0]] = min(score, ranked.get(row[0], 99))
    return [BY_CID[cid] for cid in sorted(ranked, key=lambda cid: (ranked[cid], BY_CID[cid][1]))[:limit]]

def display_name(cid, original='', formula=''):
    row = BY_CID.get(str(cid))
    return row[1] if row else 'Composto ' + (formula or 'CID ' + str(cid))
