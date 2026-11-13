; The Windows installer of Tarjuman (Inno Setup 6).
;   1) powershell -ExecutionPolicy Bypass -File installer\build.ps1
;   2) iscc /DAppVersion=3.0.0 installer\tarjuman.iss
; Output: build\windows\Tarjuman-Setup-<version>.exe
;
; It asks for administrator rights (the usual Windows prompt) and installs into Program Files for
; everyone on the computer; /CURRENTUSER on the command line installs for one user without the
; prompt. It never touches the firewall, and
; keeps the user's data (%LOCALAPPDATA%\Tarjuman) apart from the program so updates don't lose it.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0B5E0C-5D0E-4E0A-9C61-7A1F3D2E8B14}
AppName=Tarjuman
AppVersion={#AppVersion}
AppPublisher=Tarjuman
AppPublisherURL=https://github.com/MohamedElnagar94/tarjuman
AppSupportURL=https://github.com/MohamedElnagar94/tarjuman/issues
DefaultDirName={autopf}\Tarjuman
DefaultGroupName=Tarjuman
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\windows
OutputBaseFilename=Tarjuman-Setup-{#AppVersion}
SetupIconFile=..\assets\brand\icon.ico
UninstallDisplayIcon={app}\assets\brand\icon.ico
LicenseFile=..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[CustomMessages]
english.DesktopIcon=Create a desktop shortcut
arabic.DesktopIcon=أنشئ اختصارًا على سطح المكتب
english.Launch=Start Tarjuman
arabic.Launch=شغّل ترجمان
english.KeepData=Do you also want to delete your Tarjuman data (videos, subtitles, saved words and settings)?%n%n%1%n%nChoose No to keep it for a later install.
arabic.KeepData=هل تريد حذف بيانات ترجمان أيضًا (الفيديوهات والترجمات والكلمات المحفوظة والإعدادات)؟%n%n%1%n%nاختر «لا» للاحتفاظ بها لتثبيت لاحق.
english.ExtensionFolder=Browser extension folder
arabic.ExtensionFolder=مجلد إضافة المتصفح

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"

[Files]
Source: "..\build\windows\app\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; Packages and code of the version being replaced: a file dropped by a newer version must not linger.
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\backend"
Type: filesandordirs; Name: "{app}\frontend"
Type: filesandordirs; Name: "{app}\extension"
Type: filesandordirs; Name: "{app}\shared"

[Icons]
; pythonw.exe: Tarjuman opens in a window of its own, with no console window behind it.
; A shortcut name is a file name: no quotes or other characters Windows forbids in it.
Name: "{group}\Tarjuman"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m tarjuman app"; WorkingDir: "{app}"; IconFilename: "{app}\assets\brand\icon.ico"; AppUserModelID: "Tarjuman.Desktop"
Name: "{group}\{cm:ExtensionFolder}"; Filename: "{app}\extension"
Name: "{autodesktop}\Tarjuman"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m tarjuman app"; WorkingDir: "{app}"; IconFilename: "{app}\assets\brand\icon.ico"; AppUserModelID: "Tarjuman.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: "-m tarjuman app"; WorkingDir: "{app}"; Description: "{cm:Launch}"; Flags: postinstall nowait skipifsilent runasoriginaluser
; An update started from the app runs silently: start the app again when it is done.
Filename: "{app}\python\pythonw.exe"; Parameters: "-m tarjuman app"; WorkingDir: "{app}"; Flags: nowait runasoriginaluser; Check: WizardSilent

[Registry]
; "Start with Windows" (Settings → Desktop) is a value under Run that the app itself adds or removes.
; Uninstalling removes it, for the user who uninstalls; Setup never creates it.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Tarjuman"; Flags: uninsdeletevalue

[UninstallDelete]
; What Python wrote next to the program while running (compiled files, updated packages).
Type: filesandordirs; Name: "{app}"

[Code]
{ Before files are replaced, Tarjuman (window, engine, notification-area icon) is closed by itself,
  so Windows doesn't list "Python" as an application in the way. First it is asked to quit, which
  lets it save its caches; a version too old to understand that, or one that doesn't answer, is then
  stopped. Only Python processes running from this program folder are touched. }
procedure CloseTarjuman(const Dir: String);
var
  Code: Integer;
begin
  if FileExists(Dir + '\python\python.exe') then
    Exec(Dir + '\python\python.exe', '-m tarjuman quit', Dir, SW_HIDE, ewWaitUntilTerminated, Code);
  Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | ' +
    'Where-Object { $_.Path -and $_.Path.StartsWith(''' + Dir + '\python\'', [StringComparison]::OrdinalIgnoreCase) } | ' +
    'Stop-Process -Force -ErrorAction SilentlyContinue"',
    '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if DirExists(ExpandConstant('{app}')) then
    CloseTarjuman(ExpandConstant('{app}'));
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
    CloseTarjuman(ExpandConstant('{app}'));
  if CurUninstallStep = usPostUninstall then
  begin
    { The data of the user who runs the uninstaller; other users' data is left alone. }
    DataDir := ExpandConstant('{localappdata}\Tarjuman');
    if DirExists(DataDir) and not UninstallSilent then
      if MsgBox(FmtMessage(CustomMessage('KeepData'), [DataDir]), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
