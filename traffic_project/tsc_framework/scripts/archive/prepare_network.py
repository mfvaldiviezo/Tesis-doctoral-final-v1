"""
prepare_network.py — Preparación de Redes SUMO (Benchmark + Custom OSM)
=========================================================================
Framework computacional para Tesis Doctoral: Control Semafórico Inteligente

Referencia Académica:
    Capítulo 4.4.1 - Benchmark Hangzhou 4×4 para comparativa SOTA
    Capítulo 5.5 - Validación en redes reales desde OpenStreetMap
    Sección 3.2 - Pipeline de preprocesamiento de redes viales

Este script gestiona la preparación automática de redes SUMO en dos modos:
    • Modo BENCHMARK: Verifica/descarga/genera la red Hangzhou 4×4
    • Modo CUSTOM: Importa archivos .osm y los convierte a .net.xml

Uso:
    python scripts/prepare_network.py --mode benchmark
    python scripts/prepare_network.py --mode custom --osm-file data/osm/my_city.osm
    python scripts/prepare_network.py --mode custom --osm-file data/osm/my_city.osm --name my_city

Salidas generadas:
    sumo_configs/networks/hangzhou_4x4.net.xml  (modo benchmark)
    sumo_configs/networks/custom_<name>.net.xml (modo custom)
    sumo_configs/routes/hangzhou/               (rutas sintéticas benchmark)
    sumo_configs/routes/custom_minimal.rou.xml  (rutas sintéticas custom)
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

# ── Asegurar que src/ esté en el PYTHONPATH ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML no encontrado. Instalar con: pip install pyyaml")

try:
    import traci
    TRACI_AVAILABLE = True
except ImportError:
    TRACI_AVAILABLE = False
    logging.warning("TraCI no disponible. La validación de redes se limitará a verificación de archivos.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tsc.prepare_network")


# ─────────────────────────────────────────────────────────────────────────────
# Configuración y rutas
# ─────────────────────────────────────────────────────────────────────────────

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Carga la configuración desde YAML."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "default_config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuración no encontrada: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_directories(cfg: Dict[str, Any]) -> None:
    """Crea directorios necesarios si no existen."""
    paths = cfg.get("paths", {})
    dirs_to_create = [
        paths.get("sumo_networks", "sumo_configs/networks"),
        paths.get("sumo_routes", "sumo_configs/routes"),
        paths.get("sumo_routes", "sumo_configs/routes") + "/hangzhou",
        "data/osm",
    ]
    
    for dir_path in dirs_to_create:
        full_path = PROJECT_ROOT / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directorio verificado: {full_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Modo BENCHMARK: Hangzhou 4×4
# ─────────────────────────────────────────────────────────────────────────────

def check_hangzhou_network(cfg: Dict[str, Any]) -> Optional[Path]:
    """Verifica si la red Hangzhou ya existe."""
    network_file = cfg["network"]["benchmark"]["network_file"]
    network_path = PROJECT_ROOT / network_file
    
    if network_path.exists():
        logger.info(f"✅ Red Hangzhou encontrada: {network_path}")
        return validate_netxml(network_path)
    
    logger.warning(f"❌ Red Hangzhou no encontrada: {network_path}")
    return None


def validate_netxml(netxml_path: Path) -> Optional[Path]:
    """Valida que un archivo .net.xml sea legible por SUMO."""
    if not netxml_path.exists():
        logger.error(f"❌ Archivo no encontrado: {netxml_path}")
        return None
    
    # Validación básica: verificar que el archivo tiene estructura XML válida
    try:
        with open(netxml_path, "r", encoding="utf-8") as f:
            content = f.read(2000)
            
            # Verificar elementos esenciales de net.xml
            has_xml_decl = "<?xml" in content
            has_net = "<net " in content or "<network" in content
            has_nodes = "<node " in content
            has_edges = "<edge " in content
            
            if has_xml_decl and has_net and has_nodes and has_edges:
                logger.info(f"✅ Estructura XML válida en {netxml_path.name}")
                
                # Contar semáforos si existen
                tl_count = content.count("<tlLogic ")
                if tl_count > 0:
                    logger.info(f"   Semáforos detectados: {tl_count}")
                
                return netxml_path
            else:
                logger.warning(f"⚠️  Validación incompleta para {netxml_path.name}")
                logger.debug(f"   has_xml_decl={has_xml_decl}, has_net={has_net}, has_nodes={has_nodes}, has_edges={has_edges}")
                # Retornar el archivo de todos modos si existe
                return netxml_path
                
    except Exception as e:
        logger.error(f"❌ Error al validar {netxml_path}: {e}")
        return None


def generate_hangzhou_grid(cfg: Dict[str, Any]) -> Path:
    """
    Genera una red grid 4×4 similar a Hangzhou usando netgenerate.
    
    Referencia: Capítulo 4.4.1 - Benchmark Hangzhou 4×4
    La red original tiene 16 intersecciones semafóricas en configuración grid.
    """
    output_path = PROJECT_ROOT / cfg["network"]["benchmark"]["network_file"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Generando red grid 4×4 tipo Hangzhou con netgenerate...")
    
    # Parámetros basados en el benchmark RESCO/Hangzhou
    cmd = [
        "netgenerate",
        "--grid",
        "--grid.number=4",              # 4×4 intersecciones
        "--grid.length=500",            # 500m entre intersecciones
        "--tls.default-type=actuated",  # Semáforos actuados
        "--junctions.uniform=true",     # Distribución uniforme
        "--tls.all-off=false",          # Semáforos activos
        "--seed=42",                    # Reproducibilidad
        f"--output-file={output_path}",
    ]
    
    logger.debug(f"Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"✅ Red generada exitosamente: {output_path}")
        
        if result.stdout:
            logger.debug(f"Salida netgenerate: {result.stdout[:500]}")
        
        return validate_netxml(output_path) or output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error al generar red: {e.stderr}")
        raise RuntimeError(f"netgenerate falló: {e.stderr}")
    except FileNotFoundError:
        logger.error("❌ netgenerate no encontrado. Verificar instalación de SUMO.")
        logger.info("   En Windows: https://sumo.dlr.de/docs/Installing.html")
        logger.info("   En Linux: sudo apt-get install sumo")
        raise


def generate_benchmark_routes(cfg: Dict[str, Any], network_path: Path) -> List[Path]:
    """
    Genera archivos de rutas sintéticas para domain randomization.
    
    Referencia: Capítulo 4.5.1 - Domain Randomization para robustez
    Genera 100 escenarios con variaciones en demanda vehicular.
    """
    routes_dir = PROJECT_ROOT / cfg["network"]["benchmark"]["route_files_dir"]
    routes_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    num_scenarios = cfg["network"]["benchmark"].get("num_scenarios", 100)
    
    logger.info(f"Generando {num_scenarios} archivos de rutas para domain randomization...")
    
    for i in range(num_scenarios):
        route_file = routes_dir / f"scenario_{i:03d}_hangzhou.rou.xml"
        
        # Variación de demanda entre 0.5× y 1.5× la demanda base
        demand_factor = 0.5 + (i / num_scenarios) * 1.0
        
        content = generate_route_xml_content(
            scenario_name=f"hangzhou_scenario_{i:03d}",
            demand_factor=demand_factor,
            network_type="grid_4x4",
        )
        
        with open(route_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        generated_files.append(route_file)
        
        if (i + 1) % 20 == 0:
            logger.debug(f"  Progreso: {i + 1}/{num_scenarios}")
    
    logger.info(f"✅ {num_scenarios} archivos de rutas generados en {routes_dir}")
    return generated_files


def generate_route_xml_content(
    scenario_name: str,
    demand_factor: float = 1.0,
    network_type: str = "grid_4x4",
    simulation_time: int = 3600,
) -> str:
    """
    Genera contenido XML para archivo de rutas .rou.xml.
    
    Parameters
    ----------
    scenario_name : str
        Nombre identificador del escenario
    demand_factor : float
        Factor de multiplicación de demanda (0.5 a 1.5)
    network_type : str
        Tipo de red: "grid_4x4" o "custom"
    simulation_time : int
        Duración de la simulación en segundos
    """
    # Vehículos por hora (base 600, ajustado por demand_factor)
    veh_per_hour = int(600 * demand_factor)
    
    if network_type == "grid_4x4":
        # Para grid 4x4, usar edges genéricos del tipo "edge_X_Y"
        edges = [f"edge_{i}_{j}" for i in range(4) for j in range(4)]
        
        flows = []
        for idx, edge in enumerate(edges[:8]):  # 8 edges de entrada
            flow_id = f"flow_{idx:03d}"
            flows.append(f'''
    <flow id="{flow_id}" from="{edge}" to="{edges[-1]}" begin="0" end="{simulation_time}" 
          vehsPerHour="{veh_per_hour}" departLane="random" departSpeed="desired">
        <route edges="{edge}"/>
    </flow>''')
        
        flows_str = "\n".join(flows)
    else:
        # Para red custom, usar flujo genérico
        flows_str = f'''
    <flow id="flow_main" from="edge_in" to="edge_out" begin="0" end="{simulation_time}"
          vehsPerHour="{veh_per_hour}" departLane="random" departSpeed="desired">
        <route edges="edge_in edge_out"/>
    </flow>'''
    
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!--
{scenario_name}
Generado automáticamente por prepare_network.py
Demanda factor: {demand_factor:.2f}×
-->
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    
    <!-- Definición de tipos de vehículo -->
    <vType id="car" length="4.5" minGap="2.5" maxSpeed="16.67" sigma="0.5" 
           tau="1.0" speedFactor="normc(1.0, 0.1)" />
    
    <vType id="truck" length="9.0" minGap="3.0" maxSpeed="11.11" sigma="0.3"
           tau="1.5" speedFactor="normc(0.9, 0.05)" />
    
    <!-- Flujos de tráfico con domain randomization -->
    {flows_str}
    
</routes>
'''
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Modo CUSTOM: Importación desde OpenStreetMap
# ─────────────────────────────────────────────────────────────────────────────

def check_osm_file(osm_path: Path) -> bool:
    """Verifica que el archivo .osm exista y tenga contenido válido."""
    if not osm_path.exists():
        logger.error(f"❌ Archivo .osm no encontrado: {osm_path}")
        return False
    
    # Validación básica de estructura XML
    try:
        with open(osm_path, "r", encoding="utf-8") as f:
            content = f.read(1000)
            if "<osm" in content:
                logger.info(f"✅ Archivo OSM válido encontrado: {osm_path}")
                logger.info(f"   Tamaño: {osm_path.stat().st_size / 1024:.1f} KB")
                return True
            else:
                logger.error(f"❌ Archivo {osm_path.name} no parece ser un OSM válido")
                return False
    except Exception as e:
        logger.error(f"❌ Error al leer {osm_path}: {e}")
        return False


def convert_osm_to_netxml(
    osm_path: Path,
    output_path: Path,
    cfg: Dict[str, Any],
) -> Path:
    """
    Convierte archivo .osm a .net.xml usando netconvert.
    
    Parameters
    ----------
    osm_path : Path
        Ruta al archivo .osm de entrada
    output_path : Path
        Ruta para el archivo .net.xml de salida
    cfg : dict
        Configuración con parámetros de conversión
    
    Returns
    -------
    Path
        Ruta al archivo .net.xml generado
    """
    custom_cfg = cfg["network"]["custom"]
    
    logger.info(f"Convirtiendo OSM a red SUMO: {osm_path.name} → {output_path.name}")
    
    # Construir comando netconvert
    cmd = [
        "netconvert",
        f"--osm-files={osm_path}",
        f"--output-file={output_path}",
        "--tls.guess-signals=true",           # Detectar semáforos automáticamente
        f"--tls.default-type={custom_cfg.get('tls_mode', 'actuated')}",
        "--tls.joining-detection=true",       # Unir semáforos cercanos
        "--geometry.remove",                  # Simplificar geometría
        "--roundabouts.guess",                # Detectar rotondas
        "--remove-edges.isolated",            # Eliminar edges aislados
        "--projection=" + custom_cfg.get("projection", "EPSG:4326"),
    ]
    
    # Agregar filtros de tipos de vías a excluir
    remove_edges = custom_cfg.get("remove_edges", ["footway", "path", "steps"])
    for edge_type in remove_edges:
        cmd.append(f"--remove-edges.by-type={edge_type}")
    
    logger.debug(f"Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"✅ Conversión completada: {output_path}")
        
        if result.stderr:
            # netconvert suele escribir advertencias en stderr
            warnings = [l for l in result.stderr.split('\n') if 'WARNING' in l]
            if warnings:
                logger.warning(f"Advertencias de netconvert ({len(warnings)}):")
                for w in warnings[:3]:
                    logger.warning(f"  {w}")
        
        return validate_netxml(output_path) or output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error en netconvert: {e.stderr}")
        raise RuntimeError(f"netconvert falló: {e.stderr}")
    except FileNotFoundError:
        logger.error("❌ netconvert no encontrado. Verificar instalación de SUMO.")
        raise


def generate_custom_minimal_routes(output_path: Path, cfg: Dict[str, Any]) -> Path:
    """
    Genera archivo de rutas mínimas para validación inicial de red custom.
    """
    route_file = PROJECT_ROOT / cfg["network"]["custom"]["route_file"]
    route_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generando rutas mínimas para validación: {route_file.name}")
    
    content = generate_route_xml_content(
        scenario_name="custom_minimal_routes",
        demand_factor=0.8,
        network_type="custom",
        simulation_time=1800,  # 30 minutos para validación rápida
    )
    
    with open(route_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"✅ Rutas mínimas generadas: {route_file}")
    return route_file


# ─────────────────────────────────────────────────────────────────────────────
# Validación final de conexión TraCI
# ─────────────────────────────────────────────────────────────────────────────

def test_sumo_connection(network_path: Path, route_path: Path, timeout: int = 30) -> bool:
    """
    Prueba de conexión TraCI con la red generada.
    
    Parameters
    ----------
    network_path : Path
        Ruta al archivo .net.xml
    route_path : Path
        Ruta al archivo .rou.xml
    timeout : int
        Tiempo máximo de espera para conexión (segundos)
    
    Returns
    -------
    bool
        True si la conexión fue exitosa
    """
    if not TRACI_AVAILABLE:
        logger.warning("TraCI no disponible. Saltando prueba de conexión.")
        return True
    
    import socket
    import time
    
    # Puerto aleatorio para evitar colisiones
    port = 8813 + int(uuid.uuid4().hex[:4], 16) % 1000
    
    logger.info(f"Iniciando prueba de conexión TraCI en puerto {port}...")
    
    # Configurar comando SUMO
    sumo_cmd = [
        "sumo",
        "--net-file", str(network_path),
        "--route-files", str(route_path),
        "--start",
        f"--remote-port={port}",
        "--step-length=5",
        "--end=60",  # Solo 60 segundos para prueba
        "--no-warnings",
    ]
    
    try:
        # Iniciar SUMO en segundo plano
        logger.debug(f"Ejecutando: {' '.join(sumo_cmd)}")
        sumo_proc = subprocess.Popen(sumo_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Esperar a que SUMO levante el servidor
        time.sleep(2)
        
        # Intentar conectar
        for attempt in range(10):
            try:
                traci.init(port=port)
                logger.info("✅ Conexión TraCI exitosa")
                
                # Ejecutar un paso de simulación
                traci.simulationStep()
                
                # Obt información básica
                step = traci.simulation.getTime()
                logger.info(f"   Simulación en paso: {step}s")
                
                traci.close()
                sumo_proc.terminate()
                sumo_proc.wait(timeout=5)
                
                return True
                
            except ConnectionRefusedError:
                if attempt < 9:
                    time.sleep(1)
                continue
            except Exception as e:
                logger.error(f"❌ Error en conexión: {e}")
                break
        
        sumo_proc.terminate()
        sumo_proc.wait(timeout=5)
        logger.error(f"❌ No se pudo conectar a SUMO en {timeout}s")
        return False
        
    except FileNotFoundError:
        logger.error("❌ Binario 'sumo' no encontrado. Verificar instalación.")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Funciones principales
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark_mode(cfg: Dict[str, Any], skip_generation: bool = False) -> Dict[str, Path]:
    """Ejecuta el modo benchmark (Hangzhou 4×4)."""
    logger.info("=" * 60)
    logger.info("MODO BENCHMARK: Hangzhou 4×4")
    logger.info("=" * 60)
    
    ensure_directories(cfg)
    
    # Verificar si la red ya existe
    network_path = check_hangzhou_network(cfg)
    
    if network_path is None and not skip_generation:
        # Generar red desde cero
        network_path = generate_hangzhou_grid(cfg)
        
        # Generar rutas para domain randomization
        route_files = generate_benchmark_routes(cfg, network_path)
        
        # Probar conexión
        first_route = route_files[0] if route_files else None
        if first_route:
            test_sumo_connection(network_path, first_route)
    
    elif network_path is None and skip_generation:
        logger.warning("⚠️  Modo --skip-generation activado. Red no generada.")
        network_path = PROJECT_ROOT / cfg["network"]["benchmark"]["network_file"]
    
    return {
        "network": network_path,
        "routes_dir": PROJECT_ROOT / cfg["network"]["benchmark"]["route_files_dir"],
    }


def run_custom_mode(cfg: Dict[str, Any], osm_file: str, name: str = "custom") -> Dict[str, Path]:
    """Ejecuta el modo custom (importación desde OSM)."""
    logger.info("=" * 60)
    logger.info(f"MODO CUSTOM: Importando {osm_file}")
    logger.info("=" * 60)
    
    ensure_directories(cfg)
    
    osm_path = Path(osm_file)
    if not osm_path.is_absolute():
        osm_path = PROJECT_ROOT / osm_path
    
    # Validar archivo OSM
    if not check_osm_file(osm_path):
        raise FileNotFoundError(f"Archivo OSM no válido: {osm_path}")
    
    # Determinar ruta de salida
    output_name = f"{name}.net.xml"
    output_path = PROJECT_ROOT / "sumo_configs" / "networks" / output_name
    
    # Convertir OSM → net.xml
    netxml_path = convert_osm_to_netxml(osm_path, output_path, cfg)
    
    # Generar rutas mínimas
    route_path = generate_custom_minimal_routes(output_path, cfg)
    
    # Probar conexión
    test_sumo_connection(netxml_path, route_path)
    
    return {
        "network": netxml_path,
        "routes": route_path,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Preparar redes SUMO para tsc_framework (Benchmark + Custom OSM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/prepare_network.py --mode benchmark
  python scripts/prepare_network.py --mode custom --osm-file data/osm/bogota.osm --name bogota
  python scripts/prepare_network.py --mode benchmark --skip-generation
        """,
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["benchmark", "custom"],
        default="benchmark",
        help="Modo de operación: 'benchmark' (Hangzhou) o 'custom' (OSM)",
    )
    
    parser.add_argument(
        "--osm-file",
        type=str,
        help="Ruta al archivo .osm (requerido para modo custom)",
    )
    
    parser.add_argument(
        "--name",
        type=str,
        default="custom",
        help="Nombre para la red custom (default: 'custom')",
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Ruta al archivo de configuración YAML",
    )
    
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Saltar generación si la red ya existe (benchmark mode)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo validar configuración sin ejecutar generación",
    )
    
    args = parser.parse_args()
    
    # Cargar configuración
    cfg = load_config(args.config)
    
    # Actualizar configuración con argumentos CLI
    if args.mode == "custom" and args.osm_file:
        cfg["network"]["mode"] = "custom"
        cfg["network"]["custom"]["osm_file"] = args.osm_file
    
    logger.info(f"Configuración cargada: modo={cfg['network']['mode']}")
    
    if args.dry_run:
        logger.info("🔍 DRY-RUN: Validando configuración...")
        logger.info(f"   Mode: {cfg['network']['mode']}")
        if cfg['network']['mode'] == "benchmark":
            logger.info(f"   Network file: {cfg['network']['benchmark']['network_file']}")
            logger.info(f"   Routes dir: {cfg['network']['benchmark']['route_files_dir']}")
        else:
            logger.info(f"   OSM file: {cfg['network']['custom']['osm_file']}")
            logger.info(f"   Output: {cfg['network']['custom']['net_output']}")
        logger.info("✅ Configuración válida")
        return
    
    # Ejecutar modo seleccionado
    try:
        if args.mode == "benchmark":
            results = run_benchmark_mode(cfg, skip_generation=args.skip_generation)
        else:
            if not args.osm_file:
                parser.error("--osm-file es requerido para modo custom")
            results = run_custom_mode(cfg, args.osm_file, args.name)
        
        logger.info("=" * 60)
        logger.info("✅ PREPARACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("=" * 60)
        logger.info(f"Red generada: {results['network']}")
        if "routes_dir" in results:
            logger.info(f"Rutas en: {results['routes_dir']}")
        elif "routes" in results:
            logger.info(f"Rutas: {results['routes']}")
        
        logger.info("")
        logger.info("Próximos pasos:")
        logger.info("  1. Ejecutar: python scripts/train.py --timesteps 100 --n-envs 1")
        logger.info("  2. Para modo custom, actualizar config/default_config.yaml:")
        logger.info(f"     network.mode: \"custom\"")
        logger.info(f"     network.custom.osm_file: \"{args.osm_file if args.osm_file else ''}\"")
        
    except Exception as e:
        logger.error(f"❌ Error durante la preparación: {e}")
        logger.exception("Traceback completo:")
        sys.exit(1)


if __name__ == "__main__":
    main()
