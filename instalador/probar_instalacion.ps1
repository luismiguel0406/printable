# Prueba de instalación real (GitHub Actions, windows-latest).
param([Parameter(Mandatory)][string]$Setup)
$ErrorActionPreference = "Stop"
$App = "$env:ProgramFiles\Printable"
$Datos = "$env:ProgramData\Printable"
$Py = "$App\python\python.exe"
$env:PRINTABLE_DATOS = $Datos

function Paso($Texto) { Write-Host "`n=== $Texto" }
function Instalar {
    $p = Start-Process $Setup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$PWD\instalacion.log" -Wait -PassThru
    Get-Content instalacion.log | Select-String "Paso:|Resultado:|Pasos con error" | ForEach-Object { Write-Host $_ }
    if ($p.ExitCode -ne 0) { throw "El instalador terminó con código $($p.ExitCode)" }
    if (Select-String -Path instalacion.log -Pattern "Pasos con error" -Quiet) { throw "Algún paso del instalador falló (ver arriba)" }
}
function Esperar([scriptblock]$Condicion, [int]$Segundos, [string]$Que) {
    for ($i = 0; $i -lt $Segundos; $i++) { if (& $Condicion) { return }; Start-Sleep 1 }
    throw "Tiempo agotado esperando: $Que"
}
function Responde {
    try { (Invoke-WebRequest "http://127.0.0.1:8000/" -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop).StatusCode -in 200, 302 }
    catch { $_.Exception.Response -and [int]$_.Exception.Response.StatusCode -in 200, 302 }
}

Paso "Instalar"
Instalar
& $Py "$App\app\instalador\configurar.py" verificar
if ($LASTEXITCODE -ne 0) { throw "La verificación de la instalación falló" }

Paso "Arrancar el lanzador"
$Lanzador = Start-Process "$App\python\python.exe" -ArgumentList "`"$App\app\lanzador.py`"" -WorkingDirectory "$App\app" -PassThru
Esperar { Responde } 90 "que el servidor responda"
Write-Host "El servidor responde"

Paso "Ctrl+P hacia Printable"
& $Py "$App\app\instalador\prueba_humo.py" usuario
"Prueba de Printable desde el Bloc de notas" | Out-Printer -Name "Printable"
Esperar { & $Py "$App\app\instalador\prueba_humo.py" capturados; $LASTEXITCODE -eq 0 } 120 "que el PDF llegue como trabajo recibido"
Write-Host "El trabajo llegó a la bandeja"

Paso "Actualizar (reinstalar) conserva los datos"
Stop-Process -Id $Lanzador.Id -Force -ErrorAction SilentlyContinue
Instalar
& $Py "$App\app\instalador\prueba_humo.py" capturados
if ($LASTEXITCODE -ne 0) { throw "Se perdieron los datos al reinstalar" }

Paso "Desinstalar conserva los datos"
$p = Start-Process "$App\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
Start-Sleep 5
if (-not (Test-Path "$Datos\db.sqlite3")) { throw "La desinstalación borró los datos" }
if (Test-Path "$App\app\lanzador.py") { throw "La desinstalación dejó el programa" }
Write-Host "`nPrueba de instalación: OK"
