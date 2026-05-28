#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_benchmark_suite.py
======================
Script maestro para el benchmark de resiliencia MARL en Hangzhou (4x4).
Ejecuta todos los algoritmos en escenarios ideal y caótico (LATAM),
recopila métricas SUMO unificadas y genera una tabla comparativa
para la tesis doctoral.

Uso:
    python run_benchmark_suite.py [--skip-existing] [--report-only]

Algoritmos evaluados:
    - FIXED       : Tiempo fijo (línea base)
    - MAXPRESSURE : Heurística clásica
    - IPPO        : Independent PPO (deep RL)
    - CoLight     : Graph-Attention Multi-Agent RL (SOTA)

Métricas unificadas (independientes de la reward interna):
    - Avg Queue Length    : Longitud media de colas por semáforo
    - Throughput/step     : Vehículos que salen por paso de simulación
    - Cumul. Wait Proxy   : Suma acumulada de tiempo de espera (abs reward)
    - Episode Reward      : Reward interna del algoritmo (no comparable directa)
    - Degradation %       : Cambio porcentual ideal → caótico en throughput
"""

import os
import sys
import json
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime

# ─── Configuración ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
RESCO_DIR    = PROJECT_ROOT / "baselines" / "RESCO"
RESULTS_DIR  = RESCO_DIR / "results"
REPORT_DIR   = PROJECT_ROOT / "benchmark_reports"
REPORT_DIR.mkdir(exist_ok=True)

# Algoritmos a evaluar: (nombre_cli, nombre_display, tiene_entrenamiento)
ALGORITHMS = [
    ("FIXED",        "Fixed Time",       False),
    ("MAXPRESSURE",  "Max Pressure",     False),
    ("IPPO",         "IPPO",             True),
    ("CoLight",      "CoSLight (SOTA)",  True),
]

SCENARIOS = [
    ("ideal", "Tráfico Ideal"),
    ("latam", "Tráfico LATAM (Caótico)"),
]

# ─── Helpers ───────────────────────────────────────────────────────────────────
def print_header(text, width=70):
    print("\n" + "═" * width)
    print(f"  {text}")
    print("═" * width)

def print_section(text):
    print(f"\n  ▶ {text}")

def run_experiment(algo: str, scenario: str, timeout: int = 900) -> dict:
    """Lanza run_resco.py y captura el resultado."""
    print_section(f"Ejecutando {algo} | {scenario} ...")
    t0 = time.time()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + str(RESCO_DIR)
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "run_resco.py"),
         "--algo", algo, "--scenario", scenario],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(PROJECT_ROOT),
        encoding="utf-8",
        errors="replace",
    )

    episode_reward = None
    output_lines = []
    try:
        for line in proc.stdout:
            output_lines.append(line.rstrip())
            if "Episode Reward:" in line:
                try:
                    episode_reward = float(line.split("Episode Reward:")[-1].strip().rstrip(",").rstrip(")"))
                except ValueError:
                    pass
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"    ⚠️  TIMEOUT ({timeout}s)")

    elapsed = time.time() - t0
    success = proc.returncode == 0

    # Muestra las últimas líneas de salida para diagnóstico
    if not success:
        print(f"    ❌ Error (código {proc.returncode})")
        for ln in output_lines[-5:]:
            print(f"       {ln}")
    else:
        print(f"    ✅ Completado en {elapsed:.1f}s  |  Episode Reward = {episode_reward}")

    return {
        "algo": algo,
        "scenario": scenario,
        "success": success,
        "elapsed_s": round(elapsed, 1),
        "episode_reward": episode_reward,
        "returncode": proc.returncode,
    }


def find_latest_unified_metrics(algo: str, scenario: str) -> dict | None:
    """Busca el archivo unified_metrics más reciente para este experimento."""
    # Mapear alias CLI -> nombre interno RESCO
    algo_map = {"CoLight": "coslight", "IPPO": "ippo", "FIXED": "fixed", "MAXPRESSURE": "maxpressure"}
    algo_key = algo_map.get(algo, algo.lower())
    scenario_key = "latam" if scenario == "latam" else ""

    best_mtime = 0
    best_data  = None

    for run_dir in RESULTS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        name = run_dir.name.lower()
        if algo_key not in name:
            continue
        # Filtrar por escenario
        has_latam = "latam" in name
        if scenario == "latam" and not has_latam:
            continue
        if scenario == "ideal" and has_latam:
            continue

        # Buscar unified_metrics recursivamente
        for metrics_file in run_dir.rglob("unified_metrics_ep*.json"):
            mtime = metrics_file.stat().st_mtime
            if mtime > best_mtime:
                try:
                    data = json.loads(metrics_file.read_text(encoding="utf-8"))
                    best_data = data
                    best_mtime = mtime
                except Exception:
                    pass

    return best_data


def build_comparison_table(results: list[dict]) -> str:
    """Construye la tabla comparativa como texto."""
    lines = []
    sep   = "─" * 100

    lines.append("\n" + "═" * 100)
    lines.append(f"{'TABLA COMPARATIVA DE RESILIENCIA MARL — RED HANGZHOU 4×4':^100}")
    lines.append(f"{'Generado: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}")
    lines.append("═" * 100)

    # Cabecera
    lines.append(
        f"{'Algoritmo':<18} {'Escenario':<20} {'Ep. Reward':>14} "
        f"{'Avg Queue':>12} {'Throughput/step':>16} {'Wait Proxy':>14} "
        f"{'Tiempo (s)':>11} {'OK':>4}"
    )
    lines.append(sep)

    # Datos agrupados por algoritmo
    algo_order = [a[0] for a in ALGORITHMS]
    grouped: dict[str, dict] = {a: {} for a in algo_order}

    for r in results:
        if r["algo"] not in grouped:
            grouped[r["algo"]] = {}
        grouped[r["algo"]][r["scenario"]] = r

    for algo in algo_order:
        if algo not in grouped:
            continue
        for scenario in ["ideal", "latam"]:
            r = grouped[algo].get(scenario)
            if r is None:
                lines.append(f"  {algo:<16} {'  ' + scenario:<20}  {'—':>14} {'—':>12} {'—':>16} {'—':>14} {'—':>11} {'—':>4}")
                continue

            m = find_latest_unified_metrics(algo, scenario)
            ep_rew    = f"{r['episode_reward']:.2f}"   if r['episode_reward'] is not None else "N/D"
            avg_q     = f"{m['avg_queue_length']:.3f}" if m else "N/D"
            tput      = f"{m['throughput_per_step']:.4f}" if m else "N/D"
            wait_prx  = f"{m['cumulative_wait_proxy']:.1f}" if m else "N/D"
            elapsed   = f"{r['elapsed_s']}"
            ok        = "✓" if r["success"] else "✗"

            scen_label = "Ideal" if scenario == "ideal" else "LATAM (Caótico)"
            lines.append(
                f"  {algo:<16} {scen_label:<20} {ep_rew:>14} {avg_q:>12} {tput:>16} {wait_prx:>14} {elapsed:>11} {ok:>4}"
            )
        lines.append(sep)

    # Sección de análisis de degradación
    lines.append("")
    lines.append("  📊 ANÁLISIS DE DEGRADACIÓN  (ideal → caótico)")
    lines.append("─" * 60)
    lines.append(f"  {'Algoritmo':<18} {'Δ Throughput':>15} {'Δ Avg Queue':>15} {'Resiliencia':>14}")
    lines.append("─" * 60)

    for algo in algo_order:
        m_ideal = find_latest_unified_metrics(algo, "ideal")
        m_latam = find_latest_unified_metrics(algo, "latam")
        if m_ideal and m_latam:
            tput_i = m_ideal.get("throughput_per_step", 0)
            tput_l = m_latam.get("throughput_per_step", 0)
            q_i    = m_ideal.get("avg_queue_length", 0)
            q_l    = m_latam.get("avg_queue_length", 0)
            delta_tput = ((tput_l - tput_i) / max(tput_i, 1e-9)) * 100
            delta_q    = ((q_l - q_i) / max(q_i, 1e-9)) * 100
            resil = "Alta 🟢" if abs(delta_tput) < 10 else ("Media 🟡" if abs(delta_tput) < 25 else "Baja 🔴")
            lines.append(
                f"  {algo:<18} {delta_tput:>+14.1f}% {delta_q:>+14.1f}% {resil:>14}"
            )
        else:
            lines.append(f"  {algo:<18} {'Sin datos suficientes':>44}")

    lines.append("═" * 100)
    lines.append("")
    lines.append("  ℹ️  NOTAS METODOLÓGICAS:")
    lines.append("  • 'Avg Queue'    : Longitud media de colas por semáforo por paso (vehículos)")
    lines.append("  • 'Throughput'   : Vehículos que abandonaron la simulación por paso de tiempo")
    lines.append("  • 'Wait Proxy'   : Suma absoluta de la reward de espera (escala interna RESCO)")
    lines.append("  • 'Ep. Reward'   : Reward interna del agente — NO comparable entre FIXED/IPPO y CoLight")
    lines.append("  • 'Δ Throughput' : Cambio porcentual del throughput en caos vs ideal")
    lines.append("  • 'Resiliencia'  : Alta=|Δ|<10%, Media=|Δ|<25%, Baja=|Δ|≥25%")
    lines.append("═" * 100)

    return "\n".join(lines)


def save_report(table: str, results: list[dict]):
    """Guarda el reporte en texto plano y JSON."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path  = REPORT_DIR / f"benchmark_{ts}.txt"
    json_path = REPORT_DIR / f"benchmark_{ts}_raw.json"

    txt_path.write_text(table, encoding="utf-8")
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  💾 Reporte guardado en:")
    print(f"     {txt_path}")
    print(f"     {json_path}")


