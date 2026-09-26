"""Editable molecular graphs and quantitative rigid alignment."""

import copy
from dataclasses import asdict
import numpy as np
from nexum.core.structures import Atom, Molecule
from nexum.core.molecular_analysis import molecule_from_dict


def chemistry(operation, *args):
    from nexum import chemistry_worker

    if chemistry_worker.configured():
        return chemistry_worker.call(operation, *args)
    return {"builder": build, "conformers": conformers, "smiles_graph": smiles_graph}[
        operation
    ](*args)


def rd_molecule(graph):
    from rdkit import Chem
    from .validation import graph as validate_graph

    validate_graph(graph)
    atoms = graph["atoms"]
    bonds = graph["bonds"]
    if not 1 <= len(atoms) <= 200:
        raise ValueError(
            "O editor aceita 1–200 átomos; use importação para estruturas maiores."
        )
    rw = Chem.RWMol()
    for a in atoms:
        if not np.isfinite([a.get("x", 0), a.get("y", 0)]).all():
            raise ValueError("Posição inválida.")
        atom = Chem.Atom(a["element"])
        atom.SetFormalCharge(int(a.get("charge", 0)))
        atom.SetNumExplicitHs(int(a.get("explicit_h", 0)))
        atom.SetNoImplicit(bool(a.get("no_implicit", False)))
        rw.AddAtom(atom)
    orders = {
        1: Chem.BondType.SINGLE,
        2: Chem.BondType.DOUBLE,
        3: Chem.BondType.TRIPLE,
        1.5: Chem.BondType.AROMATIC,
    }
    for i, j, order in bonds:
        if (
            type(i) is not int
            or type(j) is not int
            or not 0 <= i < len(atoms)
            or not 0 <= j < len(atoms)
            or i == j
            or order not in orders
        ):
            raise ValueError("Ligação inválida.")
        if rw.GetBondBetweenAtoms(i, j):
            raise ValueError("Ligação duplicada.")
        rw.AddBond(i, j, orders[order])
    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        raise ValueError(
            "Valência ou aromaticidade inválida; confira ligações e cargas formais."
        ) from exc
    return mol


def graph_from_rd(mol):
    from rdkit.Chem import rdDepictor
    from rdkit import Chem

    mol = Chem.Mol(mol)
    rdDepictor.Compute2DCoords(mol)
    c = mol.GetConformer()
    return {
        "atoms": [
            {
                "element": a.GetSymbol(),
                "charge": a.GetFormalCharge(),
                "explicit_h": a.GetNumExplicitHs(),
                "no_implicit": a.GetNoImplicit(),
                "x": float(c.GetAtomPosition(a.GetIdx()).x),
                "y": float(c.GetAtomPosition(a.GetIdx()).y),
            }
            for a in mol.GetAtoms()
        ],
        "bonds": [
            [b.GetBeginAtomIdx(), b.GetEndAtomIdx(), b.GetBondTypeAsDouble()]
            for b in mol.GetBonds()
        ],
    }


def smiles_graph(smiles):
    from rdkit import Chem

    if len(smiles) > 4000:
        raise ValueError("SMILES muito longo.")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("SMILES inválido.")
    if any(
        a.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED
        or a.GetIsotope()
        or a.GetNumRadicalElectrons()
        for a in mol.GetAtoms()
    ) or any(b.GetStereo() != Chem.BondStereo.STEREONONE for b in mol.GetBonds()):
        raise ValueError(
            "Este editor não preserva estereoquímica, isótopos ou radicais explícitos. Use a importação de estruturas para esse caso."
        )
    if mol.GetNumAtoms() > 200:
        raise ValueError("Editor limitado a 200 átomos.")
    return graph_from_rd(mol)


def _embedded(graph, count, seed):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    base = rd_molecule(graph)
    if len(Chem.GetMolFrags(base)) != 1:
        raise ValueError(
            "Gere uma espécie conectada por vez; a posição relativa de fragmentos separados não é definida por este editor."
        )
    mol = Chem.AddHs(base)
    params = AllChem.ETKDGv3()
    params.randomSeed = int(seed)
    params.numThreads = 1
    ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=count, params=params))
    if not ids:
        raise ValueError("Não foi possível gerar uma geometria 3D.")
    if AllChem.MMFFHasAllMoleculeParams(mol):
        method = "MMFF94"
        props = AllChem.MMFFGetMoleculeProperties(mol)
        make = lambda cid: AllChem.MMFFGetMoleculeForceField(mol, props, confId=cid)
    elif AllChem.UFFHasAllMoleculeParams(mol):
        method = "UFF"
        make = lambda cid: AllChem.UFFGetMoleculeForceField(mol, confId=cid)
    else:
        raise ValueError(
            "Os campos de força MMFF94/UFF não têm parâmetros para esta estrutura."
        )
    results = []
    for cid in ids:
        ff = make(cid)
        status = ff.Minimize(maxIts=1000)
        energy = float(ff.CalcEnergy())
        results.append((energy, int(cid), int(status)))
    return mol, method, sorted(results)


