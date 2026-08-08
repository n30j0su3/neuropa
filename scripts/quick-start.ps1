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
# Two entry paths handled here:
#   A) Script is being run from inside an existing repo checkout ($RootDir
#      has pyproject.toml) -> use it directly.
#   B) Script is run standalone (e.g. via iex) -> ask user where the repo
#      lives. If a complete checkout is already there, reuse it; if only an
#      empty/partial folder, run git pull; otherwise clone fresh.
$RootDir = $PSScriptRoot
$DetectedRepo = $false
if (Test-Path "$RootDir\pyproject.toml") {
    Ok "Repo detectado en $RootDir"
    $DetectedRepo = $true
}

if (-not $DetectedRepo) {
    $DefaultClone = Join-Path $HOME 'neuropa'
    $Choice = Read-Host "  Donde esta (o donde instalar) NeuroPA? (Enter = $DefaultClone, escribe otra ruta)"
    if ([string]::IsNullOrWhiteSpace($Choice)) { $CloneTarget = $DefaultClone }
    else { $CloneTarget = $Choice.Trim() }
    Info "Voy a usar NeuroPA en $CloneTarget"

    if (Test-Path "$CloneTarget\pyproject.toml") {
        Ok "Repo ya existente en $CloneTarget"
        $RootDir = $CloneTarget
    } elseif (Test-Path $CloneTarget) {
        # Carpeta existe pero no es un repo NeuroPA valido. Opciones:
        Warn "La carpeta $CloneTarget existe pero no contiene NeuroPA (sin pyproject.toml)."
        $Choice2 = Read-Host "  Que hago? (B=borrar y clonar fresh / A=abortar / O=ruta distinta)"
        switch ($Choice2.ToUpper()) {
            "B" {
                Info "Borrando $CloneTarget y clonando fresh..."
                Run-Native { Remove-Item -Recurse -Force $CloneTarget }
                Run-Native { git clone --depth 1 https://github.com/n30j0su3/neuropa.git $CloneTarget }
                if (Test-Path "$CloneTarget\pyproject.toml") {
                    $RootDir = $CloneTarget
                    Ok "Repo clonado en $RootDir"
                } else {
                    Fail "No pude clonar tras borrar. Verifica tu conexion."
                    exit 1
                }
            }
            "O" {
                $NewChoice = Read-Host "  Escribe la nueva ruta"
                $CloneTarget = $NewChoice.Trim()
                if (Test-Path "$CloneTarget\pyproject.toml") {
                    $RootDir = $CloneTarget
                    Ok "Repo encontrado en $RootDir"
                } else {
                    Run-Native { git clone --depth 1 https://github.com/n30j0su3/neuropa.git $CloneTarget }
                    if (Test-Path "$CloneTarget\pyproject.toml") {
                        $RootDir = $CloneTarget
                        Ok "Repo clonado en $RootDir"
                    } else { Fail "No pude clonar. Verifica tu conexion." ; exit 1 }
                }
            }
            default {
                Fail "Abortado por el usuario. Borra la carpeta o elige otra ruta."
                exit 1
            }
        }
    } elseif (Confirm "Clonar NeuroPA desde GitHub en $CloneTarget?") {
        Run-Native { git clone --depth 1 https://github.com/n30j0su3/neuropa.git $CloneTarget }
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

# Crea accesos .lnk reales: conservan el directorio de trabajo y muestran el icono de NeuroPA.
if (Test-Path $EasyBat) {
    $WshShell = New-Object -ComObject WScript.Shell
    $EasyShortcut = Join-Path $DestDir 'NeuroPA.lnk'
    $Link = $WshShell.CreateShortcut($EasyShortcut)
    $Link.TargetPath = $EasyBat
    $Link.WorkingDirectory = $RootDir
    $IconPath = Join-Path $RootDir 'neuropa\frontend\favicon.ico'
    if (Test-Path $IconPath) { $Link.IconLocation = "$IconPath,0" }
    $Link.Description = 'Abrir NeuroPA'
    $Link.Save()
    Ok "Acceso directo creado: $EasyShortcut"
} else {
    Warn "No encontre $EasyBat"
}

if (Test-Path $UninstallBat) {
    $UninstallShortcut = Join-Path $DestDir 'Desinstalar NeuroPA.lnk'
    $Link = $WshShell.CreateShortcut($UninstallShortcut)
    $Link.TargetPath = $UninstallBat
    $Link.WorkingDirectory = $RootDir
    $IconPath = Join-Path $RootDir 'neuropa\frontend\favicon.ico'
    if (Test-Path $IconPath) { $Link.IconLocation = "$IconPath,0" }
    $Link.Description = 'Desinstalar NeuroPA y preservar tus datos por defecto'
    $Link.Save()
    Info "Desinstalador creado: $UninstallShortcut"
}

Write-Host ""
Write-Host "  NeuroPA esta listo!" -ForegroundColor Green
Write-Host ""
Write-Host "  Para arrancar: doble-click en 'NeuroPA.bat' de tu escritorio" -ForegroundColor DarkGray
Write-Host "  O desde terminal:  cd $RootDir ; uv run neuropa" -ForegroundColor DarkGray
Write-Host "  URL:               http://127.0.0.1:8474" -ForegroundColor Cyan
Write-Host ""

# ── Step 8: Ofrecer actualizar repo (si es un checkout git) ──
if (Has git) {
    Push-Location $RootDir
    try {
        $gitCheck = git rev-parse --is-inside-work-tree 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            if (Confirm "Quieres verificar actualizaciones del repo? (git pull)") {
                Info "Ejecutando git pull..."
                Run-Native { git pull --ff-only }
                if ($LASTEXITCODE -eq 0) {
                    Ok "Repo actualizado a la ultima version."
                } else {
                    Warn "git pull tuvo conflictos. Tu codigo local difiere del remoto."
                    Info "Si quieres reinstalar: cierra NeuroPA, borra $RootDir (tus datos en %LOCALAPPDATA%\neuropa estan a salvo) y vuelve a correr el installer."
                }
            }
        }
    } finally { Pop-Location }
}

if (Confirm "Arrancar NeuroPA ahora?") {
    uv run neuropa
}