# ─── Programa principal ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Benchmark MARL suite para Hangzhou 4x4")
    parser.add_argument("--skip-existing", action="store_true",
                        help="No vuelve a ejecutar experimentos si ya tienen resultados")
    parser.add_argument("--report-only", action="store_true",
                        help="Solo genera el reporte con los resultados ya existentes")
    parser.add_argument("--algos", nargs="+", default=None,
                        help="Subset de algoritmos a ejecutar (ej: FIXED IPPO)")
    parser.add_argument("--scenarios", nargs="+", default=None,
                        choices=["ideal","latam"],
                        help="Subset de escenarios (ideal latam)")
    args = parser.parse_args()

    algos_to_run    = args.algos    or [a[0] for a in ALGORITHMS]
    scenarios_to_run = args.scenarios or ["ideal","latam"]

    print_header("🚦 BENCHMARK SUITE MARL — HANGZHOU 4x4")
    print(f"  Algoritmos : {algos_to_run}")
    print(f"  Escenarios : {scenarios_to_run}")
    print(f"  Resultados : {RESULTS_DIR}")

    all_results: list[dict] = []

    if not args.report_only:
        total = len(algos_to_run) * len(scenarios_to_run)
        current = 0
        for algo in algos_to_run:
            for scenario in scenarios_to_run:
                current += 1
                print_header(f"[{current}/{total}] {algo} | {scenario.upper()}")

                if args.skip_existing:
                    existing = find_latest_unified_metrics(algo, scenario)
                    if existing:
                        print(f"  ⏩ Ya existe resultado, saltando (--skip-existing).")
                        all_results.append({
                            "algo": algo,
                            "scenario": scenario,
                            "success": True,
                            "elapsed_s": 0,
                            "episode_reward": existing.get("episode_reward"),
                            "returncode": 0,
                            "skipped": True,
                        })
                        continue

                result = run_experiment(algo, scenario)
                all_results.append(result)

                # Pausa mínima entre experimentos para que SUMO libere puertos TCP
                time.sleep(3)

    # ─── Tabla comparativa ────────────────────────────────────────────────────
    print_header("📊 TABLA COMPARATIVA FINAL")
    table = build_comparison_table(all_results)
    print(table)
    save_report(table, all_results)

    # ─── Resumen rápido ───────────────────────────────────────────────────────
    failures = [r for r in all_results if not r.get("success", False)]
    if failures:
        print(f"\n  ⚠️  {len(failures)} experimento(s) fallaron:")
        for f in failures:
            print(f"       {f['algo']} | {f['scenario']} — código {f.get('returncode')}")
    else:
        print(f"\n  ✅ Todos los experimentos completados exitosamente.")


if __name__ == "__main__":
    main()
