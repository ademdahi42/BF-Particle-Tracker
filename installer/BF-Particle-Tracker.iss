#define MyAppName "BF-Particle-Tracker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Adem Dahi"
#define MyAppExeName "run_app.bat"

[Setup]
AppId={{8D7B494E-09AF-46DD-B55F-BD3F12E74C5A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=BF-Particle-Tracker-Installer
SetupIconFile=..\assets\app_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\assets\app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "..\main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\gui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\processing.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\run_app.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\documentation\*"; DestDir: "{app}\documentation"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "install.bat"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "uninstall.bat"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "uninstall.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "README_INSTALL.md"; DestDir: "{app}\installer"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\Install or repair dependencies"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\install.ps1"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run_app.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\install.ps1"""; WorkingDir: "{app}"; Description: "Install Python dependencies"; Flags: postinstall runascurrentuser waituntilterminated
Filename: "{app}\run_app.bat"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent
