"""
import_osm.py — Importación de Redes OpenStreetMap para SUMO
=============================================================
Framework computacional para Tesis Doctoral: Control Semafórico Inteligente

Referencia Académica:
    Capítulo 5.5 - Validación en contextos reales/latinoamericanos
    Sección 3.2.3 - Pipeline de importación de datos geográficos

Este script convierte archivos .osm de OpenStreetMap a formato .net.xml
utilizable por SUMO, con configuración optimizada para tráfico urbano.

Fuentes de datos OSM recomendadas:
    • GeoFabrik: https://download.geofabrik.de/ (extractos por ciudad/región)
    • BBBike: https://extract.bbbike.org/ (extractos personalizados)
    • OSM Direct: https://www.openstreetmap.org/export (áreas pequeñas)

Uso:
    python scripts/import_osm.py --osm data/osm/bogota_centro.osm --name bogota
    python scripts/import_osm.py --osm data/osm/medellin.osm --name medellin --tls-mode static
    python scripts/import_osm.py --osm data/osm/santiago.osm --name santiago --no-traffic-lights

Parámetros:
    --osm: Ruta al archivo .osm de OpenStreetMap
    --name: Nombre identificador para la red generada
    --tls-mode: Tipo de semáforos: "actuated" (default), "static", "none"
    --projection: Proyección geográfica (default: EPSG:4326)
    --output-dir: Directorio de salida (default: sumo_configs/networks)
    --generate-routes: Generar archivo de rutas mínimas para validación
    --validate: Ejecutar prueba de conexión TraCI tras la conversión
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Asegurar que src/ esté en el PYTHONPATH ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import traci
    TRACI_AVAILABLE = True
except ImportError:
    TRACI_AVAILABLE = False
    logging.warning("TraCI no disponible. La validación se limitará a verificación de archivos.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tsc.import_osm")


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de validación
# ─────────────────────────────────────────────────────────────────────────────

def validate_osm_file(osm_path: Path) -> bool:
    """
    Valida que el archivo .osm exista y tenga estructura válida.
    
    Parameters
    ----------
    osm_path : Path
        Ruta al archivo .osm
    
    Returns
    -------
    bool
        True si el archivo es válido
    """
    if not osm_path.exists():
        logger.error(f"❌ Archivo no encontrado: {osm_path}")
        return False
    
    try:
        file_size = osm_path.stat().st_size
        logger.info(f"📄 Archivo OSM encontrado: {osm_path.name}")
        logger.info(f"   Tamaño: {file_size / 1024:.1f} KB ({file_size / 1024 / 1024:.2f} MB)")
        
        # Leer primeros bytes para validar estructura XML
        with open(osm_path, "r", encoding="utf-8") as f:
            header = f.read(500)
            
            if "<?xml" in header and "<osm" in header:
                logger.info("✅ Estructura XML OSM válida detectada")
                
                # Contar elementos básicos
                nodes = header.count("<node ")
                ways = header.count("<way ")
                relations = header.count("<relation ")
                
                logger.info(f"   Elementos detectados (preview): {nodes} nodos, {ways} vías, {relations} relaciones")
                return True
            else:
                logger.error("❌ El archivo no parece ser un OSM válido (falta etiqueta <osm>)")
                return False
                
    except PermissionError:
        logger.error(f"❌ Permiso denegado para leer: {osm_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Error al validar archivo: {e}")
        return False


def validate_netxml_output(netxml_path: Path) -> bool:
    """Valida que el archivo .net.xml generado sea legible."""
    if not netxml_path.exists():
        logger.error(f"❌ Archivo .net.xml no generado: {netxml_path}")
        return False
    
    try:
        file_size = netxml_path.stat().st_size
        logger.info(f"📄 Red SUMO generada: {netxml_path.name}")
        logger.info(f"   Tamaño: {file_size / 1024:.1f} KB")
        
        with open(netxml_path, "r", encoding="utf-8") as f:
            content = f.read(2000)
            
            # Verificar elementos esenciales
            has_network = "<network" in content or "<net>" in content
            has_edges = "<edge " in content
            has_nodes = "<node " in content
            
            if has_network and has_edges and has_nodes:
                logger.info("✅ Estructura .net.xml válida")
                
                # Contar semáforos si existen
                tl_count = content.count("<tl ")
                if tl_count > 0:
                    logger.info(f"   Semáforos detectados: {tl_count}")
                else:
                    logger.warning("   ⚠️  No se detectaron semáforos. Verificar parámetro --tls-mode")
                
                # Contar edges y nodes (aproximado)
                edge_count = content.count("<edge ")
                node_count = content.count("<node ")
                logger.info(f"   Aproximado: {edge_count} edges, {node_count} nodes")
                
                return True
            else:
                logger.error("❌ El archivo .net.xml parece estar corrupto o incompleto")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error al validar .net.xml: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Conversión OSM → NETXML
# ─────────────────────────────────────────────────────────────────────────────

def build_netconvert_command(
    osm_path: Path,
    output_path: Path,
    tls_mode: str = "actuated",
    projection: str = "EPSG:4326",
    remove_edge_types: Optional[List[str]] = None,
    additional_params: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    Construye el comando netconvert con parámetros optimizados.
    
    Parameters
    ----------
    osm_path : Path
        Ruta al archivo .osm de entrada
    output_path : Path
        Ruta para el archivo .net.xml de salida
    tls_mode : str
        Tipo de semáforos: "actuated", "static", "none"
    projection : str
        Proyección geográfica del archivo OSM
    remove_edge_types : list, optional
        Tipos de vías a excluir (default: footway, path, steps, pedestrian)
    additional_params : dict, optional
        Parámetros adicionales para netconvert
    
    Returns
    -------
    list
        Lista de argumentos para subprocess.run()
    """
    cmd = [
        "netconvert",
        f"--osm-files={osm_path}",
        f"--output-file={output_path}",
        f"--projection={projection}",
    ]
    
    # Configuración de semáforos
    if tls_mode == "none":
        cmd.append("--tls.no-signals=true")
    else:
        cmd.extend([
            "--tls.guess-signals=true",           # Detectar ubicación de semáforos
            f"--tls.default-type={tls_mode}",     # actuated o static
            "--tls.joining-detection=true",       # Unir semáforos cercanos en intersecciones
            "--tls.repair=true",                   # Reparar semáforos mal ubicados
        ])
    
    # Optimizaciones de geometría
    cmd.extend([
        "--geometry.remove",                      # Eliminar puntos de geometría innecesarios
        "--geometry.max-angle-fix=179.9",         # Corregir ángulos casi planos
        "--roundabouts.guess",                    # Detectar y modelar rotondas
        "--remove-edges.isolated",                # Eliminar edges sin conexión
        "--remove-edges.by-typehighway=footway",  # Eliminar vías peatonales
    ])
    
    # Tipos de vías a excluir
    default_remove = ["footway", "path", "steps", "pedestrian", "bridleway", "cycleway"]
    edge_types = remove_edge_types if remove_edge_types else default_remove
    
    for edge_type in edge_types:
        cmd.append(f"--remove-edges.by-type={edge_type}")
    
    # Parámetros adicionales opcionales
    if additional_params:
        for key, value in additional_params.items():
            cmd.append(f"--{key}={value}")
    
    # Logging
    cmd.extend([
        "--verbose",
        "--log.time=true",
        "--log.memory=true",
    ])
    
    return cmd


