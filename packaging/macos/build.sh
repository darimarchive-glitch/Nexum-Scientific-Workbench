#!/usr/bin/env bash
# Run inside the environment.yml environment on a Mac, in a logged-in desktop.
set -euo pipefail
cd "$(dirname "$0")/../.."
[[ $(uname -s) == Darwin ]] || { echo 'A compilação macOS precisa ser executada em um Mac.' >&2; exit 1; }
arch=$(uname -m)
artifact=$(python -m nexum.identity artifact --system macos --arch "$arch")
mkdir -p build/macos dist
python -m unittest discover -s tests -v
python scripts/update_catalog.py --check
python packaging/build_icons.py
conda list --explicit > "build/macos/environment-$arch.lock.txt"
python -m pip freeze > "build/macos/python-$arch.txt"
# GI typelibs refer to library basenames; expose the active native toolchain
# only while resolving dependencies. The frozen self-test below clears it.
DYLD_LIBRARY_PATH="$CONDA_PREFIX/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}" \
  python -m PyInstaller --noconfirm --clean packaging/macos/Nexum.spec
app="$PWD/dist/Nexum.app"
if ! env -u PYTHONPATH -u PYTHONHOME -u GI_TYPELIB_PATH -u DYLD_LIBRARY_PATH -u DYLD_FALLBACK_LIBRARY_PATH -u GTK_DATA_PREFIX -u GSETTINGS_SCHEMA_DIR \
  PATH="/usr/bin:/bin:/usr/sbin:/sbin" NEXUM_SELF_TEST_LOG="$PWD/build/macos/self-test.log" "$app/Contents/MacOS/Nexum" --self-test; then
  cat build/macos/self-test.log
  exit 1
fi
cat build/macos/self-test.log
codesign --verify --deep --strict --verbose=2 "$app"
# An optional Developer ID identity is picked up by the spec. No credentials are stored here.
if [[ -n ${NEXUM_MAC_NOTARY_PROFILE:-} ]]; then
  [[ -n ${NEXUM_MAC_SIGN_IDENTITY:-} ]] || { echo 'Notarização exige identidade Developer ID.' >&2; exit 1; }
  ditto -c -k --keepParent "$app" build/macos/Nexum-notarize.zip
  xcrun notarytool submit build/macos/Nexum-notarize.zip --keychain-profile "$NEXUM_MAC_NOTARY_PROFILE" --wait
  xcrun stapler staple "$app"
  spctl --assess --type execute --verbose=2 "$app"
fi
stage=$(mktemp -d "${TMPDIR:-/tmp}/nexum-dmg.XXXXXX")
trap 'rm -rf "$stage"' EXIT
cp -R "$app" "$stage/Nexum.app"
cp LICENSE "$stage/LICENSE.txt"
ln -s /Applications "$stage/Applications"
hdiutil create -ov -volname Nexum -srcfolder "$stage" -format UDZO "dist/$artifact"
if [[ -n ${NEXUM_MAC_SIGN_IDENTITY:-} ]]; then codesign --sign "$NEXUM_MAC_SIGN_IDENTITY" --timestamp "dist/$artifact"; fi
if [[ -n ${NEXUM_MAC_NOTARY_PROFILE:-} ]]; then
  xcrun notarytool submit "dist/$artifact" --keychain-profile "$NEXUM_MAC_NOTARY_PROFILE" --wait
  xcrun stapler staple "dist/$artifact"
fi
shasum -a 256 "dist/$artifact" > "dist/$artifact.sha256"
echo "Pacote criado: dist/$artifact"
