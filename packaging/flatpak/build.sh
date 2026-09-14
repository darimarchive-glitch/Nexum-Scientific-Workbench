#!/usr/bin/env bash
# Build on Linux x86_64 with Flatpak and flatpak-builder installed.
set -euo pipefail
cd "$(dirname "$0")/../.."
app_id=io.github.nexum.ScientificWorkbench
sdk=org.gnome.Sdk//49
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub org.gnome.Platform//49 "$sdk"
mkdir -p build/flatpak-input/wheels dist
cp -R nexum packaging LICENSE requirements.txt build/flatpak-input/
# Resolve wheels with the SDK's own Python/ABI; the builder then runs offline.
flatpak run --filesystem="$PWD/build/flatpak-input" --share=network --command=sh "$sdk" -c \
    'python3 -m ensurepip --user; python3 -m pip download --only-binary=:all: --dest "$1/wheels" -r "$1/requirements.txt"' sh "$PWD/build/flatpak-input"
# Record the exact inputs for the build artifact. No token or private URL is embedded.
(cd build/flatpak-input/wheels && sha256sum ./*.whl) > build/flatpak-input/WHEELS.sha256
flatpak-builder --user --force-clean --repo=build/flatpak-repo build/flatpak-app packaging/flatpak/io.github.nexum.ScientificWorkbench.json
flatpak build-bundle build/flatpak-repo dist/Nexum-x86_64.flatpak "$app_id" --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo
