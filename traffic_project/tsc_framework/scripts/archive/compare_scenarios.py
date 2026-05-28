"""
compare_scenarios.py — Comparación Directa PPO en Tráfico Normal vs LATAM
========================================================================
Este script lanza dos evaluaciones secuenciales para el mismo modelo:
1. Escenario Normal (Ideal)
2. Escenario LATAM (Caótico/Imprudente)

Imprime un reporte unificado para la tesis doctoral.
"""

import sys
import yaml
import os
import argparse
from pathlib import Path

# Resolver la raíz del proyecto para importar módulos correctamente
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import warnings
warnings.filterwarnings("ignore")

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from stable_baselines3.common.utils import set_random_seed

from src.core.tsc_env import TSCEnv
from scripts.evaluate import evaluate_agent, print_report, save_csv


def create_env_from_config(config_path: Path, rank: int, seed: int, use_gui: bool = False):
    """Lee un YAML de configuración y retorna una función creadora del entorno TSCEnv."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    net_cfg = cfg.get("network", {}).get("benchmark", {})
    sumo_cfg = cfg.get("sumo", {})
    
    NETWORK = ROOT / net_cfg.get("network_file", "sumo_configs/networks/hangzhou_4x4.net.xml")
    ROUTE_DIR = ROOT / net_cfg.get("route_files_dir", "sumo_configs/routes/hangzhou")
    TLS_ID = net_cfg.get("tls_id", "B1")
    DELTA_T = int(sumo_cfg.get("step_length", 5))
    end_time_sec = int(sumo_cfg.get("end_time", 3600))
    TIME_TO_TELEPORT = int(sumo_cfg.get("time_to_teleport", -1))
    MAX_STEPS = end_time_sec // DELTA_T
    
    latam_feat = cfg.get("latam_features", {})
    lateral_res = latam_feat.get("lateral_resolution", None)

    # Soporte explícito para route_file o fallback a glob
    if "route_file" in net_cfg:
        ROUTE_FILE = str(ROOT / net_cfg["route_file"])
    else:
        # Usamos el escenario de tráfico equivalente (mismo volumen) pero con conductores normales
        ROUTE_FILE = str(ROOT / "experiments/hangzhou_robustness/scenarios/hangzhou_normal_drivers.rou.xml")
        # Forzamos la red con peatones para que la topología sea idéntica a LATAM
        NETWORK = ROOT / "sumo_configs/hangzhou/hangzhou_pedestrian.net.xml"

    def _make_sumocfg() -> str:
        add_path = ROOT / "experiments/hangzhou_robustness/scenarios/latam_infrastructure.add.xml"
        add_files = f'\n        <additional-files value="{add_path}"/>' if add_path.exists() else ''
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NETWORK}"/>
        <route-files value="{ROUTE_FILE}"/>{add_files}
    </input>
    <time><begin value="0"/><end value="{end_time_sec}"/></time>
    <processing>
        <time-to-teleport value="{TIME_TO_TELEPORT}"/>
        {f'<lateral-resolution value="{lateral_res}"/>' if lateral_res else ''}
    </processing>
    <report><no-warnings value="true"/></report>
</configuration>'''
        tmp = os.path.join(ROOT, f"compare_sumo_rank{rank}.sumocfg")
        with open(tmp, "w", encoding="utf-8") as f: f.write(content)
        return tmp

    def _thunk():
        set_random_seed(seed + rank)
        enable_chaos = latam_feat.get("enable_traci_chaos", False)
        # Solo activamos caos en el escenario LATAM (rank == 102), el Normal (rank == 101) no debería tener caos TraCI
        final_enable_chaos = enable_chaos if rank == 102 else False
        return TSCEnv(
            sumocfg_path=_make_sumocfg(),
            tls_id=TLS_ID,
            delta_t=DELTA_T,
            max_steps=MAX_STEPS,
            use_gui=use_gui,
            seed=seed + rank,
            enable_traci_chaos=final_enable_chaos,
        )
    
    return _thunk, MAX_STEPS


def main():
    parser = argparse.ArgumentParser(description="Comparativa Normal vs LATAM")
    parser.add_argument("--model", required=True, help="Ruta al modelo PPO entrenado")
    parser.add_argument("--n-episodes", type=int, default=1, help="Episodios por escenario")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gui", action="store_true", help="Activar SUMO-GUI")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"❌ Modelo no encontrado: {model_path}")
        sys.exit(1)

    print(f"\n  📦 Cargando modelo: {model_path.name}")
    model = PPO.load(str(model_path), device="cpu")
    
    results = []

    # -------------------------------------------------------------------------
    # 1. EVALUAR EN ESCENARIO NORMAL
    # -------------------------------------------------------------------------
    cfg_normal = ROOT / "config/default_config.yaml"
    env_fn_norm, max_steps_norm = create_env_from_config(cfg_normal, rank=101, seed=args.seed, use_gui=args.gui)
    
    env_normal = VecMonitor(DummyVecEnv([env_fn_norm]))
    metrics_normal = evaluate_agent(
        model, env_normal, args.n_episodes, 
        label="PPO (Normal)", max_steps_limit=max_steps_norm
    )
    results.append(metrics_normal)
    env_normal.close()

    # -------------------------------------------------------------------------
    # 2. EVALUAR EN ESCENARIO LATAM (CAÓTICO)
    # -------------------------------------------------------------------------
    cfg_latam = ROOT / "config/latam_config.yaml"
    env_fn_latam, max_steps_latam = create_env_from_config(cfg_latam, rank=102, seed=args.seed, use_gui=args.gui)
    
    env_latam = VecMonitor(DummyVecEnv([env_fn_latam]))
    metrics_latam = evaluate_agent(
        model, env_latam, args.n_episodes, 
        label="PPO (LATAM)", max_steps_limit=max_steps_latam
    )
    results.append(metrics_latam)
    env_latam.close()

    # -------------------------------------------------------------------------
    # REPORTE FINAL COMBINADO
    # -------------------------------------------------------------------------
    print_report(results)
    
    # Guardar resultados comparativos
    save_csv(results, ROOT / "outputs" / "results" / "comparative_results.csv")

if __name__ == "__main__":
    main()
