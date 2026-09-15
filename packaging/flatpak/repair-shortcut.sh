#!/usr/bin/env bash
# Run on the Linux host, outside the Flatpak sandbox. No administrator access.
set -euo pipefail
app_id=io.github.nexum.ScientificWorkbench
command -v flatpak >/dev/null || { echo 'Flatpak não encontrado.' >&2; exit 1; }
location=''
for scope in --user --system; do
    if location=$(flatpak info "$scope" --show-location "$app_id" 2>/dev/null); then break; fi
    location=''
done
[[ -n "$location" ]] || { echo 'Instale o Flatpak do Nexum antes de reparar o atalho.' >&2; exit 1; }
source_desktop="$location/export/share/applications/$app_id.desktop"
source_icon="$location/files/share/icons/hicolor/scalable/apps/$app_id.svg"
[[ -f "$source_desktop" && -f "$source_icon" ]] || {
    echo 'A instalação não contém o atalho ou o logo esperado. Reinstale o pacote atualizado.' >&2
    exit 1
}
data_root="${XDG_DATA_HOME:-$HOME/.local/share}"
applications="$data_root/applications"
icons="$data_root/icons/hicolor/scalable/apps"
mkdir -p "$applications" "$icons"
target="$applications/$app_id.desktop"
if [[ -e "$target" ]] && ! cmp -s "$source_desktop" "$target"; then
    if [[ ! -e "$target.nexum-backup" ]]; then cp -p -- "$target" "$target.nexum-backup"; fi
fi
# Keep the command rewritten by Flatpak, including the installed branch/architecture.
install -m644 "$source_desktop" "$target"
install -m644 "$source_icon" "$icons/$app_id.svg"
if command -v update-desktop-database >/dev/null; then update-desktop-database "$applications"; fi
if command -v gtk-update-icon-cache >/dev/null; then gtk-update-icon-cache -f -t "$data_root/icons/hicolor" >/dev/null 2>&1 || true; fi
echo 'Atalho do Nexum atualizado. Procure Nexum no menu de aplicativos.'
echo 'Se o menu ainda não atualizar, saia da sessão e entre novamente. Você pode fixar o Nexum nos favoritos.'
