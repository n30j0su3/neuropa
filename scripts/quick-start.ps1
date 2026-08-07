# ═══════════════════════════════════════════════════════════════════
# NeuroPA — Instalador de 1 comando para Windows (PowerShell)
# Uso:  irm https://raw.githubusercontent.com/n30j0su3/neuropa/main/scripts/quick-start.ps1 | iex
#   o:  powershell -ExecutionPolicy Bypass -File scripts\quick-start.ps1
# ═══════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# Allow native commands (git, uv, npm) to write to stderr without aborting.
# Git sends progress ("Cloning into...") to stderr, which PowerShell treats as
# a fatal error under Stop mode. This function runs a native command safely.
function Run-Native($block) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $block } finally { $ErrorActionPreference = $prev }
}

Write-Host ""
Write-Host "  NeuroPA — Instalador automatico" -ForegroundColor Cyan
Write-Host "  Sistema: Windows ($env:PROCESSOR_ARCHITECTURE)" -ForegroundColor DarkGray
Write-Host ""

function Ok($msg)    { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Info($msg)  { Write-Host "  -> $msg" -ForegroundColor Cyan }
function Warn($msg)  { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Fail($msg)  { Write-Host "  X $msg" -ForegroundColor Red }
function Has($cmd)   { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Confirm($prompt) {
    $ans = Read-Host "$prompt [S/n]"
    return ($ans -eq "" -or $ans -eq "s" -or $ans -eq "S" -or $ans -eq "y" -or $ans -eq "Y")
}

# ── Step 1: Git (BEFORE clone — can't clone without it) ──
Write-Host ""
Write-Host "  -- Git --" -ForegroundColor Cyan
if (Has git) { Ok "git detectado" }
else {
    Warn "git no detectado. Es necesario para descargar NeuroPA."
    if (Has winget) {
        if (Confirm "Instalar git con winget?") {
            Run-Native { winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements }
            # Refresh PATH for this session
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
            if (Has git) { Ok "git instalado" } else { Fail "git no se detecto tras instalar. Reinicia PowerShell y vuelve a ejecutar." ; exit 1 }
        } else { Fail "Sin git no puedo continuar. Instala desde https://git-scm.com" ; exit 1 }
    } else { Fail "Instala git desde https://git-scm.com y vuelve a ejecutar." ; exit 1 }
}

# ── Step 2: Detect or clone ──
$RootDir = $PSScriptRoot
if (-not (Test-Path "$RootDir\pyproject.toml") -and -not (Has neuropa)) {
    Info "No estas dentro del repo de NeuroPA. Lo clonare en $HOME\neuropa"
    if (Confirm "Clonar NeuroPA desde GitHub?") {
        Run-Native { git clone --depth 1 https://github.com/n30j0su3/neuropa.git "$HOME\neuropa" }
        if (Test-Path "$HOME\neuropa\pyproject.toml") {
            $RootDir = "$HOME\neuropa"
            Ok "Repo clonado en $RootDir"
        } else {
            Fail "No pude clonar. Verifica tu conexion o instala git primero."
            exit 1
        }
    } else {
        Fail "Necesitas el repo. Clona manualmente: git clone https://github.com/n30j0su3/neuropa.git"
        exit 1
    }
}
Set-Location $RootDir

# ── Step 3: Python ──
Write-Host ""
Write-Host "  -- Python --" -ForegroundColor Cyan
$pythonOk = $false
try {
    $pyver = python --version 2>$null
    if ($pyver -match "3\.(\d+)") { $pyverNum = [int]$Matches[1]; if ($pyverNum -ge 8) { Ok "Python $pyver"; $pythonOk = $true } }
} catch {}

if (-not $pythonOk) {
    Warn "Python 3.8+ no detectado"
    if (Has winget) {
        if (Confirm "Instalar Python con winget?") {
            winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements 2>$null
            # Refresh PATH for this session
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            Ok "Python instalado"
        }
    } else {
        Fail "Instala Python desde https://python.org"
        exit 1
    }
}

# ── Step 4: uv ──
Write-Host ""
Write-Host "  -- uv (gestor de entorno) --" -ForegroundColor Cyan
if (Has uv) { Ok "uv detectado" }
else {
    Info "uv no detectado. Evita pelear con pip/venv."
    if (Confirm "Instalar uv automaticamente?") {
        try {
            irm https://astral.sh/uv/install.ps1 | iex 2>$null
            $env:PATH += ";$HOME\.local\bin;$HOME\.cargo\bin"
            Ok "uv instalado"
        } catch {
            Fail "No pude instalar uv. Ve a https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        }
    } else { exit 1 }
}

# ── Step 5: Install NeuroPA ──
Write-Host ""
Write-Host "  -- Configurando NeuroPA --" -ForegroundColor Cyan
Info "Creando entorno y dependencias (1-2 min)…"
uv sync --quiet 2>$null
if ($LASTEXITCODE -ne 0) { uv sync }
Ok "Dependencias instaladas"
uv run neuropa --version 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { Ok "NeuroPA CLI listo" }
else { Fail "Algo fallo"; exit 1 }

# ── Step 6: OpenCode (opcional) ──
Write-Host ""
Write-Host "  -- OpenCode (IA gratuita) --" -ForegroundColor Cyan
if (Has opencode -or (Has opencode-ai)) { Ok "OpenCode detectado" }
else {
    if (Has npm) {
        if (Confirm "Instalar OpenCode con npm?") {
            npm install -g opencode-ai 2>$null
            Ok "OpenCode instalado"
        } else { Info "OpenCode omitido. NeuroPA funcionara sin IA hasta que lo instales." }
    } else {
        Warn "Node.js/npm no detectado. OpenCode es opcional."
        Info "Para IA gratis despues: instala Node.js desde https://nodejs.org y ejecuta: npm install -g opencode-ai"
    }
}

# ── Step 7: Launch ──
Write-Host ""
Write-Host "  NeuroPA esta listo!" -ForegroundColor Green
Write-Host ""
Write-Host "  Arrancar:  cd $RootDir ; uv run neuropa" -ForegroundColor DarkGray
Write-Host "  URL:       http://127.0.0.1:8474" -ForegroundColor Cyan
Write-Host ""
if (Confirm "Arrancar NeuroPA ahora?") {
    uv run neuropa
}
