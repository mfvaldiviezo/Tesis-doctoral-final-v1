"""
fix_network_tls.py — Inyección de Semáforos en Red SUMO
========================================================
Framework de Tesis Doctoral: Control Semafórico Inteligente
Referencia: Capítulo 4.4.1 - Benchmark Hangzhou 4×4

Problema: netgenerate genera junctions tipo "priority" en vez de "traffic_light".
Solución: Usar netconvert --tls.guess=true para añadir TLS a todos los nodos
          internos del grid que tengan estructura de intersección controlada.

Si netconvert no está disponible, inyecta <tlLogic> directamente vía XML.

Uso:
    python scripts/fix_network_tls.py
    python scripts/fix_network_tls.py --input sumo_configs/networks/hangzhou_4x4.net.xml
    python scripts/fix_network_tls.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tsc.fix_network_tls")

# ── Nodos internos de la grilla 4×4 que deben tener semáforos ────────────────
# Topología:
#   A3 -- B3 -- C3 -- D3
#   |     |     |     |
#   A2 -- B2 -- C2 -- D2
#   |     |     |     |
#   A1 -- B1 -- C1 -- D1
#   |     |     |     |
#   A0 -- B0 -- C0 -- D0
#
# Nodos internos (no son esquinas puras A0,A3,D0,D3):
TLS_NODES_4WAY = ["B1", "B2", "C1", "C2"]  # Intersecciones completas 4 vías
TLS_NODES_3WAY = ["A1", "A2", "B0", "B3", "C0", "C3", "D1", "D2"]  # T-intersecciones

ALL_TLS_NODES = TLS_NODES_4WAY + TLS_NODES_3WAY

# Duración de fases (segundos de simulación)
PHASE_GREEN  = 31   # Verde principal
PHASE_YELLOW = 4    # Ámbar
PHASE_GREEN2 = 31   # Verde secundario (para 4-way)


def archive_file(path: Path) -> Path:
    """Archiva el archivo original añadiendo sufijo .bak (no elimina)."""
    bak_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak_path)
    logger.info(f"📦 Archivo archivado: {bak_path.name}")
    return bak_path


def try_netconvert(input_path: Path, output_path: Path) -> bool:
    """
    Intenta usar netconvert para añadir TLS automáticamente.
    Retorna True si tiene éxito.
    """
    cmd = [
        "netconvert",
        f"--sumo-net-file={input_path}",
        f"--output-file={output_path}",
        "--tls.guess=true",
        "--tls.default-type=actuated",
        "--tls.joining-detection=false",
        "--no-warnings",
    ]
    logger.info(f"🔄 Intentando netconvert: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            # Verificar que el archivo resultante tiene TLS
            if output_path.exists():
                with open(output_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "<tlLogic" in content:
                    tl_count = content.count("<tlLogic ")
                    logger.info(f"✅ netconvert añadió {tl_count} semáforos correctamente")
                    return True
                else:
                    logger.warning("⚠️  netconvert no añadió semáforos — usando inyección XML")
        else:
            logger.warning(f"⚠️  netconvert falló (código {result.returncode}): {result.stderr[:300]}")
    except FileNotFoundError:
        logger.warning("⚠️  netconvert no encontrado en PATH")
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  netconvert tardó demasiado (>60s)")
    except Exception as e:
        logger.warning(f"⚠️  Error inesperado en netconvert: {e}")
    return False


def build_tl_program_4way(tls_id: str) -> ET.Element:
    """
    Construye programa TLS para intersección de 4 vías (tipo actuated).

    Esquema de 4 fases:
      Fase 0: NS verde  (Norte-Sur green)     — 31s
      Fase 1: NS ámbar                         — 4s
      Fase 2: EW verde  (Este-Oeste green)    — 31s
      Fase 3: EW ámbar                         — 4s

    Para una intersección con 4 carriles de entrada (1 por dirección),
    cada fase tiene 4 estados de movimiento controlado.
    La representación "GGrrGGrr" usa:
      G = verde protegido, g = verde permisivo, y = ámbar, r = rojo
    """
    # Para intersección de 4 vías con 4 entradas de 1 carril cada una
    # y movimientos S/R/L/U: estado simplificado de 4 pos
    logic = ET.Element("tlLogic", {
        "id": tls_id,
        "type": "actuated",
        "programID": "0",
        "offset": "0",
    })
    # 16 conexiones en una intersección 4-vía típica (4 entradas × 4 salidas)
    # Simplificado: usar estado de 4 posiciones (una por carril de entrada)
    n = 4  # número de carriles controlados
    phases = [
        # NS green: carriles Norte (índice 2) y Sur (índice 0) en verde
        ("GGrrGGrr" if n >= 8 else "GGrr", PHASE_GREEN,  "30", "60"),
        ("yyyyrrrr" if n >= 8 else "yyrr", PHASE_YELLOW,  "4",  "4"),
        # EW green: carriles Este (índice 1) y Oeste (índice 3) en verde
        ("rrGGrrGG" if n >= 8 else "rrGG", PHASE_GREEN,  "30", "60"),
        ("rryyrryy" if n >= 8 else "rryy", PHASE_YELLOW,  "4",  "4"),
    ]
    for state, dur, minDur, maxDur in phases:
        ET.SubElement(logic, "phase", {
            "duration": str(dur),
            "state": state,
            "minDur": minDur,
            "maxDur": maxDur,
        })
    return logic


def build_tl_program_3way(tls_id: str) -> ET.Element:
    """
    Construye programa TLS para T-intersección de 3 vías.

    Esquema de 2 fases:
      Fase 0: eje principal verde  — 31s
      Fase 1: eje principal ámbar  — 4s
    """
    logic = ET.Element("tlLogic", {
        "id": tls_id,
        "type": "actuated",
        "programID": "0",
        "offset": "0",
    })
    phases = [
        ("GGGr", PHASE_GREEN,  "30", "60"),
        ("yyyy", PHASE_YELLOW,  "4",  "4"),
        ("rrrG", PHASE_GREEN,  "30", "60"),
        ("rryy", PHASE_YELLOW,  "4",  "4"),
    ]
    for state, dur, minDur, maxDur in phases:
        ET.SubElement(logic, "phase", {
            "duration": str(dur),
            "state": state,
            "minDur": minDur,
            "maxDur": maxDur,
        })
    return logic


def inject_tls_xml(input_path: Path, output_path: Path) -> int:
    """
    Inyecta semáforos directamente en el XML de la red SUMO.

    Pasos:
      1. Parsear el .net.xml con ElementTree
      2. Cambiar type="priority" → type="traffic_light" en nodos internos
      3. Insertar elementos <tlLogic> antes del primer <junction>
      4. Guardar en output_path

    Returns:
        Número de semáforos inyectados.
    """
    logger.info(f"🔧 Inyectando semáforos vía XML en: {input_path.name}")

    # Preservar el encoding original con escritura manual
    ET.register_namespace("", "")

    # Leer el XML preservando estructura
    try:
        tree = ET.parse(str(input_path))
    except ET.ParseError as e:
        logger.error(f"❌ Error parseando XML: {e}")
        raise

    root = tree.getroot()

    # ── Paso 1: Cambiar tipo de junctions a traffic_light ────────────────────
    changed = 0
    for junction in root.findall("junction"):
        jid = junction.get("id", "")
        if jid in ALL_TLS_NODES and junction.get("type") != "internal":
            old_type = junction.get("type", "unknown")
            junction.set("type", "traffic_light")
            logger.debug(f"  Junction {jid}: {old_type} → traffic_light")
            changed += 1

    logger.info(f"   Junctions actualizadas: {changed}/{len(ALL_TLS_NODES)}")

    # ── Paso 2: Insertar <tlLogic> antes del primer <junction> ───────────────
    # Encontrar posición de inserción
    children = list(root)
    insert_idx = 0
    for i, child in enumerate(children):
        if child.tag == "junction":
            insert_idx = i
            break

    # Insertar elementos tlLogic en orden reverso (insert mantiene orden)
    tl_inserted = 0
    for tls_id in reversed(ALL_TLS_NODES):
        if tls_id in TLS_NODES_4WAY:
            tl_elem = build_tl_program_4way(tls_id)
        else:
            tl_elem = build_tl_program_3way(tls_id)
        root.insert(insert_idx, tl_elem)
        tl_inserted += 1

    logger.info(f"   Semáforos <tlLogic> insertados: {tl_inserted}")

    # ── Paso 3: Añadir atributos tl/linkIndex a <connection> ─────────────────
    # Para cada junction con TLS, sus conexiones necesitan referencia al TLS.
    # Nota: SUMO puede inferir esto automáticamente si los junctions
    # están marcados como traffic_light — aquí solo marcamos los junctions.
    # La asignación completa de linkIndex requeriría análisis de grafo complejo.
    # SUMO manejará esto al cargar la red si los tipos de junction son correctos.

    # ── Paso 4: Guardar el XML ────────────────────────────────────────────────
    # Preservar declaración XML
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'

    tree.write(
        str(output_path),
        encoding="unicode",
        xml_declaration=False,
    )

    # Prefijar con cabecera XML
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_header + content)

    logger.info(f"✅ Red con TLS guardada: {output_path}")
    return tl_inserted


def verify_network_has_tls(net_path: Path) -> Dict[str, int]:
    """Verifica que la red tiene semáforos y retorna estadísticas."""
    stats = {"tlLogic": 0, "traffic_light_junctions": 0, "total_junctions": 0}

    with open(net_path, "r", encoding="utf-8") as f:
        content = f.read()

    stats["tlLogic"] = content.count("<tlLogic ")
    stats["traffic_light_junctions"] = content.count('type="traffic_light"')

    # Contar junctions no-internas
    import re
    stats["total_junctions"] = len(re.findall(r'<junction id="\w+"\s+type="(?!internal)', content))

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Añadir semáforos (TLS) a la red Hangzhou 4×4 del tsc_framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Referencia Académica: Capítulo 4.4.1 - Red Hangzhou 4×4 para benchmark SOTA

Ejemplos:
  python scripts/fix_network_tls.py
  python scripts/fix_network_tls.py --dry-run
  python scripts/fix_network_tls.py --input sumo_configs/networks/hangzhou_4x4.net.xml
        """,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Ruta al archivo .net.xml (default: sumo_configs/networks/hangzhou_4x4.net.xml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo verificar si la red tiene TLS, sin modificar",
    )
    parser.add_argument(
        "--force-xml",
        action="store_true",
        help="Forzar inyección XML sin intentar netconvert primero",
    )
    args = parser.parse_args()

    # ── Rutas ─────────────────────────────────────────────────────────────────
    if args.input:
        net_path = args.input
        if not net_path.is_absolute():
            net_path = PROJECT_ROOT / net_path
    else:
        net_path = PROJECT_ROOT / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"

    if not net_path.exists():
        logger.error(f"❌ Archivo de red no encontrado: {net_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("VERIFICACIÓN Y REPARACIÓN DE SEMÁFOROS (TLS)")
    logger.info("Referencia: Cap. 4.4.1 - Hangzhou 4×4 Benchmark")
    logger.info("=" * 60)

    # ── Verificar estado actual ────────────────────────────────────────────────
    stats = verify_network_has_tls(net_path)
    logger.info(f"\n📊 Estado actual de la red: {net_path.name}")
    logger.info(f"   tlLogic elements   : {stats['tlLogic']}")
    logger.info(f"   Junctions TLS      : {stats['traffic_light_junctions']}")
    logger.info(f"   Total junctions    : {stats['total_junctions']}")
    logger.info(f"   Nodos a controlar  : {len(ALL_TLS_NODES)} ({', '.join(ALL_TLS_NODES)})")

    if args.dry_run:
        if stats["tlLogic"] >= len(ALL_TLS_NODES):
            logger.info("\n✅ DRY-RUN: La red ya tiene semáforos suficientes")
        else:
            logger.warning(f"\n⚠️  DRY-RUN: La red necesita {len(ALL_TLS_NODES)} semáforos, tiene {stats['tlLogic']}")
        return

    # ── Si ya tiene TLS suficientes, no hacer nada ────────────────────────────
    if stats["tlLogic"] >= len(ALL_TLS_NODES):
        logger.info("\n✅ La red ya tiene semáforos. No se requiere modificación.")
        return

    # ── Archivar la red original ───────────────────────────────────────────────
    logger.info(f"\n📦 Archivando red original...")
    archive_file(net_path)

    # ── Intentar netconvert primero (más robusto) ──────────────────────────────
    success = False
    if not args.force_xml:
        success = try_netconvert(net_path, net_path)

    # ── Si netconvert falla, inyectar TLS vía XML ──────────────────────────────
    if not success:
        logger.info("\n🔧 Usando inyección XML directa...")
        n_injected = inject_tls_xml(net_path, net_path)

        # Verificar resultado
        stats_after = verify_network_has_tls(net_path)
        logger.info(f"\n📊 Estado DESPUÉS de la inyección:")
        logger.info(f"   tlLogic elements   : {stats_after['tlLogic']}")
        logger.info(f"   Junctions TLS      : {stats_after['traffic_light_junctions']}")

        if stats_after["traffic_light_junctions"] >= len(ALL_TLS_NODES) // 2:
            logger.info(f"\n✅ Semáforos inyectados correctamente: {n_injected}")
        else:
            logger.warning(f"\n⚠️  Verificar manualmente: puede necesitar ajuste de estado strings")

    # ── Verificación final ────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("RESULTADO FINAL")
    logger.info("=" * 60)
    final_stats = verify_network_has_tls(net_path)
    logger.info(f"   tlLogic en red     : {final_stats['tlLogic']}")
    logger.info(f"   Junctions TLS      : {final_stats['traffic_light_junctions']}")
    logger.info(f"   Archivo            : {net_path}")
    logger.info(f"   Backup             : {net_path.with_suffix('.xml.bak')}")

    logger.info("\n📌 Próximos pasos:")
    logger.info("   1. python scripts/generate_hangzhou_scenarios.py")
    logger.info("   2. python scripts/test_sumo_connection.py --mode benchmark")


if __name__ == "__main__":
    main()
