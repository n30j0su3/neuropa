[CmdletBinding()]
param(
    [ValidateRange(1,65535)][int]$Port = 8474,
    [switch]$Lan,
    [switch]$Pairing,
    [string]$LanCidr = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "Falta uv. Ejecuta scripts\install.ps1 primero."
    }
    if ($Pairing -and -not $Lan) { throw "-Pairing requiere -Lan." }
    $arguments = @("run", "neuropa", "--port", "$Port")
    if ($Lan) { $arguments += "--lan" }
    if ($LanCidr) { $arguments += @("--lan-cidr", $LanCidr) }
    if ($Pairing) { $arguments += "--pairing" }
    & uv @arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
