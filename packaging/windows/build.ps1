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
Checked $SciencePython @('-m','PyInstaller','--noconfirm','--clean','--onedir','--name','NexumChemistry','--paths','.', '--collect-all','rdkit','--collect-all','gemmi','packaging/worker_entry.py')
Checked $gtkPython @('-m','PyInstaller','--noconfirm','--clean','packaging/windows/desktop.spec')
Copy-Item -Recurse -Force 'dist/NexumChemistry' 'dist/Nexum/chemistry'
Copy-Item 'LICENSE' 'dist/Nexum/LICENSE.txt'
# Verify the frozen bundle with the development interpreter variables removed.
Remove-Item Env:NEXUM_CHEMISTRY_PYTHON,Env:PYTHONPATH,Env:PYTHONHOME -ErrorAction SilentlyContinue
$bundle=Join-Path $root 'dist/Nexum/Nexum.exe'
$check=Start-Process -FilePath $bundle -ArgumentList '--self-test' -Wait -PassThru
if ($check.ExitCode -ne 0) { throw 'Frozen desktop self-test failed.' }
$iscc=(Get-Command ISCC.exe -ErrorAction SilentlyContinue)
if ($iscc) { $compiler=$iscc.Source } else { $compiler="${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
Checked $compiler @("/DBundleDir=$root\dist\Nexum",'packaging/windows/nexum.iss')
