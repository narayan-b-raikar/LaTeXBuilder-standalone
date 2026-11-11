; Inno Setup 6 script for LaTeX Builder (stand-alone).
; Build the program first (build_exe.bat), then compile this file (build_installer.bat).

#define MyAppName "LaTeX Builder"
#define MyAppVersion "1.6.0"
#define MyAppExeName "LaTeXBuilder.exe"

[Setup]
AppId={{8E5B2C4A-6F31-4D7E-9B0A-3C1D5E7F2A64}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=LaTeX Builder
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=LaTeXBuilder-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Installs for the current user without administrator rights unless the user chooses all users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "assocproj"; Description: "Open LaTeX Builder project files (.texproj) with LaTeX Builder"; GroupDescription: "File types:"
Name: "assoctex"; Description: "Add LaTeX Builder to the Open with list for .tex files"; GroupDescription: "File types:"

[Files]
Source: "dist\LaTeXBuilder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.texproj"; ValueType: string; ValueName: ""; ValueData: "LaTeXBuilder.Project"; Flags: uninsdeletevalue; Tasks: assocproj
Root: HKA; Subkey: "Software\Classes\LaTeXBuilder.Project"; ValueType: string; ValueName: ""; ValueData: "LaTeX Builder project"; Flags: uninsdeletekey; Tasks: assocproj
Root: HKA; Subkey: "Software\Classes\LaTeXBuilder.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assocproj
Root: HKA; Subkey: "Software\Classes\.tex\OpenWithProgids"; ValueType: string; ValueName: "LaTeXBuilder.Tex"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoctex
Root: HKA; Subkey: "Software\Classes\LaTeXBuilder.Tex"; ValueType: string; ValueName: ""; ValueData: "LaTeX document"; Flags: uninsdeletekey; Tasks: assoctex
Root: HKA; Subkey: "Software\Classes\LaTeXBuilder.Tex\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assoctex

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function ToolInstalled(const ExeName: String; const Extra1, Extra2, Extra3: String): Boolean;
begin
  Result := (FileSearch(ExeName, GetEnv('PATH')) <> '')
    or ((Extra1 <> '') and FileExists(Extra1))
    or ((Extra2 <> '') and FileExists(Extra2))
    or ((Extra3 <> '') and FileExists(Extra3));
end;

procedure CurPageChanged(CurPageID: Integer);
var
  Note: String;
begin
  if CurPageID = wpFinished then
  begin
    Note := '';
    if not ToolInstalled('pdflatex.exe',
        ExpandConstant('{localappdata}\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'),
        ExpandConstant('{commonpf}\MiKTeX\miktex\bin\x64\pdflatex.exe'),
        ExpandConstant('{commonpf32}\MiKTeX\miktex\bin\pdflatex.exe')) then
      Note := Note + #13#10#13#10 + 'MiKTeX was not found. Install MiKTeX from https://miktex.org to build PDF files and to use Indian languages.';
    if not ToolInstalled('pandoc.exe',
        ExpandConstant('{localappdata}\Pandoc\pandoc.exe'),
        ExpandConstant('{commonpf}\Pandoc\pandoc.exe'),
        '') then
      Note := Note + #13#10#13#10 + 'Pandoc was not found. Install Pandoc from https://pandoc.org to make Word, HTML and other formats.';
    if Note <> '' then
      WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + Note;
  end;
end;
