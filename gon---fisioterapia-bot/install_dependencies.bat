@echo off
echo ============================================
echo Instalando dependencias del proyecto web
echo ============================================
echo.

cd /d "%~dp0"

echo Verificando Node.js...
node --version
if %errorlevel% neq 0 (
    echo ERROR: Node.js no esta instalado o no esta en el PATH
    echo Por favor:
    echo 1. Cierra esta ventana
    echo 2. Abre una NUEVA ventana de PowerShell
    echo 3. Ejecuta este script de nuevo
    pause
    exit /b 1
)

echo Verificando npm...
npm --version
if %errorlevel% neq 0 (
    echo ERROR: npm no esta disponible
    pause
    exit /b 1
)

echo.
echo Instalando dependencias...
npm install

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La instalacion fallo
    echo Intenta ejecutar manualmente: npm install
    pause
    exit /b 1
)

echo.
echo ============================================
echo EXITO! Dependencias instaladas correctamente
echo ============================================
echo.
echo El error de TypeScript deberia desaparecer ahora.
echo Cierra y vuelve a abrir el archivo tsconfig.json
echo.
pause
