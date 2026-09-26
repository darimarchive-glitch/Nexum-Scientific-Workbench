#ifndef BundleDir
  #define BundleDir "..\..\dist\Nexum"
#endif
#ifndef AppVersion
  #define AppVersion "7.0.0-preview.1"
#endif
[Setup]
AppId={{863F9039-AC62-4E2D-A848-E14474B9C09E}
AppName=Nexum
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Nexum
DefaultGroupName=Nexum
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=Nexum-{#AppVersion}-windows-x86_64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\build\icons\nexum.ico
UninstallDisplayIcon={app}\Nexum.exe
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Nexum"; Filename: "{app}\Nexum.exe"
Name: "{autodesktop}\Nexum"; Filename: "{app}\Nexum.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"
[Run]
Filename: "{app}\Nexum.exe"; Description: "Abrir Nexum"; Flags: nowait postinstall skipifsilent


