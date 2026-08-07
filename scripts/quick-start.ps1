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

# Search a command in common Windows install locations
# (npm-global %AppData%\npm and Program Files) in addition to PATH.
function Find-Command($cmd) {
    if (Has $cmd) { return (Get-Command $cmd).Path }
    $candidates = @(
        (Join-Path $HOME 'AppData\Roaming\npm' "$cmd.cmd"),
        (Join-Path $HOME 'AppData\Roaming\npm' "$cmd.ps1"),
        "C:\Program Files\nodejs\$cmd.cmd",
        "C:\Program Files (x86)\nodejs\$cmd.cmd"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

# After npm-global installs, prepend %AppData%\npm to PATH for the
# current PowerShell session so Has / Get-Command finds it.
function Refresh-PathForNpm {
    $npmBin = Join-Path $HOME 'AppData\Roaming\npm'
    if (Test-Path $npmBin) {
        $env:PATH = "$npmBin;$env:PATH"
    }
}

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
    # Por defecto usamos $HOME\neuropa, pero el usuario puede elegir otra ruta
    # (por ejemplo C:\dev\neuropa) para mantener limpio su perfil.
    $DefaultClone = Join-Path $HOME 'neuropa'
    $Choice = Read-Host "  Donde instalar NeuroPA? (Enter = $DefaultClone, escribe otra ruta)"
    if ([string]::IsNullOrWhiteSpace($Choice)) { $CloneTarget = $DefaultClone }
    else { $CloneTarget = $Choice.Trim() }
    Info "Voy a clonar NeuroPA en $CloneTarget"
    if (Test-Path "$CloneTarget\pyproject.toml") {
        Ok "Repo ya existente en $CloneTarget"
        $RootDir = $CloneTarget
    } elseif (Confirm "Clonar NeuroPA desde GitHub en $CloneTarget?") {
        Run-Native { git clone --depth 1 https://github.com/n30j0su3/neuropa.git "$CloneTarget" }
        if (Test-Path "$CloneTarget\pyproject.toml") {
            $RootDir = $CloneTarget
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

# ── Step 6: OpenCode (IA gratuita — LA forma fácil de empezar) ──
Write-Host ""
Write-Host "  -- IA gratuita (OpenCode) --" -ForegroundColor Cyan
Write-Host "  Sin esto, NeuroPA no puede responder mensajes." -ForegroundColor DarkGray
Write-Host ""
if (Has opencode -or (Has opencode-ai)) {
    Ok "OpenCode detectado — IA lista"
} else {
    # Need npm first
    if (-not (Has npm)) {
        Warn "Node.js/npm no detectado. Necesario para OpenCode (IA gratuita)."
        if (Has winget) {
            if (Confirm "Instalar Node.js con winget? (necesario para IA gratuita)") {
                Run-Native { winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements }
                $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
                if (Has npm) { Ok "Node.js instalado" } else { Fail "Node.js no se detecto. Instala desde https://nodejs.org" }
            } else {
                Warn "Sin Node.js no hay IA gratuita. Instala desde https://nodejs.org despues."
            }
        } else {
            Warn "Instala Node.js desde https://nodejs.org para tener IA gratuita."
        }
    }
    # Now install opencode
    if (Has npm) {
        Write-Host ""
        Info "Instalando OpenCode (IA gratuita, no requiere API key)…"
        Run-Native { npm install -g opencode-ai }
        # npm install -g on Windows lands under %AppData%\npm which is NOT
        # on PATH by default for new sessions. Refresh for current shell AND
        # persist NEUROPA_OPENCODE_BIN so the runtime can find it later.
        Refresh-PathForNpm
        $oc = Find-Command 'opencode'
        if ($null -ne $oc) {
            Ok "OpenCode detectado en: $oc"
            [System.Environment]::SetEnvironmentVariable('NEUROPA_OPENCODE_BIN', $oc, 'User')
            Info "Variable NEUROPA_OPENCODE_BIN registrada para futuras sesiones."
        } else {
            Warn "OpenCode no se detecto tras instalar. Puedes probar manualmente: npm install -g opencode-ai"
            Info "Sin OpenCode, NeuroPA arrancara pero NO podra responder mensajes."
            Info "Alternativa: configura OpenRouter (gratis) en Ajustes dentro de NeuroPA."
        }
    }
}

# ── Step 7: Crear acceso directo "NeuroPA fácil" en el Escritorio ──
Write-Host ""
Write-Host "  -- Creando acceso directo 'NeuroPA' en tu escritorio --" -ForegroundColor Cyan

$DestDir = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path $DestDir)) { $DestDir = $env:USERPROFILE }

$EasyBat = Join-Path $RootDir 'scripts/neuropa-easy.bat'
$UninstallBat = Join-Path $RootDir 'scripts/neuropa-uninstall.bat'

# Copia neuropa-easy.bat al escritorio para doble-click
if (Test-Path $EasyBat) {
    $EasyShortcut = Join-Path $DestDir 'NeuroPA.bat'
    Copy-Item $EasyBat $EasyShortcut -Force
    Ok "Acceso directo creado: $EasyShortcut"
} else {
    Warn "No encontre $EasyBat"
}

# Ofrece crear acceso al desinstalador (sin forzar — el usuario decide)
if (Test-Path $UninstallBat) {
    Write-Host ""
    Info "Desinstalador (cuando lo necesites): scripts/neuropa-uninstall.bat"
}

Write-Host ""
Write-Host "  NeuroPA esta listo!" -ForegroundColor Green
Write-Host ""
Write-Host "  Para arrancar: doble-click en 'NeuroPA.bat' de tu escritorio" -ForegroundColor DarkGray
Write-Host "  O desde terminal:  cd $RootDir ; uv run neuropa" -ForegroundColor DarkGray
Write-Host "  URL:               http://127.0.0.1:8474" -ForegroundColor Cyan
Write-Host ""
if (Confirm "Arrancar NeuroPA ahora?") {
    uv run neuropa
}
