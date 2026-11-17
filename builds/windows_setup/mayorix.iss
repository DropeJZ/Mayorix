; Inno Setup script para Mayorix Desktop
; Genera Mayorix_Setup.exe en la raíz del proyecto.

#define MyAppName "Mayorix"
#define MyAppVersion "2.1.5"
#define MyAppPublisher "DropeTech"
#define MyAppExeName "Mayorix.exe"

[Setup]
AppId={{A3F5C2D1-7E4B-4C9A-9B2D-5E8F1A6C3D70}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userpf}\Mayorix
DefaultGroupName=Mayorix
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\..
OutputBaseFilename=Mayorix_Setup
SetupIconFile=..\..\src\Mayorix_Desktop\assets\mayorix.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\..\Mayorix.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\config\mongo_uri.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Mayorix"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Mayorix"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar Mayorix"; Flags: nowait postinstall skipifsilent
