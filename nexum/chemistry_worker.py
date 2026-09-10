"""JSON boundary between MSYS2 GTK and CPython's gemmi/RDKit wheels.

Only three named operations are supported. No shell, pickle or network service.
Linux and regular CPython continue to call the existing implementations directly.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys


def configured():
    return bool(os.environ.get("NEXUM_CHEMISTRY_PYTHON"))


def call(operation, *args):
    from nexum.core.structures import Atom, Molecule

    env = os.environ.copy()
    executable = env.pop("NEXUM_CHEMISTRY_PYTHON")
    # Do not inject the MinGW interpreter's Python modules into CPython.
    for key in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(key, None)
    try:
        result = subprocess.run(
            [executable, "-I", str(Path(__file__).resolve())],
            input=json.dumps({"operation": operation, "args": args}, ensure_ascii=False),
            capture_output=True, text=True, encoding="utf-8", env=env,
            timeout=180, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Não foi possível executar o motor químico. Execute install-windows.cmd novamente.") from exc
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError("O motor químico não retornou uma resposta válida.") from exc
    if result.returncode or "error" in response:
        raise RuntimeError(response.get("error", "Falha no motor químico."))
    response["atoms"] = [Atom(**atom) for atom in response["atoms"]]
    response["bonds"] = [tuple(bond) for bond in response["bonds"]]
    return Molecule(**response)


def main():
    # -I disables cwd imports; use only the source tree containing this worker.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ.pop("NEXUM_CHEMISTRY_PYTHON", None)
    from nexum.core import structures
    operations = {
        "mmcif": structures.parse_mmcif,
        "smiles": structures._rdkit_conformer_from_smiles,
        "molblock": structures._rdkit_conformer_from_molblock,
    }
    try:
        request = json.load(sys.stdin)
        molecule = operations[request["operation"]](*request["args"])
        print(json.dumps(asdict(molecule), ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
