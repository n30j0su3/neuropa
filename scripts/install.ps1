[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    Write-Host "NeuroPA · instalación local para Windows" -ForegroundColor Cyan
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "Falta uv. Instálalo desde https://docs.astral.sh/uv/getting-started/installation/ y vuelve a ejecutar este script."
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Falta Git para Windows: https://git-scm.com/download/win"
    }
    uv --version
    if ($Check) {
        Write-Host "Requisitos listos. --Check no modificó el entorno." -ForegroundColor Green
        exit 0
    }
    if (-not $Yes) {
        $answer = Read-Host "Se creará .venv y se descargarán dependencias verificadas por uv. ¿Continuar? [s/N]"
        if ($answer -notmatch '^(s|si|sí|y|yes)$') { Write-Host "Cancelado sin cambios."; exit 0 }
    }
    uv sync --frozen
    Write-Host "Instalación lista. Ejecuta: scripts\run-neuropa.ps1" -ForegroundColor Green
} finally {
    Pop-Location
}
