[CmdletBinding()]
param(
    [ValidateSet('Install', 'Run', 'Test', 'Shortcut', 'Doctor')]
    [string]$Action = 'Run',
    [string]$MsysRoot,
    [string]$PythonExe
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $projectRoot
$configPath = Join-Path $projectRoot '.windows-config.json'

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed (exit $LASTEXITCODE)." }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
    if (-not $MsysRoot -and (Test-Path -LiteralPath $configPath)) {
        $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        $MsysRoot = $config.msysRoot
    }
    if (-not $MsysRoot) { $MsysRoot = 'C:\msys64' }
    $MsysRoot = [IO.Path]::GetFullPath($MsysRoot)
    $bash = Join-Path $MsysRoot 'usr\bin\bash.exe'
    $gtkPython = Join-Path $MsysRoot 'ucrt64\bin\python.exe'
    $sciencePython = Join-Path $projectRoot '.venv-science\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $bash)) {
        throw 'Install MSYS2: winget install --exact --id MSYS2.MSYS2. For another location use -MsysRoot.'
    }
    if ($Action -eq 'Install') {
        if (-not (Test-Path -LiteralPath $sciencePython)) {
            if (-not $PythonExe) {
                if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
                    throw 'Install Python 3.12 x64: winget install --exact --id Python.Python.3.12. Then open a new terminal.'
                }
                $PythonExe = & py.exe -3.12 -c 'import sys; print(sys.executable)'
                if ($LASTEXITCODE -ne 0) { throw 'Use -PythonExe with the full path of CPython 3.12 x64.' }
            }
            Invoke-Checked $PythonExe @('-c', 'import sys,struct; assert struct.calcsize(chr(80)) == 8 and sys.version_info[:2] == (3,12)')
            Invoke-Checked $PythonExe @('-m', 'venv', (Join-Path $projectRoot '.venv-science'))
        }
        Invoke-Checked $sciencePython @('-m', 'pip', 'install', '--only-binary=:all:', '-r', 'requirements.txt')
        $env:MSYSTEM = 'UCRT64'
        $env:CHERE_INVOKING = '1'
        # A core update can terminate this shell. Rerun the installer to finish.
        Invoke-Checked $bash @('--login', '-c', 'pacman -Syu --noconfirm')
        Invoke-Checked $bash @('--login', '-c', 'pacman -Syu --noconfirm')
        Invoke-Checked $bash @('--login', '-c', 'pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-libadwaita mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-python-cairo mingw-w64-ucrt-x86_64-python-numpy mingw-w64-ucrt-x86_64-python-scipy mingw-w64-ucrt-x86_64-python-pyopengl mingw-w64-ucrt-x86_64-adwaita-icon-theme')
        @{ msysRoot = $MsysRoot } | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
    }
    if (-not (Test-Path -LiteralPath $gtkPython) -or -not (Test-Path -LiteralPath $sciencePython)) {
        throw 'Dependencies missing. Run install-windows.cmd first.'
    }
    # Process-local configuration; never change the system PATH.
    $prefix = Join-Path $MsysRoot 'ucrt64'
    $env:PATH = "$prefix\bin;$env:PATH"
    $env:GI_TYPELIB_PATH = "$prefix\lib\girepository-1.0"
    $env:GSETTINGS_SCHEMA_DIR = "$prefix\share\glib-2.0\schemas"
    $env:XDG_DATA_DIRS = "$prefix\share"
    $env:GDK_BACKEND = 'win32'
    $env:GDK_DISABLE = 'egl,gles-api'
    $env:PYOPENGL_PLATFORM = 'win32'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONNOUSERSITE = '1'
    Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue
    $env:NEXUM_CHEMISTRY_PYTHON = $sciencePython
    if ($Action -in @('Install', 'Doctor', 'Test')) {
        Invoke-Checked $gtkPython @('-m', 'nexum.windows_check')
    }
    if ($Action -in @('Install', 'Test')) {
        Invoke-Checked $gtkPython @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
        Invoke-Checked $gtkPython @('-m', 'compileall', '-q', 'nexum')
        Write-Host 'Checks passed. Open run-windows.cmd to start Nexum.'
    }
    if ($Action -eq 'Run') { Invoke-Checked $gtkPython @('-m', 'nexum.main') }
    if ($Action -in @('Install', 'Shortcut')) {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Nexum.lnk'))
        $shortcut.TargetPath = Join-Path $projectRoot 'run-windows.cmd'
        $shortcut.WorkingDirectory = $projectRoot
        $shortcut.Description = 'Nexum Scientific Workbench'
        $shortcut.Save()
        Write-Host 'Nexum desktop shortcut created.'
    }
    exit 0
} catch {
    Write-Host "Nexum: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
