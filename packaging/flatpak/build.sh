#!/usr/bin/env bash
# Independent Flatpak bundle; this is not a Flathub submission manifest.
set -euo pipefail
cd "$(dirname "$0")/../.."
app_id=$(python3 -m nexum.identity id)
arch=$(flatpak --default-arch)
artifact=$(python3 -m nexum.identity artifact --system linux --arch "$arch")
runtime_version=$(python3 -c 'import json; print(json.load(open("packaging/flatpak/io.github.nexum.ScientificWorkbench.json"))["runtime-version"])')
sdk=org.gnome.Sdk//$runtime_version
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub "org.gnome.Platform//$runtime_version" "$sdk"
mkdir -p build dist
# Regenerate the dedicated staging tree so old wheels cannot enter a new bundle.
python3 -c 'import shutil; shutil.rmtree("build/flatpak-input",ignore_errors=True)'
mkdir -p build/flatpak-input/wheels
cp -R nexum packaging LICENSE requirements.txt build/flatpak-input/
# Resolve wheels with the SDK's own Python/ABI; the builder then runs offline.
flatpak run --filesystem="$PWD/build/flatpak-input" --share=network --command=sh "$sdk" -c \
    'python3 -m ensurepip --user; python3 -m pip download --only-binary=:all: --dest "$1/wheels" -r "$1/requirements.txt"' sh "$PWD/build/flatpak-input"
# Record the exact inputs for the build artifact. No token or private URL is embedded.
(cd build/flatpak-input/wheels && sha256sum ./*.whl) > build/flatpak-input/WHEELS.sha256
flatpak-builder --user --force-clean --repo=build/flatpak-repo build/flatpak-app packaging/flatpak/io.github.nexum.ScientificWorkbench.json
flatpak build-bundle build/flatpak-repo "dist/$artifact" "$app_id" --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo


cp packaging/flatpak/repair-shortcut.sh dist/nexum-repair-shortcut.sh