def convert_osm_to_netxml(
    osm_path: Path,
    output_path: Path,
    tls_mode: str = "actuated",
    projection: str = "EPSG:4326",
    remove_edge_types: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Ejecuta la conversión OSM → .net.xml.
    
    Parameters
    ----------
    osm_path : Path
        Ruta al archivo .osm de entrada
    output_path : Path
        Ruta para el archivo .net.xml de salida
    tls_mode : str
        Tipo de semáforos
    projection : str
        Proyección geográfica
    remove_edge_types : list, optional
        Tipos de vías a excluir
    dry_run : bool
        Si True, solo muestra el comando sin ejecutarlo
    
    Returns
    -------
    Path or None
        Ruta al archivo generado, o None si falló
    """
    # Asegurar directorio de salida
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("CONVERSIÓN OSM → NETXML")
    logger.info("=" * 60)
    logger.info(f"Entrada:  {osm_path.name} ({osm_path.parent})")
    logger.info(f"Salida:   {output_path.name} ({output_path.parent})")
    logger.info(f"TLS mode: {tls_mode}")
    logger.info(f"Proyección: {projection}")
    
    # Construir comando
    cmd = build_netconvert_command(
        osm_path=osm_path,
        output_path=output_path,
        tls_mode=tls_mode,
        projection=projection,
        remove_edge_types=remove_edge_types,
    )
    
    logger.debug(f"Comando: {' '.join(cmd)}")
    
    if dry_run:
        logger.info("🔍 DRY-RUN: Comando construido exitosamente")
        logger.info(f"   netconvert se ejecutaría con {len(cmd)} parámetros")
        return None
    
    # Ejecutar conversión
    logger.info("Ejecutando netconvert...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # No lanzar excepción automáticamente
            timeout=300,  # 5 minutos máximo
        )
        
        # Mostrar stderr (netconvert usa stderr para logs)
        if result.stderr:
            lines = result.stderr.strip().split('\n')
            
            # Filtrar y mostrar warnings importantes
            errors = [l for l in lines if 'ERROR' in l]
            warnings = [l for l in lines if 'WARNING' in l and 'No shape' not in l]
            
            if errors:
                logger.error(f"{len(errors)} errores durante la conversión:")
                for err in errors[:5]:
                    logger.error(f"  {err}")
            
            if warnings:
                logger.warning(f"{len(warnings)} advertencias:")
                for warn in warnings[:5]:
                    logger.warning(f"  {warn}")
        
        # Verificar código de retorno
        if result.returncode != 0:
            logger.error(f"❌ netconvert falló con código {result.returncode}")
            return None
        
        # Validar salida
        if validate_netxml_output(output_path):
            logger.info("✅ Conversión completada exitosamente")
            return output_path
        else:
            logger.error("❌ El archivo generado parece inválido")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout: La conversión tomó más de 5 minutos")
        logger.info("   Esto puede deberse a un archivo OSM muy grande.")
        logger.info("   Considere usar extractos más pequeños de GeoFabrik o BBBike.")
        return None
    except FileNotFoundError:
        logger.error("❌ netconvert no encontrado. Verificar instalación de SUMO.")
        logger.info("   En Windows: Asegúrese de que SUMO esté en el PATH")
        logger.info("   En Linux: sudo apt-get install sumo")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Generación de rutas sintéticas
# ─────────────────────────────────────────────────────────────────────────────

def generate_minimal_routes(
    netxml_path: Path,
    output_path: Path,
    simulation_time: int = 1800,
    demand_factor: float = 0.8,
) -> Optional[Path]:
    """
    Genera archivo de rutas mínimas para validación inicial.
    
    Parameters
    ----------
    netxml_path : Path
        Ruta al archivo .net.xml
    output_path : Path
        Ruta para el archivo .rou.xml de salida
    simulation_time : int
        Duración de la simulación en segundos
    demand_factor : float
        Factor de demanda vehicular
    
    Returns
    -------
    Path or None
        Ruta al archivo generado, o None si falló
    """
    logger.info(f"Generando rutas mínimas para validación: {output_path.name}")
    
    # Contenido básico de rutas
    vehs_per_hour = int(500 * demand_factor)
    
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!--
Rutas mínimas para validación de red
Generado automáticamente por import_osm.py
Red base: {netxml_path.name}
-->
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    
    <!-- Tipos de vehículo -->
    <vType id="car" length="4.5" minGap="2.5" maxSpeed="16.67" sigma="0.5" tau="1.0" />
    <vType id="truck" length="9.0" minGap="3.0" maxSpeed="11.11" sigma="0.3" tau="1.5" />
    
    <!-- Nota: Los edges específicos deben ajustarse según la red importada -->
    <!-- Este es un template genérico que requiere edición manual -->
    
    <flow id="flow_001" begin="0" end="{simulation_time}" 
          vehsPerHour="{vehs_per_hour}" departLane="random" departSpeed="desired">
        <route edges="edge_in edge_mid edge_out"/>
    </flow>
    
    <!-- 
    INSTRUCCIONES PARA EDICIÓN MANUAL:
    1. Abra el archivo .net.xml en NetEdit o un editor de texto
    2. Identifique los IDs de edges de entrada y salida principales
    3. Reemplace "edge_in edge_mid edge_out" con la secuencia real de edges
    4. Alternativamente, use duarouter para generar rutas automáticamente:
       duarouter --net-file {netxml_path.name} --route-files {output_path.name} ...
    -->
    
</routes>
'''
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"✅ Rutas mínimas generadas: {output_path}")
        logger.info("   ⚠️  NOTA: Las rutas requieren edición manual para ajustar los edge IDs")
        logger.info("   Use NetEdit o duarouter para generar rutas automáticas basadas en la red.")
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error al generar rutas: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Prueba de conexión TraCI
# ─────────────────────────────────────────────────────────────────────────────

def test_traci_connection(netxml_path: Path, route_path: Optional[Path] = None) -> bool:
    """
    Prueba de conexión TraCI con la red generada.
    
    Parameters
    ----------
    netxml_path : Path
        Ruta al archivo .net.xml
    route_path : Path, optional
        Ruta al archivo .rou.xml (opcional para prueba básica)
    
    Returns
    -------
    bool
        True si la conexión fue exitosa
    """
    if not TRACI_AVAILABLE:
        logger.warning("TraCI no disponible. Saltando prueba de conexión.")
        return True
    
    import time
    import uuid
    
    port = 8813 + int(uuid.uuid4().hex[:4], 16) % 1000
    logger.info(f"Probando conexión TraCI en puerto {port}...")
    
    # Comando SUMO
    cmd = [
        "sumo",
        "--net-file", str(netxml_path),
        "--start",
        f"--remote-port={port}",
        "--step-length=5",
        "--end=30",
        "--no-warnings",
        "--quit-on-end",
    ]
    
    if route_path and route_path.exists():
        cmd.extend(["--route-files", str(route_path)])
    
    try:
        # Iniciar SUMO
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        
        # Intentar conectar
        for attempt in range(5):
            try:
                traci.init(port=port)
                logger.info("✅ Conexión TraCI exitosa")
                
                # Información básica
                step = traci.simulation.getTime()
                loaded = traci.simulation.getLoadedVehiclesNumber()
                
                logger.info(f"   Paso actual: {step}s")
                logger.info(f"   Vehículos cargados: {loaded}")
                
                traci.close()
                proc.terminate()
                proc.wait(timeout=5)
                
                return True
                
            except ConnectionRefusedError:
                if attempt < 4:
                    time.sleep(1)
                continue
        
        proc.terminate()
        proc.wait(timeout=5)
        logger.error("❌ No se pudo establecer conexión TraCI")
        return False
        
    except FileNotFoundError:
        logger.error("❌ Binario 'sumo' no encontrado")
        return False
    except Exception as e:
        logger.error(f"❌ Error en prueba TraCI: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Importar redes OpenStreetMap (.osm) a formato SUMO (.net.xml)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/import_osm.py --osm data/osm/bogota.osm --name bogota
  python scripts/import_osm.py --osm data/osm/medellin.osm --name medellin --tls-mode static
  python scripts/import_osm.py --osm data/osm/city.osm --name city --dry-run

Fuentes de datos OSM recomendadas:
  • GeoFabrik: https://download.geofabrik.de/
  • BBBike: https://extract.bbbike.org/
  • OSM Direct: https://www.openstreetmap.org/export
        """,
    )
    
    parser.add_argument(
        "--osm",
        type=str,
        required=True,
        help="Ruta al archivo .osm de OpenStreetMap",
    )
    
    parser.add_argument(
        "--name",
        type=str,
        default="custom",
        help="Nombre identificador para la red generada (default: 'custom')",
    )
    
    parser.add_argument(
        "--tls-mode",
        type=str,
        choices=["actuated", "static", "none"],
        default="actuated",
        help="Tipo de semáforos: actuated (default), static, none",
    )
    
    parser.add_argument(
        "--projection",
        type=str,
        default="EPSG:4326",
        help="Proyección geográfica del archivo OSM (default: EPSG:4326)",
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="sumo_configs/networks",
        help="Directorio de salida (default: sumo_configs/networks)",
    )
    
    parser.add_argument(
        "--generate-routes",
        action="store_true",
        help="Generar archivo de rutas mínimas para validación",
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Ejecutar prueba de conexión TraCI tras la conversión",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo validar y mostrar comando sin ejecutar conversión",
    )
    
    args = parser.parse_args()
    
    # Paths
    osm_path = Path(args.osm)
    if not osm_path.is_absolute():
        osm_path = PROJECT_ROOT / osm_path
    
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    netxml_name = f"{args.name}.net.xml"
    netxml_path = output_dir / netxml_name
    
    route_name = f"{args.name}_minimal.rou.xml"
    route_path = output_dir.parent / "routes" / route_name
    
    # Validar archivo OSM
    logger.info("=" * 60)
    logger.info("IMPORTACIÓN DE RED OPENSTREETMAP")
    logger.info("=" * 60)
    
    if not validate_osm_file(osm_path):
        sys.exit(1)
    
    # Ejecutar conversión
    result_path = convert_osm_to_netxml(
        osm_path=osm_path,
        output_path=netxml_path,
        tls_mode=args.tls_mode,
        projection=args.projection,
        dry_run=args.dry_run,
    )
    
    if args.dry_run:
        logger.info("✅ Dry-run completado. Ejecute sin --dry-run para convertir.")
        return
    
    if result_path is None:
        logger.error("❌ Conversión fallida")
        sys.exit(1)
    
    # Generar rutas si se solicita
    if args.generate_routes:
        generate_minimal_routes(result_path, route_path)
    
    # Validar conexión TraCI si se solicita
    if args.validate:
        route_for_test = route_path if args.generate_routes else None
        test_traci_connection(result_path, route_for_test)
    
    # Resumen final
    logger.info("=" * 60)
    logger.info("✅ IMPORTACIÓN COMPLETADA")
    logger.info("=" * 60)
    logger.info(f"Red generada: {result_path}")
    if args.generate_routes:
        logger.info(f"Rutas generadas: {route_path}")
    
    logger.info("")
    logger.info("Próximos pasos:")
    logger.info(f"  1. Actualice config/default_config.yaml:")
    logger.info(f"     network.mode: \"custom\"")
    logger.info(f"     network.custom.osm_file: \"{args.osm}\"")
    logger.info(f"     network.custom.net_output: \"{result_path.relative_to(PROJECT_ROOT)}\"")
    logger.info("")
    logger.info(f"  2. Edite las rutas en {route_path} para ajustar los edge IDs")
    logger.info(f"     o use NetEdit para generar rutas visualmente.")
    logger.info("")
    logger.info("  3. Ejecute entrenamiento de prueba:")
    logger.info(f"     python scripts/train.py --timesteps 100 --n-envs 1")


if __name__ == "__main__":
    main()
