"""Check local documentation links, source organization and release metadata."""

from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from nexum.identity import APP_ID, VERSION

errors = []
for path in root.rglob("*.md"):
    if any(part in ("build", "dist", ".venv") for part in path.relative_to(root).parts):
        continue
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        target = target.split("#")[0]
        if target and not (path.parent / target).exists():
            errors.append(f"{path.relative_to(root)}: link ausente {target}")
folder = root / "packaging/flatpak"
meta = ET.parse(folder / (APP_ID + ".metainfo.xml")).getroot()
if meta.findtext("id") != APP_ID:
    errors.append("ID de metadados divergente")
if meta.find("releases/release").get("version") != VERSION:
    errors.append("Versão de metadados divergente")
if json.loads((folder / (APP_ID + ".json")).read_text())["app-id"] != APP_ID:
    errors.append("ID do manifesto divergente")
if (root / ".github/workflows/publish-release.yml").exists():
    errors.append("Publicador histórico não deve acompanhar esta prévia")
if (root / "docs/logo-nexum.svg").read_bytes() != (
    root / "nexum/assets/logo.svg"
).read_bytes():
    errors.append("Logo divergente")
if errors:
    raise SystemExit("\n".join(errors))
print("Links locais, identidade, versão, organização e logo: OK")
