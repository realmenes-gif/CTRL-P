; Instalador de Ctrl-P (Inno Setup 6). Lo arma GitHub al publicar (publicar_windows.yml) con la carpeta
; Ctrl-P_portable. Se instala SOLO para el usuario (no pide administrador), en %LOCALAPPDATA%\Programs\Ctrl-P,
; con acceso en el menu Inicio, en el escritorio, desinstalador y doble clic en los proyectos .ctrlp.
; Instalado, los proyectos y exportaciones van a Documentos\CTRL-P DOC.
#ifndef MiVersion
  #define MiVersion "1.4"
#endif

[Setup]
AppId={{8F3B2C71-5D4A-4E9B-A1C6-2E7D9B0F4C58}
AppName=Ctrl-P
AppVersion={#MiVersion}
AppVerName=Ctrl-P v{#MiVersion}
AppPublisher=Meneses999
DefaultDirName={localappdata}\Programs\Ctrl-P
DefaultGroupName=Ctrl-P
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=Ctrl-P_v{#MiVersion}_instalador
SetupIconFile=ctrlp.ico
UninstallDisplayIcon={app}\Ctrl-P.exe
UninstallDisplayName=Ctrl-P
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos:"
Name: "ctrlp"; Description: "Abrir los proyectos .ctrlp con doble clic"; GroupDescription: "Proyectos:"

[Files]
; los proyectos nunca se tocan (instalado, van a Documentos\CTRL-P DOC)
Source: "Ctrl-P_portable\*"; DestDir: "{app}"; Excludes: "CTRL-P DOC"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; la version anterior del programa se reemplaza completa (sin restos de librerias viejas)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Ctrl-P"; Filename: "{app}\Ctrl-P.exe"
Name: "{autodesktop}\Ctrl-P"; Filename: "{app}\Ctrl-P.exe"; Tasks: escritorio

[Registry]
Root: HKCU; Subkey: "Software\Classes\.ctrlp"; ValueType: string; ValueData: "CtrlP.Proyecto"; Flags: uninsdeletevalue; Tasks: ctrlp
Root: HKCU; Subkey: "Software\Classes\CtrlP.Proyecto"; ValueType: string; ValueData: "Proyecto Ctrl-P"; Flags: uninsdeletekey; Tasks: ctrlp
Root: HKCU; Subkey: "Software\Classes\CtrlP.Proyecto\DefaultIcon"; ValueType: string; ValueData: "{app}\Ctrl-P.exe,0"; Tasks: ctrlp
Root: HKCU; Subkey: "Software\Classes\CtrlP.Proyecto\shell\open\command"; ValueType: string; ValueData: """{app}\Ctrl-P.exe"" ""%1"""; Tasks: ctrlp

[Run]
Filename: "{app}\Ctrl-P.exe"; Description: "Abrir Ctrl-P"; Flags: nowait postinstall skipifsilent
