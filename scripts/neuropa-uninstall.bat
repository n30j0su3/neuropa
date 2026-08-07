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
echo  Se eliminara:
echo    - Repositorio:       %ROOTDIR%
echo    - Dependencias (uv):  cache local
echo    - OpenCode CLI:       uninstall npm
echo.
echo  Se CONSERVARA:
echo    - Tus datos:          %DATA%
echo.
echo  Tus datos (memoria, skills, identidad) NO se tocan.
echo.
set /p CONFIRM="Continuar? (S/n): "
if /i not "%CONFIRM%"=="S" (
    echo Cancelado.
    pause
    exit /b 0
)

REM 1. Borrar repo
if exist "%ROOTDIR%" (
    echo.
    echo  [1/3] Borrando repositorio %ROOTDIR%...
    rmdir /s /q "%ROOTDIR%"
    echo        OK.
)

REM 2. Limpiar cache uv (dependencias)
echo.
echo  [2/3] Limpiando cache de dependencias uv...
uv cache clean 2>nul >nul
echo        OK.

REM 3. Desinstalar OpenCode CLI
echo.
echo  [3/3] Desinstalando OpenCode CLI...
where npm >nul 2>nul
if not errorlevel 1 (
    npm uninstall -g opencode-ai 2>nul
    echo        OK.
) else (
    echo        npm no encontrado, omitido.
)

echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║  ✓ NeuroPA desinstalado.                               ║
echo  ║                                                          ║
echo  ║  Tus datos siguen en:                                    ║
echo  ║    %DATA%
echo  ║                                                          ║
echo  ║  Para borrarlos tambien, ejecuta:                       ║
echo  ║    rmdir /s /q "%DATA%"
echo  ╚════════════════════════════════════════════════════════════╝
echo.
pause
