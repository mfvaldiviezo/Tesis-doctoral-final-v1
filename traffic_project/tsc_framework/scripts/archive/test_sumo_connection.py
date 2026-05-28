#!/usr/bin/env python3
"""
test_sumo_connection.py — Diagnóstico de conexión SUMO/TraCI para Windows
============================================================================
Framework de Tesis Doctoral: Control Semafórico Inteligente con RL

Este script verifica:
1. Instalación de SUMO y variable SUMO_HOME
2. Disponibilidad del binario sumo.exe
3. Importación de TraCI
4. Generación de archivo .sumocfg temporal
5. Lanzamiento de SUMO y conexión TraCI

Uso en PowerShell (Windows):
    python scripts/test_sumo_connection.py

Salida esperada:
    ✓ SUMO_HOME configurado
    ✓ Binario sumo.exe encontrado
    ✓ TraCI importable
    ✓ Conexión establecida exitosamente
"""

import os
import sys
import subprocess
import time
import socket
import tempfile
from pathlib import Path

# Colores para output en terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_ok(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def log_info(msg):
    print(f"{Colors.CYAN}ℹ{Colors.RESET} {msg}")

def find_free_port():
    """Encuentra un puerto TCP libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def check_sumo_installation():
    """Verifica instalación de SUMO."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}1. Verificando instalación de SUMO{Colors.RESET}")
    print("="*60)
    
    # Verificar SUMO_HOME
    sumo_home = os.environ.get("SUMO_HOME", "")
    
    if not sumo_home:
        # Rutas típicas en Windows
        default_paths = [
            r"C:\Program Files (x86)\Eclipse\Sumo",
            r"C:\Program Files\Eclipse\Sumo",
        ]
        for path in default_paths:
            if os.path.exists(path):
                sumo_home = path
                log_ok(f"SUMO encontrado en ruta predeterminada: {sumo_home}")
                break
        
        if not sumo_home:
            log_error("SUMO_HOME no está configurado y no se encontró en rutas predeterminadas")
            log_warn("Instala SUMO desde: https://sumo.dlr.de/docs/Installing.html")
            return None, None
    else:
        log_ok(f"SUMO_HOME configurado: {sumo_home}")
    
    # Priorizar conda sumo (shutil.which) sobre SUMO_HOME/bin
    # El sumo.EXE del entorno conda (tsc-env) es el verificado como funcional
    import shutil
    sumo_binary = shutil.which("sumo")
    if sumo_binary:
        log_ok(f"Binario SUMO encontrado (conda/PATH): {sumo_binary}")
        return sumo_home, sumo_binary

    # Fallback a SUMO_HOME/bin
    if os.name == 'nt':
        candidate = os.path.join(sumo_home, "bin", "sumo.exe")
    else:
        candidate = "sumo"

    if os.path.exists(candidate) or os.name != 'nt':
        log_ok(f"Binario SUMO encontrado (SUMO_HOME): {candidate}")
        return sumo_home, candidate
    else:
        log_error(f"Binario sumo.exe no encontrado en: {candidate}")
        return sumo_home, None

