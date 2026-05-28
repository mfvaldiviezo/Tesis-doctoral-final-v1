# =============================================================================
# setup_sumo_windows.ps1
# Script de configuración para Eclipse SUMO en Windows
# Tesis Doctoral - Control Semafórico Inteligente con RL
# =============================================================================
# Este script:
# 1. Verifica la instalación de SUMO
# 2. Configura variables de entorno
# 3. Valida la red Hangzhou 4x4
# 4. Genera archivos .sumocfg si faltan
# =============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup SUMO para TSC Framework (Windows)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ── 1. Verificar instalación de SUMO ────────────────────────────────────────
$SUMO_HOME_DEFAULT = "C:\Program Files (x86)\Eclipse\Sumo"
$SUMO_HOME = $env:SUMO_HOME

if ([string]::IsNullOrEmpty($SUMO_HOME)) {
    if (Test-Path $SUMO_HOME_DEFAULT) {
        $SUMO_HOME = $SUMO_HOME_DEFAULT
        Write-Host "[INFO] SUMO encontrado en ruta predeterminada: $SUMO_HOME" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] SUMO no está instalado o no está en PATH" -ForegroundColor Red
        Write-Host "  Descarga e instala desde: https://sumo.dlr.de/docs/Installing.html" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[INFO] SUMO_HOME configurado: $SUMO_HOME" -ForegroundColor Green
}

# Verificar binario de SUMO
$SUMO_BINARY = Join-Path $SUMO_HOME "bin\sumo.exe"
if (Test-Path $SUMO_BINARY) {
    Write-Host "[OK] Binario SUMO encontrado: $SUMO_BINARY" -ForegroundColor Green
} else {
    # Intentar sin 'bin'
    $SUMO_BINARY = Join-Path $SUMO_HOME "sumo.exe"
    if (Test-Path $SUMO_BINARY) {
        Write-Host "[OK] Binario SUMO encontrado: $SUMO_BINARY" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Binario sumo.exe no encontrado" -ForegroundColor Red
        exit 1
    }
}

# ── 2. Configurar variables de entorno temporalmente ────────────────────────
$env:SUMO_HOME = $SUMO_HOME
$env:PATH = "$SUMO_HOME\bin;$env:PATH"
Write-Host "[INFO] Variables de entorno configuradas para esta sesión" -ForegroundColor Cyan

# ── 3. Verificar red Hangzhou 4x4 ───────────────────────────────────────────
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$NETWORK_FILE = Join-Path $SCRIPT_DIR "sumo_configs\networks\hangzhou_4x4.net.xml"

if (Test-Path $NETWORK_FILE) {
    Write-Host "[OK] Red Hangzhou 4x4 encontrada: $NETWORK_FILE" -ForegroundColor Green
    
    # Validar que contiene el semáforo B1
    $content = Get-Content $NETWORK_FILE -Raw
    if ($content -match 'id="B1"') {
        Write-Host "[OK] Semáforo B1 encontrado en la red" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Semáforo B1 no encontrado en la red" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ERROR] Red Hangzhou 4x4 no encontrada: $NETWORK_FILE" -ForegroundColor Red
    Write-Host "  Ejecuta: python scripts/generate_hangzhou_scenarios.py" -ForegroundColor Yellow
}

# ── 4. Verificar archivos de rutas ──────────────────────────────────────────
$ROUTE_DIR = Join-Path $SCRIPT_DIR "sumo_configs\routes\hangzhou"
if (Test-Path $ROUTE_DIR) {
    $routeFiles = Get-ChildItem -Path $ROUTE_DIR -Filter "*.rou.xml"
    Write-Host "[OK] Directorio de rutas encontrado: $ROUTE_DIR" -ForegroundColor Green
    Write-Host "       Archivos .rou.xml encontrados: $($routeFiles.Count)" -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] Directorio de rutas no encontrado: $ROUTE_DIR" -ForegroundColor Yellow
    Write-Host "  Ejecuta: python scripts/generate_hangzhou_scenarios.py" -ForegroundColor Yellow
}

# ── 5. Probar conexión TraCI ────────────────────────────────────────────────
Write-Host "`n[INFO] Probando conexión TraCI..." -ForegroundColor Cyan
try {
    $testScript = @"
import sys
sys.path.insert(0, '$SUMO_HOME\tools')
import traci
print("TraCI import OK")
"@
    $result = python -c $testScript 2>&1
    if ($result -match "TraCI import OK") {
        Write-Host "[OK] TraCI disponible" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] TraCI podría no estar configurado correctamente" -ForegroundColor Yellow
        Write-Host "  Resultado: $result" -ForegroundColor Gray
    }
} catch {
    Write-Host "[ERROR] Error al probar TraCI: $_" -ForegroundColor Red
}

# ── 6. Instrucciones finales ────────────────────────────────────────────────
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Configuración completada" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para ejecutar entrenamiento:" -ForegroundColor Cyan
Write-Host "  python scripts/train.py --config config/default_config.yaml --timesteps 10 --n-envs 1 --seed 42" -ForegroundColor White
Write-Host ""
Write-Host "Si persisten errores de conexión:" -ForegroundColor Yellow
Write-Host "  1. Verifica que SUMO esté instalado correctamente" -ForegroundColor Gray
Write-Host "  2. Asegúrate de que sumo.exe esté en el PATH" -ForegroundColor Gray
Write-Host "  3. Revisa que los archivos .net.xml y .rou.xml existan" -ForegroundColor Gray
Write-Host ""
