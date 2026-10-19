[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$apiPort = if ($env:AUTOMATIZACION_TECNICA -eq '1') { 18019 } else { 18018 }
$n8nPort = if ($env:AUTOMATIZACION_TECNICA -eq '1') { 5689 } else { 5688 }
$checks = @(
    @{ Name = 'API health'; Uri = "http://127.0.0.1:$apiPort/health" },
    @{ Name = 'API OpenAPI'; Uri = "http://127.0.0.1:$apiPort/openapi.json" },
    @{ Name = 'n8n editor'; Uri = "http://127.0.0.1:$n8nPort/" }
)

foreach ($check in $checks) {
    try {
        $response = Invoke-WebRequest -Uri $check.Uri -TimeoutSec 8 -UseBasicParsing
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            throw "HTTP $($response.StatusCode)"
        }
        Write-Host "OK  $($check.Name) ($($response.StatusCode))"
    } catch {
        Write-Error "FALLO $($check.Name): $($_.Exception.Message)"
        exit 1
    }
}

Write-Host 'Smoke HTTP completado. Esto no ejecuta el webhook ni demuestra una llamada real al LLM o correo.'

