"""
generate_hangzhou_scenarios.py — Domain Randomization para Benchmark Hangzhou 4×4
==================================================================================
Framework de Tesis Doctoral: Control Semafórico Inteligente con RL Sensible al Riesgo
Referencia: Capítulo 4.5.1 - Domain Randomization para Robustez

VERSIÓN 2: Actualizada para usar los edge IDs correctos de la red generada por
netgenerate (grid alfanumérico A0–D3), en lugar de los IDs Hangzhou-estilo originales.

Topología de la red:
  A3 -- B3 -- C3 -- D3
  |     |     |     |
  A2 -- B2 -- C2 -- D2
  |     |     |     |
  A1 -- B1 -- C1 -- D1
  |     |     |     |
  A0 -- B0 -- C0 -- D0

Edge IDs correctos (from→to):
  Horizontal EW: A0B0, B0C0, C0D0 (y sus inversos D0C0, C0B0, B0A0)
  Vertical SN:   A0A1, A1A2, A2A3 (y sus inversos A3A2, A2A1, A1A0)
  (igualmente para columnas B, C, D)

Uso:
    python scripts/generate_hangzhou_scenarios.py
    python scripts/generate_hangzhou_scenarios.py --n-scenarios 100 --seed 42
    python scripts/generate_hangzhou_scenarios.py --output-dir sumo_configs/routes/hangzhou
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tsc.generate_hangzhou_scenarios")

# ── Definición de rutas válidas en la red hangzhou 4×4 ─────────────────────
# Estas rutas son compatibles con los edge IDs reales de la red generada.
# Referencia: Capítulo 4.4.1 - Estructura del grid 4×4
ROUTES = {
    # Rutas Oeste→Este (por cada fila)
    "r_WE_0": "A0B0 B0C0 C0D0",
    "r_WE_1": "A1B1 B1C1 C1D1",
    "r_WE_2": "A2B2 B2C2 C2D2",
    "r_WE_3": "A3B3 B3C3 C3D3",
    # Rutas Este→Oeste (por cada fila)
    "r_EW_0": "D0C0 C0B0 B0A0",
    "r_EW_1": "D1C1 C1B1 B1A1",
    "r_EW_2": "D2C2 C2B2 B2A2",
    "r_EW_3": "D3C3 C3B3 B3A3",
    # Rutas Sur→Norte (por cada columna)
    "r_SN_A": "A0A1 A1A2 A2A3",
    "r_SN_B": "B0B1 B1B2 B2B3",
    "r_SN_C": "C0C1 C1C2 C2C3",
    "r_SN_D": "D0D1 D1D2 D2D3",
    # Rutas Norte→Sur (por cada columna)
    "r_NS_A": "A3A2 A2A1 A1A0",
    "r_NS_B": "B3B2 B2B1 B1B0",
    "r_NS_C": "C3C2 C2C1 C1C0",
    "r_NS_D": "D3D2 D2D1 D1D0",
}

# Grupos para variación de demanda (permite sesgos direccionales)
ROUTE_GROUPS = {
    "east_west": ["r_WE_0", "r_WE_1", "r_WE_2", "r_WE_3",
                  "r_EW_0", "r_EW_1", "r_EW_2", "r_EW_3"],
    "north_south": ["r_SN_A", "r_SN_B", "r_SN_C", "r_SN_D",
                    "r_NS_A", "r_NS_B", "r_NS_C", "r_NS_D"],
}

# Vehículos de arranque por escenario (garantizan tráfico desde t=0)
STARTUP_VEHICLES = [
    ("r_WE_1", 0),
    ("r_EW_1", 2),
    ("r_SN_B", 4),
    ("r_NS_C", 6),
]


def build_scenario_xml(
    scenario_idx: int,
    seed: int,
    demand_ew: float,
    demand_ns: float,
    simulation_time: int = 1800,
) -> str:
    """
    Genera el contenido XML de un escenario .rou.xml para domain randomization.

    Parameters
    ----------
    scenario_idx : int
        Índice del escenario (0–99)
    seed : int
        Semilla usada para generar este escenario
    demand_ew : float
        Factor de demanda para rutas Este-Oeste (1.0 = ~400 veh/hora)
    demand_ns : float
        Factor de demanda para rutas Norte-Sur (1.0 = ~400 veh/hora)
    simulation_time : int
        Duración de la simulación en segundos

    Returns
    -------
    str
        Contenido XML del archivo .rou.xml
    """
    lines = []

    # Cabecera XML
    lines.append('<?xml version="1.0" encoding="utf-8"?>')
    lines.append('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    lines.append('        xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">')
    lines.append(f'  <!-- Escenario {scenario_idx:03d} de Hangzhou 4×4 - Seed: {seed} -->')
    lines.append(f'  <!-- Demanda EW: {demand_ew:.2f}x | NS: {demand_ns:.2f}x -->')
    lines.append('')

    # Tipos de vehículo
    lines.append('  <vType id="car" type="passenger" length="5.0" minGap="2.5" maxSpeed="13.89" color="0,0,1"/>')
    lines.append('  <vType id="truck" type="truck" length="10.0" minGap="5.0" maxSpeed="11.11" color="0,0.5,0"/>')
    lines.append('')

    # Definición de rutas
    for route_id, edges in ROUTES.items():
        lines.append(f'  <route id="{route_id}" edges="{edges}"/>')
    lines.append('')

    # Generar flujos con variación de demanda
    # Base: ~400 veh/hora ≈ period=9s
    base_period_ew = 9.0 / demand_ew  # Ajustar período según demanda
    base_period_ns = 9.0 / demand_ns

    flow_idx = 0
    rng = random.Random(seed + scenario_idx * 31)

    for route_id in ROUTE_GROUPS["east_west"]:
        # Variación estocástica del período (±20%)
        variation = rng.uniform(0.8, 1.2)
        period = max(3.0, base_period_ew * variation)
        n_vehicles = int(simulation_time / period)

        lines.append(
            f'  <flow id="f_{flow_idx:03d}" route="{route_id}" vType="car"'
            f' begin="0" end="{simulation_time}" period="{period:.2f}" number="{n_vehicles}"/>'
        )
        flow_idx += 1

    for route_id in ROUTE_GROUPS["north_south"]:
        variation = rng.uniform(0.8, 1.2)
        period = max(3.0, base_period_ns * variation)
        n_vehicles = int(simulation_time / period)

        lines.append(
            f'  <flow id="f_{flow_idx:03d}" route="{route_id}" vType="car"'
            f' begin="0" end="{simulation_time}" period="{period:.2f}" number="{n_vehicles}"/>'
        )
        flow_idx += 1

    # Vehículos de arranque para garantizar tráfico inicial
    lines.append('')
    for v_idx, (route, depart_t) in enumerate(STARTUP_VEHICLES):
        lines.append(
            f'  <vehicle id="v{v_idx:03d}" type="car" route="{route}" depart="{depart_t}"/>'
        )

    lines.append('</routes>')
    return '\n'.join(lines) + '\n'


def generate_all_scenarios(
    output_dir: Path,
    n_scenarios: int = 100,
    base_seed: int = 42,
    simulation_time: int = 1800,
) -> list[Path]:
    """
    Genera N escenarios de domain randomization para la red Hangzhou 4×4.

    La variación entre escenarios cubre:
      - Demanda alta EW / baja NS (escenarios 0–33)
      - Demanda balanceada EW ≈ NS (escenarios 34–66)
      - Demanda baja EW / alta NS (escenarios 67–99)

    Referencia: Capítulo 4.5.1 - Domain Randomization
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    logger.info(f"Generando {n_scenarios} escenarios en {output_dir}")

    for i in range(n_scenarios):
        # Calcular factores de demanda según tercio
        if i < n_scenarios // 3:
            # Demanda alta EW, baja NS
            demand_ew = 0.8 + (i / (n_scenarios // 3)) * 0.9   # 0.8→1.7
            demand_ns = 0.5 + (i / (n_scenarios // 3)) * 0.3   # 0.5→0.8
        elif i < 2 * n_scenarios // 3:
            # Demanda balanceada
            t = (i - n_scenarios // 3) / (n_scenarios // 3)
            demand_ew = 0.7 + t * 0.6   # 0.7→1.3
            demand_ns = 0.7 + t * 0.6   # 0.7→1.3
        else:
            # Demanda alta NS, baja EW
            t = (i - 2 * n_scenarios // 3) / (n_scenarios // 3)
            demand_ew = 0.5 + t * 0.3   # 0.5→0.8
            demand_ns = 0.8 + t * 0.9   # 0.8→1.7

        seed = base_seed + i
        xml_content = build_scenario_xml(
            scenario_idx=i,
            seed=seed,
            demand_ew=demand_ew,
            demand_ns=demand_ns,
            simulation_time=simulation_time,
        )

        route_file = output_dir / f"scenario_{i:03d}_hangzhou.rou.xml"
        with open(route_file, "w", encoding="utf-8") as f:
            f.write(xml_content)

        generated.append(route_file)

        if (i + 1) % 20 == 0:
            logger.info(f"  Progreso: {i + 1}/{n_scenarios} escenarios generados")

    logger.info(f"✅ {n_scenarios} archivos de rutas generados en: {output_dir}")
    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generar escenarios de domain randomization para Hangzhou 4×4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Referencia: Capítulo 4.5.1 - Domain Randomization para Robustez del Agente RL

Los 100 escenarios cubren variaciones de demanda EW/NS para garantizar que el
agente entrenado generalice a distintos patrones de tráfico.

Ejemplos:
  python scripts/generate_hangzhou_scenarios.py
  python scripts/generate_hangzhou_scenarios.py --n-scenarios 100 --seed 42
        """,
    )
    parser.add_argument(
        "--n-scenarios", type=int, default=100,
        help="Número de escenarios a generar (default: 100)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Semilla base para reproducibilidad (default: 42)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Directorio de salida (default: sumo_configs/routes/hangzhou)",
    )
    parser.add_argument(
        "--sim-time", type=int, default=1800,
        help="Duración de simulación en segundos (default: 1800 = 30 min)",
    )
    parser.add_argument(
        "--verify-routes", action="store_true",
        help="Verificar que los edge IDs existen en la red antes de generar",
    )
    args = parser.parse_args()

    # Directorio de salida
    if args.output_dir:
        output_dir = args.output_dir
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / output_dir
    else:
        output_dir = PROJECT_ROOT / "sumo_configs" / "routes" / "hangzhou"

    logger.info("=" * 60)
    logger.info("GENERACIÓN DE ESCENARIOS HANGZHOU 4×4")
    logger.info("Referencia: Cap. 4.5.1 - Domain Randomization")
    logger.info("=" * 60)
    logger.info(f"  Escenarios  : {args.n_scenarios}")
    logger.info(f"  Semilla base: {args.seed}")
    logger.info(f"  Duración sim: {args.sim_time}s")
    logger.info(f"  Directorio  : {output_dir}")
    logger.info(f"  Edge IDs    : Grid alfanumérico (A0A1, B1C1, etc.)")
    logger.info(f"  Rutas       : {len(ROUTES)} rutas únicas definidas")

    # Opcional: verificar edge IDs contra la red
    if args.verify_routes:
        net_path = PROJECT_ROOT / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
        if net_path.exists():
            with open(net_path, "r", encoding="utf-8") as f:
                net_content = f.read()
            missing = []
            for route_id, edges in ROUTES.items():
                for edge_id in edges.split():
                    if f'id="{edge_id}"' not in net_content:
                        missing.append(f"{route_id}: {edge_id}")
            if missing:
                logger.warning(f"⚠️  Edge IDs no encontrados en la red ({len(missing)}):")
                for m in missing[:10]:
                    logger.warning(f"    {m}")
            else:
                logger.info("✅ Todos los edge IDs existen en la red")
        else:
            logger.warning(f"⚠️  Red no encontrada para verificación: {net_path}")

    # Generar escenarios
    files = generate_all_scenarios(
        output_dir=output_dir,
        n_scenarios=args.n_scenarios,
        base_seed=args.seed,
        simulation_time=args.sim_time,
    )

    logger.info(f"\n📊 Resumen:")
    logger.info(f"   {len(files)} archivos generados")
    logger.info(f"   Rango: {files[0].name} → {files[-1].name}")
    logger.info(f"\n📌 Próximos pasos:")
    logger.info(f"   python scripts/test_sumo_connection.py --mode benchmark")
    logger.info(f"   python scripts/train.py --timesteps 100 --n-envs 1")


if __name__ == "__main__":
    main()
