# Construye dist\PrintableSetup-<versión>.exe. Uso (en Windows, desde la raíz del repo):
#   ./instalador/construir.ps1 -Version 1.0.0
param([string]$Version = "0.0.0-dev")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Descargas fijas y verificadas. Si cambias una versión, actualiza su SHA-256.
$PyVersion = "3.12.10"
$PySha256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
$ClawVersion = "0.9.3"
$ClawSha256 = "4b8102955e7a75149c45efc968643db87b3aed85753136b186734ee1c614298c"

$Raiz = Resolve-Path "$PSScriptRoot\.."
$Dist = Join-Path $Raiz "dist"
$Destino = Join-Path $Dist "Printable"
$Cache = Join-Path $Raiz ".descargas"

function Descargar([string]$Url, [string]$Archivo, [string]$Sha) {
    New-Item -ItemType Directory -Force $Cache | Out-Null
    $Ruta = Join-Path $Cache $Archivo
    if (-not (Test-Path $Ruta)) { Invoke-WebRequest $Url -OutFile $Ruta }
    $Hash = (Get-FileHash $Ruta -Algorithm SHA256).Hash.ToLower()
    if (-not $Sha) { throw "Falta fijar el SHA-256 de $Archivo. Valor descargado: $Hash" }
    if ($Hash -ne $Sha) { Remove-Item $Ruta; throw "SHA-256 de $Archivo no coincide: $Hash" }
    return $Ruta
}

Write-Host "== Limpiando"
if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
New-Item -ItemType Directory -Force "$Destino\python", "$Destino\app", "$Destino\terceros" | Out-Null

Write-Host "== Python $PyVersion embebible"
$Zip = Descargar "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip" "python-$PyVersion-embed-amd64.zip" $PySha256
Expand-Archive $Zip -DestinationPath "$Destino\python"
$Pth = Get-ChildItem "$Destino\python\python3*._pth" | Select-Object -First 1
$Lineas = (Get-Content $Pth) | Where-Object { $_ -notmatch "^#?\s*import site" }
$Lineas += "Lib\site-packages", "..\app", "import site"
Set-Content $Pth $Lineas -Encoding ascii

Write-Host "== Dependencias"
python -m pip install --disable-pip-version-check --no-warn-script-location `
    --target "$Destino\python\Lib\site-packages" -r "$Raiz\requirements-windows.txt"
if ($LASTEXITCODE -ne 0) { throw "pip falló" }

Write-Host "== Código"
$Excluir = @(".git", ".github", ".superpowers", ".descargas", "dist", "tests", "docs", "media", "staticfiles", "__pycache__", ".pytest_cache")
robocopy $Raiz "$Destino\app" /E /NFL /NDL /NJH /NJS /XD $Excluir /XF "db.sqlite3*" ".clave_secreta" "*.pyc" "spike_perfil.bin" | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy falló ($LASTEXITCODE)" }
$global:LASTEXITCODE = 0

Write-Host "== Comprobando el Python incluido"
$Py = "$Destino\python\python.exe"
& $Py -c "import django, pymupdf, PIL, waitress, win32print, win32api, pystray; print('librerías ok')"
if ($LASTEXITCODE -ne 0) { throw "El Python incluido no carga las librerías" }

Write-Host "== Estáticos"
$env:PRINTABLE_DATOS = Join-Path $env:TEMP "printable-build"
Push-Location "$Destino\app"
& $Py manage.py collectstatic --noinput -v 0
if ($LASTEXITCODE -ne 0) { throw "collectstatic falló" }
Pop-Location
Remove-Item Env:PRINTABLE_DATOS

Write-Host "== clawPDF $ClawVersion"
$Msi = Descargar "https://github.com/clawsoftware/clawPDF/releases/download/$ClawVersion/clawPDF_${ClawVersion}_setup.msi" "clawPDF_${ClawVersion}_setup.msi" $ClawSha256
Copy-Item $Msi "$Destino\terceros\clawPDF_setup.msi"
Copy-Item "$Raiz\instalador\TERCEROS.txt" "$Destino\terceros\"

Write-Host "== Inno Setup"
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { choco install innosetup -y --no-progress | Out-Null; $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
$env:PRINTABLE_VERSION = $Version
& $Iscc /Q "$Raiz\instalador\printable.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
Write-Host "Listo: $Dist\PrintableSetup-$Version.exe"