def _result(mol, method, record, graph, name):
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors, rdDepictor

    energy, cid, status = record
    c = mol.GetConformer(cid)
    atoms = [
        Atom(
            a.GetSymbol(),
            float(c.GetAtomPosition(a.GetIdx()).x),
            float(c.GetAtomPosition(a.GetIdx()).y),
            float(c.GetAtomPosition(a.GetIdx()).z),
            name=f"{a.GetSymbol()}{a.GetIdx() + 1}",
        )
        for a in mol.GetAtoms()
    ]
    bond_mol = Chem.Mol(mol)
    Chem.Kekulize(bond_mol, clearAromaticFlags=True)
    bonds = [
        (b.GetBeginAtomIdx(), b.GetEndAtomIdx(), int(b.GetBondTypeAsDouble()))
        for b in bond_mol.GetBonds()
    ]
    diagram = Chem.Mol(mol)
    rdDepictor.Compute2DCoords(diagram)
    coords = diagram.GetConformer()
    metadata = {
        "coordinates_2d": [
            [coords.GetAtomPosition(i).x, coords.GetAtomPosition(i).y]
            for i in range(len(atoms))
        ],
        "builder_graph": copy.deepcopy(graph),
        "energy_kcal_mol": energy,
        "optimization_converged": status == 0,
        "geometry_method": method + " / ETKDGv3; campo de força, não cálculo quântico",
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "canonical_smiles": Chem.MolToSmiles(Chem.RemoveHs(mol)),
    }
    molecule = Molecule(
        name,
        atoms,
        bonds,
        "Construído no Nexum",
        "",
        metadata["geometry_method"],
        metadata,
    )
    return asdict(molecule)


def build(graph, name="Molécula construída", seed=42):
    mol, method, records = _embedded(graph, 1, seed)
    return {
        "molecule": _result(mol, method, records[0], graph, name),
        "graph": graph_from_rd(rd_molecule(graph)),
    }


def conformers(graph, count=6, seed=42):
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Gere entre 1 e 20 conformeros.")
    mol, method, records = _embedded(graph, count, seed)
    lowest = records[0][0]
    return [
        {
            "molecule": _result(mol, method, r, graph, f"Conformero {i + 1}"),
            "relative_energy_kcal_mol": float(r[0] - lowest),
        }
        for i, r in enumerate(records)
    ]


def align(reference, moving, pairs=None):
    ref = molecule_from_dict(reference)
    mov = molecule_from_dict(moving)
    if pairs is None:
        if [a.element for a in ref.atoms] != [a.element for a in mov.atoms]:
            raise ValueError(
                "Correspondência automática exige a mesma ordem de elementos. Informe pares de átomos para outras estruturas."
            )
        pairs = [(i, i) for i, a in enumerate(ref.atoms) if a.element != "H"]
    if len(pairs) < 3:
        raise ValueError("Selecione pelo menos três correspondências.")
    if len({p[0] for p in pairs}) != len(pairs) or len({p[1] for p in pairs}) != len(
        pairs
    ):
        raise ValueError("Correspondências repetidas.")
    if any(
        not 0 <= i < len(ref.atoms) or not 0 <= j < len(mov.atoms) for i, j in pairs
    ):
        raise ValueError("Índice inválido.")
    if any(ref.atoms[i].element != mov.atoms[j].element for i, j in pairs):
        raise ValueError("Mapeie átomos do mesmo elemento.")
    a = np.array(
        [[ref.atoms[i].x, ref.atoms[i].y, ref.atoms[i].z] for i, j in pairs], float
    )
    b = np.array(
        [[mov.atoms[j].x, mov.atoms[j].y, mov.atoms[j].z] for i, j in pairs], float
    )
    ac = a.mean(axis=0)
    bc = b.mean(axis=0)
    if np.linalg.matrix_rank(a - ac) < 2 or np.linalg.matrix_rank(b - bc) < 2:
        raise ValueError(
            "Átomos colineares não definem uma orientação única; selecione outra correspondência."
        )
    u, _, vt = np.linalg.svd((b - bc).T @ (a - ac))
    correction = np.eye(3)
    correction[-1, -1] = np.linalg.det(u @ vt)
    rotation = u @ correction @ vt
    positions = np.array([[atom.x, atom.y, atom.z] for atom in mov.atoms], float)
    aligned = (positions - bc) @ rotation + ac
    for atom, p in zip(mov.atoms, aligned):
        atom.x, atom.y, atom.z = map(float, p)
    distances = np.linalg.norm((b - bc) @ rotation + ac - a, axis=1)
    return {
        "molecule": asdict(mov),
        "rmsd_angstrom": float(np.sqrt(np.mean(distances**2))),
        "deviations_angstrom": distances.tolist(),
        "pairs": [list(p) for p in pairs],
        "method": "Kabsch sem reflexão; ajuste rígido, correspondência por índice ou pares explícitos. Não faz alinhamento de sequência.",
    }


def assign(dataset, molecule, lower, upper, indices, note=""):
    from .project import fingerprint, now

    x = np.array(dataset["x"])
    y = np.array(dataset["y"])
    lower = float(lower)
    upper = float(upper)
    ids = list(dict.fromkeys(int(i) for i in indices))
    if not ids or any(i < 0 or i >= len(molecule["atoms"]) for i in ids):
        raise ValueError("Selecione átomos válidos.")
    if not x[0] <= lower < upper <= x[-1]:
        raise ValueError("Faixa fora do espectro.")
    xx = np.r_[lower, x[(x > lower) & (x < upper)], upper]
    yy = np.interp(xx, x, y)
    return {
        "dataset_id": dataset["id"],
        "molecule_sha256": fingerprint(molecule),
        "range": [lower, upper],
        "atom_indices": ids,
        "note": note,
        "at": now(),
        "method": "Atribuição manual; integração trapezoidal, sem previsão automática",
        "area": float(np.sum(np.diff(xx) * (yy[:-1] + yy[1:]) / 2)),
    }
