"""Portable projects with atomic writes, original data and reversible editing."""

import copy
import hashlib
import json
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 48 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def fresh(title="Novo projeto"):
    return dict(
        schema=7,
        id=uuid.uuid4().hex,
        title=title,
        created=now(),
        modified=now(),
        notes="Pergunta científica:\n\nHipóteses e condições:\n\nOrigem dos dados e unidades:\n\nInterpretação e limitações:\n",
        datasets=[],
        results=[],
        assignments=[],
        scenes=[],
        events=[],
        graph={"atoms": [], "bonds": []},
        molecule=None,
        pipeline=[],
        design=None,
        process=[],
        investigation=None,
        workspace=None,
    )


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != 7:
        raise ValueError("Este arquivo não é um projeto Nexum 7.")
    for key in ("datasets", "results", "assignments", "scenes", "events"):
        if not isinstance(data.get(key), list):
            raise ValueError("Projeto inválido: " + key)
    if not isinstance(data.get("title"), str) or len(data["title"]) > 500:
        raise ValueError("Título inválido.")
    if len(json.dumps(data, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("Projeto excede 48 MiB; divida-o em projetos menores.")
    from .datasets import validate_dataset

    ids = set()
    for dataset in data["datasets"]:
        validate_dataset(dataset)
        if dataset["id"] in ids:
            raise ValueError("Identificador de série duplicado.")
        ids.add(dataset["id"])
    from .validation import nested

    nested(data)
    return data


def write_project(path, data):
    validate(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
    fd, temp = tempfile.mkstemp(prefix=".nexum-", dir=path.parent)
    try:
        with os.fdopen(fd, "w+b") as f:
            with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("project.json", payload)
                z.writestr("SHA256.txt", hashlib.sha256(payload).hexdigest())
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_project(path):
    if Path(path).stat().st_size > MAX_BYTES:
        raise ValueError("Arquivo muito grande.")
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) != 2 or set(z.namelist()) != {
            "project.json",
            "SHA256.txt",
        }:
            raise ValueError("Conteúdo de projeto inválido.")
        if (
            z.getinfo("project.json").file_size > MAX_BYTES
            or z.getinfo("SHA256.txt").file_size > 128
        ):
            raise ValueError("Projeto descompactado muito grande.")
        payload = z.read("project.json")
        if hashlib.sha256(payload).hexdigest() != z.read("SHA256.txt").decode():
            raise ValueError("O arquivo foi corrompido (SHA-256 divergente).")
    return validate(json.loads(payload))


class Project:
    def __init__(self, data=None):
        self.data = copy.deepcopy(validate(data) if data is not None else fresh())
        self.undo_stack = []
        self.redo_stack = []
        self.revision = 0

    def edit(self, label, change):
        before = copy.deepcopy(self.data)
        try:
            change(self.data)
            self.data["modified"] = now()
            self.data["events"].append({"at": now(), "action": label})
            validate(self.data)
        except Exception:
            self.data = before
            raise
        self.undo_stack.append(before)
        self.undo_stack = self.undo_stack[-15:]
        # Bound checkpoint memory for projects containing imported data or surfaces.
        while (
            len(self.undo_stack) > 1
            and sum(len(json.dumps(d).encode()) for d in self.undo_stack)
            > 64 * 1024 * 1024
        ):
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.revision += 1

    def undo(self):
        if not self.undo_stack:
            return False
        self.redo_stack.append(copy.deepcopy(self.data))
        self.data = self.undo_stack.pop()
        self.data["events"].append({"at": now(), "action": "Desfazer alteração"})
        self.revision += 1
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        self.undo_stack.append(copy.deepcopy(self.data))
        self.data = self.redo_stack.pop()
        self.data["events"].append({"at": now(), "action": "Refazer alteração"})
        self.revision += 1
        return True

    def result(self, kind, payload, source_ids=(), parameters=None):
        row = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "at": now(),
            "payload": payload,
            "sources": list(source_ids),
            "parameters": parameters or {},
        }
        self.edit("Resultado: " + kind, lambda d: d["results"].append(row))
        return row