def check_traci_import():
    """Verifica importación de TraCI."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}2. Verificando importación de TraCI{Colors.RESET}")
    print("="*60)
    
    try:
        import traci
        import traci.constants as tc
        log_ok("TraCI importado exitosamente")
        log_info(f"Versión disponible: {traci.__version__ if hasattr(traci, '__version__') else 'desconocida'}")
        return True
    except ImportError as e:
        log_error(f"No se pudo importar TraCI: {e}")
        log_warn("Intenta: pip install traci sumolib")
        return False

def create_test_sumocfg(network_file, route_file):
    """Crea un archivo .sumocfg temporal para pruebas."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}3. Creando archivo .sumocfg temporal{Colors.RESET}")
    print("="*60)
    
    tmp_dir = tempfile.gettempdir()
    sumocfg_path = os.path.join(tmp_dir, "test_intersection.sumocfg")
    
    sumocfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{network_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="100"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
    <report>
        <no-step-log value="true"/>
    </report>
</configuration>
'''
    
    with open(sumocfg_path, 'w', encoding='utf-8') as f:
        f.write(sumocfg_content)
    
    log_ok(f"Archivo .sumocfg creado: {sumocfg_path}")
    return sumocfg_path

def test_sumo_launch(sumo_binary, sumocfg_path, port):
    """Lanza SUMO y prueba conexión TraCI."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}4. Probando lanzamiento de SUMO y conexión TraCI{Colors.RESET}")
    print("="*60)
    
    cmd = [
        sumo_binary,
        "-c", sumocfg_path,
        "--remote-port", str(port),
        "--step-length", "5",
        "--no-step-log",
        # NOTA: --no-render NO existe en SUMO 1.26.0 (eliminado)
    ]
    
    log_info(f"Comando: {' '.join(cmd)}")
    
    # Configurar entorno
    env = os.environ.copy()
    if os.environ.get("SUMO_HOME"):
        env["SUMO_HOME"] = os.environ["SUMO_HOME"]
    
    # Windows: CREATE_NO_WINDOW para evitar popup
    creation_flags = 0
    if os.name == 'nt':
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            creation_flags = 0x08000000
    
    try:
        # Lanzar SUMO
        log_info("Iniciando proceso SUMO...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,   # PIPE para capturar errores de SUMO
            creationflags=creation_flags,
            env=env,
        )
        
        # Esperar inicialización
        time.sleep(2.0)
        
        # Verificar si el proceso sigue vivo
        if process.poll() is not None:
            log_error("El proceso SUMO terminó inmediatamente")
            stdout, stderr = process.communicate()
            if stderr:
                log_error(f"SUMO stderr: {stderr.decode('utf-8', errors='replace')[:600]}")
            return False
        
        log_ok("Proceso SUMO iniciado correctamente")
        
        # Conectar TraCI
        log_info(f"Conectando a localhost:{port}...")
        import traci
        
        max_retries = 5
        for i in range(max_retries):
            try:
                traci.init(port=port, numRetries=3)
                log_ok(f"¡Conexión TraCI establecida en puerto {port}!")
                
                # Probar comando básico
                sim_time = traci.simulation.getTime()
                log_info(f"Tiempo de simulación: {sim_time}s")
                
                # Cerrar
                traci.close()
                log_ok("Conexión cerrada correctamente")
                
                # Terminar proceso SUMO
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                return True
                
            except Exception as e:
                if i < max_retries - 1:
                    log_warn(f"Intento {i+1}/{max_retries} fallido: {e}")
                    time.sleep(1.0)
                else:
                    log_error(f"No se pudo conectar después de {max_retries} intentos: {e}")
                    process.terminate()
                    return False
                
    except FileNotFoundError:
        log_error(f"Binario no encontrado: {sumo_binary}")
        return False
    except Exception as e:
        log_error(f"Error inesperado: {e}")
        return False

def main():
    """Ejecuta diagnóstico completo."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}{'='*18} DIAGNÓSTICO SUMO/TraCI {'='*18}{Colors.RESET}")
    print(f"{Colors.CYAN}Framework TSC - Tesis Doctoral{Colors.RESET}")
    print("="*60)
    
    # 1. Verificar SUMO
    sumo_home, sumo_binary = check_sumo_installation()
    if not sumo_binary:
        print("\n" + "="*60)
        log_error("DIAGNÓSTICO FALLIDO: SUMO no está instalado correctamente")
        print("="*60)
        print("\nPasos a seguir:")
        print("1. Descarga SUMO desde: https://sumo.dlr.de/docs/Installing.html")
        print("2. Instala con opciones por defecto")
        print("3. Abre una NUEVA terminal y ejecuta:")
        print("   python scripts/test_sumo_connection.py")
        return 1
    
    # 2. Verificar TraCI
    if not check_traci_import():
        print("\n" + "="*60)
        log_error("DIAGNÓSTICO FALLIDO: TraCI no está disponible")
        print("="*60)
        return 1
    
    # 3. Verificar archivos de red
    script_dir = Path(__file__).parent.parent
    network_file = script_dir / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
    route_file = script_dir / "sumo_configs" / "routes" / "hangzhou" / "hangzhou_minimal.rou.xml"
    
    print("\n" + "="*60)
    print(f"{Colors.BOLD}Verificando archivos de red{Colors.RESET}")
    print("="*60)
    
    if network_file.exists():
        log_ok(f"Red encontrada: {network_file}")
    else:
        log_error(f"Red no encontrada: {network_file}")
        log_warn("Ejecuta: python scripts/generate_hangzhou_scenarios.py")
        return 1
    
    if route_file.exists():
        log_ok(f"Rutas encontradas: {route_file}")
    else:
        log_error(f"Rutas no encontradas: {route_file}")
        log_warn("Ejecuta: python scripts/generate_hangzhou_scenarios.py")
        return 1
    
    # 4. Crear .sumocfg temporal
    sumocfg_path = create_test_sumocfg(str(network_file), str(route_file))
    
    # 5. Probar conexión
    port = find_free_port()
    log_info(f"Puerto seleccionado: {port}")
    
    success = test_sumo_launch(sumo_binary, sumocfg_path, port)
    
    # Limpieza
    try:
        os.remove(sumocfg_path)
        log_info("Archivo temporal eliminado")
    except:
        pass
    
    # Resultado final
    print("\n" + "="*60)
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ DIAGNÓSTICO EXITOSO{Colors.RESET}")
        print("="*60)
        print("\n¡Tu configuración está lista para entrenar!")
        print("\nComando para entrenamiento:")
        print(f"  {Colors.CYAN}python scripts/train.py --config config/default_config.yaml --timesteps 10 --n-envs 1 --seed 42{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ DIAGNÓSTICO FALLIDO{Colors.RESET}")
        print("="*60)
        print("\nPosibles causas:")
        print("1. SUMO no está en el PATH del sistema")
        print("2. El archivo .net.xml es incompatible")
        print("3. El puerto está bloqueado por firewall")
        print("\nPara ayuda adicional, revisa:")
        print("  - QUICKSTART_WINDOWS.md")
        print("  - NETWORK_SETUP_GUIDE.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
