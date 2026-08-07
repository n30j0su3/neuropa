@echo off
REM ════════════════════════════════════════════════════════════════
REM  NeuroPA · Desinstalador (preserva tus datos)
REM  - Borra repo, dependencias Python y OpenCode
REM  - PRESERVA: ~/.local/share/neuropa/ (memoria, skills, identidad)
REM ════════════════════════════════════════════════════════════════
setlocal ENABLEDELAYEDEXPANSION

set ROOTDIR=%USERPROFILE%\neuropa
set DATA=%LOCALAPPDATA%\neuropa
if not defined DATA set DATA=%USERPROFILE%\.local\share\neuropa

echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║  Desinstalador NeuroPA                                  ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.
echo  Tus datos (memoria, skills, identidad) NO se tocan.
echo  Si tambien quieres borrarlos, elige la opcion al final.
echo.

REM ── Modo interactivo ───────────────────────────────────────────
echo  Que quieres desinstalar?
echo.
echo    [1] Solo NeuroPA  (repo + cache uv)         [RECOMENDADO]
echo    [2] NeuroPA + OpenCode (IA gratuita via npm)
echo    [3] Todo lo de arriba + Node.js
echo    [4] TODO + uv + Python (desinstalacion completa)
echo    [5] Cancelar
echo.
set /p OPT="  Elige opcion (1-5): "
if "%OPT%"=="5" (
    echo Cancelado.
    pause
    exit /b 0
)

REM ── 1. Borrar repo NeuroPA ────────────────────────────────────
echo.
if exist "%ROOTDIR%" (
    echo  [1] Borrando repositorio %ROOTDIR%...
    rmdir /s /q "%ROOTDIR%"
    echo        OK.
) else (
    echo  [1] Repositorio no encontrado (%ROOTDIR%) - omitido.
)

REM ── 2. Limpiar cache uv ───────────────────────────────────────
echo.
echo  [2] Limpiando cache de dependencias uv...
uv cache clean 2>nul >nul
echo        OK.

REM ── 3. OpenCode (opcional) ────────────────────────────────────
if "%OPT%"=="2" goto DES_OPENCODE
if "%OPT%"=="3" goto DES_OPENCODE
if "%OPT%"=="4" goto DES_OPENCODE
echo.
echo  [3] OpenCode omitido (opcion %OPT%).
goto DES_NODE

:DES_OPENCODE
echo.
echo  [3] Desinstalando OpenCode CLI...
where npm >nul 2>nul
if not errorlevel 1 (
    npm uninstall -g opencode-ai 2>nul
    echo        OK.
) else (
    echo        npm no encontrado, omitido.
)

REM ── 4. Node.js (opcional) ─────────────────────────────────────
:DES_NODE
if "%OPT%"=="3" goto DES_NODEDO
if "%OPT%"=="4" goto DES_NODEDO
echo.
echo  [4] Node.js omitido (opcion %OPT%).
goto DES_UV

:DES_NODEDO
echo.
echo  [4] Desinstalando Node.js...
where winget >nul 2>nul
if not errorlevel 1 (
    echo       ADVERTENCIA: esto afecta todo tu sistema, no solo NeuroPA.
    set /p YN="       Continuar? (s/N): "
    if /i "!YN!"=="s" (
        winget uninstall --id OpenJS.NodeJS.LTS -e 2>nul
        echo        OK.
    ) else (
        echo        Omitido.
    )
) else (
    echo        winget no disponible. Desinstala Node.js desde Panel de Control.
)

REM ── 5. uv + Python (opcional) ─────────────────────────────────
:DES_UV
if "%OPT%"=="4" goto DES_PYDO
echo.
echo  [5] uv/Python omitido (opcion %OPT%).
goto DES_DATA

:DES_PYDO
echo.
echo  [5a] Desinstalando uv...
where winget >nul 2>nul
if not errorlevel 1 (
    set /p YN="        Confirmar desinstalacion de uv? (s/N): "
    if /i "!YN!"=="s" (
        winget uninstall --id astral-sh.uv -e 2>nul
        echo         OK.
    ) else (
        echo         Omitido.
    )
) else (
    echo        winget no disponible. Desinstala uv manualmente.
)
echo.
echo  [5b] ADVERTENCIA sobre Python:
echo        Desinstalar Python puede romper otras apps. Recomendamos dejarlo.
echo        Para desinstalar manualmente: Panel de Control ^> Programas.

REM ── 6. Preguntar sobre datos del usuario ──────────────────────
:DES_DATA
echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║  Desinstalacion de app terminada.                        ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.
echo  Tus datos siguen en:
echo    %DATA%
echo.
set /p ERASE="  Quieres borrar TAMBIEN tus datos (memoria, skills, identidad)? (s/N): "
if /i "%ERASE%"=="s" (
    if exist "%DATA%" (
        rmdir /s /q "%DATA%"
        echo  Datos borrados.
    ) else (
        echo  No hay carpeta de datos.
    )
) else (
    echo  Datos preservados en: %DATA%
    echo  Para borrarlos despues: rmdir /s /q "%DATA%"
)
echo.
echo  Variable NEUROPA_OPENCODE_BIN (si fue creada por el installer):
set /p RMENV="  Eliminarla tambien? (s/N): "
if /i "%RMENV%"=="s" (
    REG delete HKCU\Environment /F /V NEUROPA_OPENCODE_BIN 2>nul >nul
    echo  Variable eliminada.
)
echo.
echo  ✓ Listo.
echo.
pause
