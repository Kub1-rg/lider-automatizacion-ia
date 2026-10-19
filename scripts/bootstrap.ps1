[CmdletBinding()]
param(
    [switch] $SkipBuild,
    [switch] $Technical
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'No se encontró Docker. Instala/inicia Docker Desktop y vuelve a ejecutar este script.'
}

if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Se creó .env con valores vacíos desde .env.example. No contiene credenciales.'
}

$workflowPath = Join-Path $repoRoot 'flujo\solicitudes.json'
if (-not (Test-Path -LiteralPath $workflowPath)) {
    throw 'No existe flujo/solicitudes.json; espera a que se entregue el workflow antes de iniciar los servicios.'
}

$composeArgs = @()
if ($Technical) {
    $composeArgs = @('-f', 'compose.yaml', '-f', 'compose.tecnico.yaml', '-p', 'lider-ia-tecnico')
}

if ($SkipBuild) {
    docker compose @composeArgs up -d
} else {
    docker compose @composeArgs up -d --build
}
if ($LASTEXITCODE -ne 0) { throw 'No fue posible iniciar Docker Compose.' }

Write-Host 'Esperando la API saludable...'
$deadline = (Get-Date).AddMinutes(2)
do {
    try {
        $apiPort = if ($Technical) { 18019 } else { 18018 }
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$apiPort/health" -TimeoutSec 3
        if ($health) { break }
    } catch {
        Start-Sleep -Seconds 2
    }
} while ((Get-Date) -lt $deadline)
if (-not $health) { throw 'La API no quedó saludable en 2 minutos. Consulta los logs del servicio api del proyecto correspondiente.' }

$n8nPort = if ($Technical) { 5689 } else { 5688 }
$n8nReady = $false
$deadline = (Get-Date).AddMinutes(3)
do {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$n8nPort/" -TimeoutSec 4 -UseBasicParsing
        $n8nReady = $true
    } catch {
        if ($_.Exception.Response) { $n8nReady = $true }
        else { Start-Sleep -Seconds 3 }
    }
} while (-not $n8nReady -and (Get-Date) -lt $deadline)
if (-not $n8nReady) { throw 'n8n no respondió en 3 minutos; revisa los logs del servicio n8n.' }
if ($Technical) {
    $stubReady = $false
    $deadline = (Get-Date).AddMinutes(1)
    do {
        try {
            $stubHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:5690/healthz' -TimeoutSec 3
            $stubReady = $stubHealth.fixture -eq $true
        } catch { Start-Sleep -Seconds 2 }
    } while (-not $stubReady -and (Get-Date) -lt $deadline)
    if (-not $stubReady) { throw 'El doble HTTP técnico no respondió en 1 minuto.' }
}

$workflow = Get-Content -LiteralPath $workflowPath -Raw | ConvertFrom-Json
if ($workflow -is [array]) { $workflows = @($workflow) } else { $workflows = @($workflow) }
$ids = @($workflows | ForEach-Object { $_.id } | Where-Object { $_ })
if ($ids.Count -eq 0) {
    throw 'El JSON no trae id de workflow; la publicación CLI de n8n requiere un id estable.'
}

Write-Host 'Importando workflow en n8n...'
docker compose @composeArgs exec -T n8n n8n import:workflow --input=/workflows/solicitudes.json
if ($LASTEXITCODE -ne 0) {
    throw "Falló la importación. Si n8n solicita configurar su propietario, completa el alta local en http://127.0.0.1:$n8nPort y ejecuta este script de nuevo."
}

foreach ($id in $ids) {
    docker compose @composeArgs exec -T n8n n8n publish:workflow "--id=$id"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo publicar el workflow $id." }
}

docker compose @composeArgs restart n8n
if ($LASTEXITCODE -ne 0) { throw 'No fue posible reiniciar n8n después de publicar el workflow.' }

$n8nHealthy = $false
$deadline = (Get-Date).AddMinutes(2)
do {
    try {
        $n8nHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$n8nPort/healthz" -TimeoutSec 4
        $n8nHealthy = [bool]$n8nHealth
    } catch { Start-Sleep -Seconds 2 }
} while (-not $n8nHealthy -and (Get-Date) -lt $deadline)
if (-not $n8nHealthy) { throw 'n8n no quedó saludable después de publicar el workflow.' }

# Healthz puede estar disponible antes de que n8n termine de registrar los webhooks.
# La entrada inválida solo espera una ruta activa y no llama a API ni proveedor.
$probeCode = $null
$probeDeadline = (Get-Date).AddSeconds(45)
do {
    $probeCode = $null
    try {
        $probe = Invoke-WebRequest -Uri "http://127.0.0.1:$n8nPort/webhook/solicitud" -Method Post `
            -ContentType 'application/json' -Body '{"cliente_email":"","mensaje":"bootstrap route probe"}' `
            -TimeoutSec 10 -UseBasicParsing
        $probeCode = [int]$probe.StatusCode
    } catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $probeCode = [int]$_.Exception.Response.StatusCode
        }
    }
    if ($probeCode -eq 422) { break }
    if ($null -ne $probeCode -and $probeCode -notin @(404, 503)) {
        throw "La comprobación del webhook recibió HTTP $probeCode; se esperaba 422 para la entrada inválida."
    }
    if ((Get-Date) -lt $probeDeadline) {
        if ($probeCode -eq 503) { Start-Sleep -Seconds 2 }
        else { Start-Sleep -Seconds 1 }
    }
} while ((Get-Date) -lt $probeDeadline)
if ($probeCode -ne 422) {
    $observed = if ($null -eq $probeCode) { 'sin respuesta de red' } else { "HTTP $probeCode" }
    throw "El webhook no quedó registrado en 45 segundos ($observed). Revisa la publicación del workflow y los logs de n8n."
}

if ($Technical) {
    Write-Host 'Entorno técnico aislado listo. API: http://127.0.0.1:18019/docs; n8n: http://127.0.0.1:5689; fixture: 127.0.0.1:5690.'
    Write-Host 'El proveedor es un doble HTTP determinista exclusivo para pruebas; no es DeepSeek. Ejecuta python scripts/integracion_tecnica.py.'
} else {
    Write-Host 'Servicios listos. API: http://127.0.0.1:18018/docs; n8n: http://127.0.0.1:5688.'
    Write-Host 'El flujo requiere configurar DEEPSEEK_API_KEY para una prueba real. Notificaciones según configuración local; consulta su estado antes de probar.'
}

