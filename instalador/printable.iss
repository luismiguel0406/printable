; Instalador de Printable. Se compila con instalador\construir.ps1 (necesita dist\Printable).
#define Version GetEnv("PRINTABLE_VERSION")
#if Version == ""
  #define Version "0.0.0-dev"
#endif

[Setup]
AppId={{19C0A8F3-886C-49DA-BB5A-007F2BA7E05F}
AppName=Printable
AppVersion={#Version}
AppPublisher=Luis Del Orbe
DefaultDirName={autopf}\Printable
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir=..\dist
OutputBaseFilename=PrintableSetup-{#Version}
SetupIconFile=printable.ico
UninstallDisplayIcon={app}\app\instalador\printable.ico
UninstallDisplayName=Printable
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
CloseApplications=force
SetupLogging=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Dirs]
Name: "{commonappdata}\Printable"; Permissions: users-modify

[Files]
Source: "..\dist\Printable\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; Código viejo fuera; los datos viven en ProgramData y no se tocan.
Type: filesandordirs; Name: "{app}\app"

[Icons]
Name: "{autodesktop}\Printable"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\lanzador.py"" --abrir"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\instalador\printable.ico"
Name: "{autoprograms}\Printable"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\lanzador.py"" --abrir"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\instalador\printable.ico"
Name: "{commonstartup}\Printable"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\lanzador.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\instalador\printable.ico"

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\lanzador.py"" --abrir"; WorkingDir: "{app}\app"; Description: "Abrir Printable ahora"; Flags: postinstall nowait skipifsilent runasoriginaluser

[Code]
var
  Fallos: String;

function ClawInstalado: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\clawPDF\SetupHelper.exe'))
         or FileExists(ExpandConstant('{commonpf32}\clawPDF\SetupHelper.exe'));
end;

procedure DetenerPrintable;
var
  Codigo: Integer;
begin
  { Cierra solo el pythonw de esta instalación, no otros programas en Python. }
  Exec('powershell.exe',
    '-NoProfile -Command "Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like ''' +
    ExpandConstant('{app}') + '\*'' } | Stop-Process -Force"',
    '', SW_HIDE, ewWaitUntilTerminated, Codigo);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  DetenerPrintable;
  Result := '';
end;

procedure Paso(const Descripcion, Archivo, Parametros: String; ComoUsuario: Boolean);
var
  Codigo: Integer;
  Ok: Boolean;
begin
  WizardForm.StatusLabel.Caption := Descripcion + '...';
  Log('Paso: ' + Descripcion + ' -> ' + Archivo + ' ' + Parametros);
  if ComoUsuario then
    Ok := ExecAsOriginalUser(Archivo, Parametros, ExpandConstant('{app}\app'), SW_HIDE, ewWaitUntilTerminated, Codigo)
  else
    Ok := Exec(Archivo, Parametros, ExpandConstant('{app}\app'), SW_HIDE, ewWaitUntilTerminated, Codigo);
  Log('Resultado: ' + IntToStr(Codigo));
  if (not Ok) or (Codigo <> 0) then
    Fallos := Fallos + #13#10 + '  - ' + Descripcion + ' (código ' + IntToStr(Codigo) + ')';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Py, Conf: String;
begin
  if CurStep = ssPostInstall then
  begin
    Fallos := '';
    Py := ExpandConstant('{app}\python\python.exe');
    Conf := '"' + ExpandConstant('{app}\app\instalador\configurar.py') + '"';
    Paso('Preparando los datos', Py, Conf + ' datos', False);
    if not ClawInstalado then
      Paso('Instalando clawPDF', 'msiexec.exe',
        '/i "' + ExpandConstant('{app}\terceros\clawPDF_setup.msi') + '" /qn /norestart', False);
    Paso('Creando la impresora Printable', Py, Conf + ' impresora', False);
    Paso('Configurando Ctrl+P hacia Printable', Py, Conf + ' clawpdf', True);
    Paso('Protegiendo las impresoras reales', Py, Conf + ' colas', False);
    if Fallos <> '' then
    begin
      Log('Pasos con error:' + Fallos);
      SuppressibleMsgBox('Printable quedó instalado, pero estos pasos fallaron:' + #13#10 + Fallos + #13#10#13#10 +
        'Puede que Ctrl+P no llegue al sistema. Vuelve a ejecutar el instalador o sigue la instalación manual de docs\instalacion.md.',
        mbError, MB_OK, IDOK);
    end;
  end;
end;

function InitializeUninstall: Boolean;
begin
  DetenerPrintable;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Datos: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Datos := ExpandConstant('{commonappdata}\Printable');
    if DirExists(Datos) and (SuppressibleMsgBox(
         '¿Borrar también los datos de Printable (trabajos, perfiles, tarifas)?' + #13#10 + Datos,
         mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES) then
      DelTree(Datos, True, True, True);
  end;
end;
