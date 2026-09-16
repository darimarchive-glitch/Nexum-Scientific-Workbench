param([Parameter(Mandatory=$true)][string]$MsysRoot,
      [Parameter(Mandatory=$true)][string]$SciencePython)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $root
function Checked([string]$Exe,[string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Build failed: $Exe ($LASTEXITCODE)" }
}
$gtkPython=Join-Path $MsysRoot 'ucrt64\bin\python.exe'
$env:PATH="$(Join-Path $MsysRoot 'ucrt64\bin');$env:PATH"
Checked $SciencePython @('-m','pip','install','CairoSVG==2.9.1','Pillow==12.3.0')
Checked $SciencePython @('packaging/build_icons.py')
Checked $SciencePython @('-m','PyInstaller','--noconfirm','--clean','--onedir','--name','NexumChemistry','--paths','.', '--collect-all','rdkit','--collect-all','gemmi','packaging/worker_entry.py')
Checked $gtkPython @('-m','PyInstaller','--noconfirm','--clean','packaging/windows/desktop.spec')
Copy-Item -Recurse -Force 'dist/NexumChemistry' 'dist/Nexum/chemistry'
Copy-Item 'LICENSE' 'dist/Nexum/LICENSE.txt'
. ./packaging/windows/mesa.ps1
# Verify the frozen bundle with the development interpreter variables removed.
Remove-Item Env:NEXUM_CHEMISTRY_PYTHON,Env:PYTHONPATH,Env:PYTHONHOME -ErrorAction SilentlyContinue
$env:NEXUM_GRAPHICS='auto'
$env:NEXUM_SELF_TEST_LOG=Join-Path $root 'build/self-test.log'
$bundle=Join-Path $root 'dist/Nexum/Nexum.exe'
$check=Start-Process -FilePath $bundle -ArgumentList '--self-test' -Wait -PassThru
if ($check.ExitCode -ne 0) {
    if (Test-Path $env:NEXUM_SELF_TEST_LOG) { Get-Content -Encoding UTF8 $env:NEXUM_SELF_TEST_LOG }
    throw 'Frozen desktop self-test failed.'
}
$iscc=(Get-Command ISCC.exe -ErrorAction SilentlyContinue)
if ($iscc) { $compiler=$iscc.Source } else { $compiler="${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
Checked $compiler @("/DBundleDir=$root\dist\Nexum",'packaging/windows/nexum.iss')

# Install the produced setup and exercise the installed copy without MSYS2
# or Python on PATH, matching an end user's launch environment.
$setupFiles=@(Get-ChildItem -LiteralPath 'dist/installer' -Filter 'Nexum-Setup-*-x64.exe')
if ($setupFiles.Count -ne 1) { throw 'Expected exactly one generated installer.' }
$installDir=Join-Path $root 'build/installed Nexum'
$install=Start-Process -FilePath $setupFiles[0].FullName -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="{0}"' -f $installDir)) -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Installer failed: $($install.ExitCode)" }
$shortcutShell=New-Object -ComObject WScript.Shell
foreach ($shortcutPath in @(
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'Nexum\Nexum.lnk'),
    (Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Nexum.lnk')
)) {
    if (-not (Test-Path -LiteralPath $shortcutPath)) { throw "Shortcut missing: $shortcutPath" }
    $shortcut=$shortcutShell.CreateShortcut($shortcutPath)
    if ($shortcut.TargetPath -ne (Join-Path $installDir 'Nexum.exe')) { throw "Wrong shortcut target: $shortcutPath" }
}
Write-Host 'Start menu and desktop shortcuts: OK'
$buildSearchPath=$env:PATH
try {
    $env:PATH="$env:SystemRoot\System32;$env:SystemRoot"
    $env:NEXUM_GRAPHICS='software'
    $env:NEXUM_SELF_TEST_LOG=Join-Path $root 'build/installed-self-test.log'
    $installed=Start-Process -FilePath (Join-Path $installDir 'Nexum.exe') -WorkingDirectory $installDir -ArgumentList '--self-test' -Wait -PassThru
    if (Test-Path $env:NEXUM_SELF_TEST_LOG) { Get-Content -Encoding UTF8 $env:NEXUM_SELF_TEST_LOG }
    if ($installed.ExitCode -ne 0) { throw "Installed application self-test failed: $($installed.ExitCode)" }
} finally {
    Remove-Item Env:NEXUM_GRAPHICS -ErrorAction SilentlyContinue
    $env:PATH=$buildSearchPath
}


