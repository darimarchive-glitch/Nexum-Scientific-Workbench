"""Check documentation links, source organization and release metadata."""
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
release = meta.find("releases/release")
if meta.findtext("id") != APP_ID:
    errors.append("ID de metadados divergente")
if release is None or release.get("version") != VERSION:
    errors.append("Versão de metadados divergente")
if "-" not in VERSION and release is not None and release.get("type") not in (None, "stable"):
    errors.append("Release estável marcada como desenvolvimento no MetaInfo")
if meta.findtext("metadata_license") != "CC0-1.0":
    errors.append("Licença dos metadados divergente")
if not (meta.findtext("project_license") or "").startswith("LicenseRef-proprietary="):
    errors.append("Licença proprietária ausente no MetaInfo")
if json.loads((folder / (APP_ID + ".json")).read_text())["app-id"] != APP_ID:
    errors.append("ID do manifesto divergente")

readme = (root / "README.md").read_text(encoding="utf-8")
if f"Versão **{VERSION}**" not in readme:
    errors.append("README não anuncia a versão corrente")
if "-" not in VERSION and "prévia de desenvolvimento" in readme.lower():
    errors.append("README estável ainda se apresenta como prévia")

if "NEXUM PROPRIETARY LICENSE" not in (root / "LICENSE").read_text(encoding="utf-8"):
    errors.append("LICENSE proprietária do Nexum não encontrada")

release_notes = root / "docs/releases" / f"{VERSION}.md"
if not release_notes.exists():
    errors.append(f"Notas da versão ausentes: {release_notes.relative_to(root)}")

iss = (root / "packaging/windows/nexum.iss").read_text(encoding="utf-8")
if f'#define AppVersion "{VERSION}"' not in iss:
    errors.append("Versão fallback do instalador Windows divergente")
if "LicenseFile=" not in iss:
    errors.append("Instalador Windows não apresenta a licença")

if (root / ".github/workflows/publish-release.yml").exists():
    errors.append("Publicador histórico duplicado não deve acompanhar o projeto")

if (root / "docs/logo-nexum.svg").read_bytes() != (root / "nexum/assets/logo.svg").read_bytes():
    errors.append("Logo divergente")

if errors:
    raise SystemExit("\n".join(errors))
print("Links, identidade, versão, licença, release, organização e logo: OK")
