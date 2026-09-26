"""Opt-in local Python extensions, executed in a separate interpreter.

This is process isolation for responsiveness, NOT a security sandbox. Only run
code you trust. Projects cannot automatically execute or enable extensions.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def inspect(path):
    path = Path(path).resolve()
    if path.suffix != ".py" or path.stat().st_size > 256000:
        raise ValueError("Selecione uma extensão .py de até 256 KB.")
    raw = path.read_bytes()
    source = raw.decode("utf-8")
    compile(source, str(path), "exec")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "source": source,
    }


def run(path, payload, accepted_hash, interpreter=None):
    info = inspect(path)
    if info["sha256"] != accepted_hash:
        raise ValueError("A extensão mudou; revise e autorize novamente.")
    if interpreter is None:
        if getattr(sys, "frozen", False):
            raise ValueError(
                "Extensões requerem um Python externo selecionado; o executável do aplicativo não é um interpretador Python."
            )
        interpreter = sys.executable
    interpreter = Path(interpreter).resolve()
    if not interpreter.is_file():
        raise ValueError("Interpretador não encontrado.")
    launcher = """import json,runpy,sys
module=runpy.run_path(sys.argv[1],run_name="nexum_extension")
result=module["run"](json.loads(open(sys.argv[2],encoding="utf-8").read()))
text=json.dumps(result,ensure_ascii=False,allow_nan=False)
if len(text.encode())>2000000:raise ValueError("Resultado da extensão excede 2 MB")
open(sys.argv[3],"w",encoding="utf-8").write(text)
"""
    with tempfile.TemporaryDirectory(prefix="nexum-extension-") as folder:
        root = Path(folder)
        script = root / "extension.py"
        script.write_text(info["source"], encoding="utf-8")
        inp = root / "input.json"
        out = root / "output.json"
        inp.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
        env = os.environ.copy()
        for k in ("PYTHONHOME", "PYTHONPATH"):
            env.pop(k, None)
        # User-authorized code; suppress unbounded console output, read bounded result.
        try:
            result = subprocess.run(
                [
                    str(interpreter),
                    "-I",
                    "-c",
                    launcher,
                    str(script),
                    str(inp),
                    str(out),
                ],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
                creationflags=0x08000000 if sys.platform == "win32" else 0,
            )
        except subprocess.TimeoutExpired:
            raise ValueError("Extensão excedeu 30 segundos.")
        if result.returncode or not out.is_file():
            raise ValueError(
                "A extensão falhou; confira a função run(payload) em seu ambiente Python."
            )
        if out.stat().st_size > 2_000_000:
            raise ValueError("Resultado muito grande.")
        data = json.loads(out.read_text())
        json.dumps(data, allow_nan=False)
        return {
            "extension_sha256": info["sha256"],
            "result": data,
            "method": "Extensão Python local autorizada pelo usuário; resultado não auditado pelo Nexum.",
        }
