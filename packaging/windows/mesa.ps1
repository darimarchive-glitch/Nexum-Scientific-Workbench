# Private compatibility renderer. Never alter the Windows system OpenGL DLL.
$ErrorActionPreference='Stop'
$archive=Join-Path $root 'build/mesa3d-26.0.3-release-msvc.7z'
$unpacked=Join-Path $root 'build/mesa3d'
$target=Join-Path $root 'dist/Nexum/mesa'
New-Item -ItemType Directory -Force (Split-Path $archive),$unpacked,$target | Out-Null
Invoke-WebRequest -UseBasicParsing 'https://github.com/pal1000/mesa-dist-win/releases/download/26.0.3/mesa3d-26.0.3-release-msvc.7z' -OutFile $archive
if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLower() -ne 'de1ec45c906164de2c046288a8969e83cf2d51d031dc8dfd1f9371bb31cd6755') {
    throw 'Mesa archive checksum mismatch.'
}
Checked '7z.exe' @('x','-y',("-o{0}" -f $unpacked),$archive)
$driver=@(Get-ChildItem $unpacked -Recurse -Filter opengl32.dll | Where-Object { $_.Directory.Name -eq 'x64' })
if ($driver.Count -ne 1) { throw 'Expected one x64 Mesa OpenGL driver.' }
Copy-Item -Force (Join-Path $driver[0].Directory.FullName '*.dll') $target
# Retain upstream notices and documentation with the redistributed binaries.
Get-ChildItem $unpacked -Recurse -File | Where-Object { $_.Extension -in '.txt','.md','.rst','.html' -or $_.Name -match '^(COPYING|LICENSE|NOTICE)' } | ForEach-Object {
    $relative=$_.FullName.Substring($unpacked.Length).TrimStart('\')
    $destination=Join-Path (Join-Path $target 'notices') $relative
    New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
    Copy-Item $_.FullName $destination
}
if (-not (Test-Path (Join-Path $target 'libgallium_wgl.dll'))) { throw 'Mesa Gallium driver missing.' }
