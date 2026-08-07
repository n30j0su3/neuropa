@echo off
REM ════════════════════════════════════════════════════════════════
REM  NeuroPA · Lanzador fácil para Windows
REM  Doble-click → arranca NeuroPA en tu navegador
REM ════════════════════════════════════════════════════════════════
setlocal ENABLEDELAYEDEXPANSION

REM Localiza el repo (busca carpeta con pyproject.toml)
set ROOTDIR=%~dp0..\
if not exist "%ROOTDIR%\pyproject.toml" set ROOTDIR=%USERPROFILE%\neuropa
if not exist "%ROOTDIR%\pyproject.toml" (
    echo.
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║  No encuentro NeuroPA.                           ║
    echo  ║  Ejecuta primero el instalador:                  ║
    echo  ║  irm https://n30j0su3.github.io/neuropa/install.ps1 | iex
    echo  ╚══════════════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)

echo.
echo  ▶ Iniciando NeuroPA...
echo.

cd /d "%ROOTDIR%"

REM Abre el navegador tras 3 segundos
start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8474"

REM Arranca el servidor (loopback). Ctrl+C para detener.
uv run neuropa --port 8474

endlocal
