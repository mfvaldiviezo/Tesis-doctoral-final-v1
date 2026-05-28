#!/usr/bin/env python3
"""
Script para generar conductores imprudentes basados en datos reales de Quito.
Utiliza distribuciones estadísticas para modelar comportamiento de conducción latinoamericana.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data(data_path: str) -> pd.DataFrame:
    """Cargar datos de comportamiento desde CSV."""
    logger.info(f"Cargando datos desde {data_path}...")
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"No se encontró el archivo: {data_path}")
    
    df = pd.read_csv(data_path)
    logger.info(f"Datos cargados: {len(df)} muestras, {df['driver_id'].nunique()} conductores")
    
    return df


def analyze_drivers(df: pd.DataFrame) -> dict:
    """Analizar comportamiento por conductor y calcular score de imprudencia."""
    logger.info("Analizando comportamiento por conductor...")
    
    driver_stats = {}
    
    for driver_id in df['driver_id'].unique():
        driver_data = df[df['driver_id'] == driver_id]
        
        # Calcular métricas de imprudencia
        avg_accel = driver_data['accel_magnitude'].mean()
        std_accel = driver_data['accel_magnitude'].std()
        max_accel = driver_data['accel_magnitude'].max()
        
        avg_jerk = abs(driver_data['jerk']).mean()
        max_jerk = abs(driver_data['jerk']).max()
        
        avg_speed = driver_data['speed'].mean()
        max_speed = driver_data['speed'].max()
        
        # Score de imprudencia (ponderado)
        # Mayor aceleración, jerk y velocidad = más imprudente
        imprudence_score = (
            0.4 * (avg_accel / df['accel_magnitude'].max()) +
            0.3 * (avg_jerk / df['jerk'].abs().max()) +
            0.2 * (std_accel / df['accel_magnitude'].std()) +
            0.1 * (max_accel / df['accel_magnitude'].max())
        )
        
        driver_stats[driver_id] = {
            'n_samples': len(driver_data),
            'avg_accel': float(avg_accel),
            'std_accel': float(std_accel),
            'max_accel': float(max_accel),
            'avg_jerk': float(avg_jerk),
            'max_jerk': float(max_jerk),
            'avg_speed': float(avg_speed),
            'max_speed': float(max_speed),
            'imprudence_score': float(imprudence_score)
        }
    
    # Ordenar por score de imprudencia
    sorted_drivers = sorted(
        driver_stats.items(), 
        key=lambda x: x[1]['imprudence_score'], 
        reverse=True
    )
    
    logger.info("Ranking de imprudencia (mayor score = más imprudente):")
    for driver_id, stats_data in sorted_drivers:
        logger.info(f"  {driver_id}: {stats_data['imprudence_score']:.4f}")
    
    return dict(sorted_drivers)


def fit_distributions(df: pd.DataFrame) -> dict:
    """Ajustar distribuciones estadísticas a las variables de comportamiento."""
    logger.info("Ajustando distribuciones estadísticas...")
    
    distributions = {}
    
    # Variables a modelar
    variables = ['accel_magnitude', 'jerk', 'speed']
    
    # Distribuciones candidatas
    candidate_dists = [
        stats.norm,
        stats.gamma,
        stats.weibull_min,
        stats.beta,
        stats.lognorm,
        stats.expon
    ]
    
    for var in variables:
        data = df[var].dropna()
        
        if len(data) < 10:
            logger.warning(f"Pocos datos para {var}, usando distribución empírica")
            distributions[var] = {'type': 'empirical', 'data': data.values}
            continue
        
        # Normalizar datos si es necesario
        if var == 'accel_magnitude':
            # Asegurar que sea positivo para gamma/lognorm
            data = data[data > 0.001]
        elif var == 'speed':
            data = data[data > 0.001]
        
        if len(data) < 10:
            distributions[var] = {'type': 'empirical', 'data': df[var].dropna().values}
            continue
        
        # Encontrar la mejor distribución
        best_dist = None
        best_pvalue = 0
        
        for dist in candidate_dists:
            try:
                # Ajustar distribución
                params = dist.fit(data)
                
                # Test de Kolmogorov-Smirnov
                ks_stat, p_value = stats.kstest(data, dist.cdf, args=params)
                
                if p_value > best_pvalue:
                    best_pvalue = p_value
                    best_dist = {
                        'type': dist.name,
                        'params': params,
                        'p_value': float(p_value),
                        'ks_stat': float(ks_stat)
                    }
            except Exception as e:
                continue
        
        if best_dist:
            distributions[var] = best_dist
            logger.info(f"  {var}: {best_dist['type']} (p={best_dist['p_value']:.4f})")
        else:
            # Fallback a empírica
            distributions[var] = {'type': 'empirical', 'data': data.values}
            logger.info(f"  {var}: empirical (fallback)")
    
    return distributions


def generate_scenarios(
    distributions: dict, 
    n_scenarios: int, 
    stress_level: str = 'nominal'
) -> pd.DataFrame:
    """Generar escenarios sintéticos con diferentes niveles de estrés."""
    
    np.random.seed(42)
    
    scenarios = []
    
    # Factores de multiplicación según nivel de estrés
    stress_factors = {
        'nominal': 1.0,
        'moderate': 1.5,
        'extreme': 2.0
    }
    
    factor = stress_factors.get(stress_level, 1.0)
    
    for i in range(n_scenarios):
        scenario = {'scenario_id': i, 'stress_level': stress_level}
        
        for var, dist_info in distributions.items():
            if dist_info['type'] == 'empirical':
                # Muestreo empírico
                value = np.random.choice(dist_info['data'])
            else:
                # Muestreo de distribución ajustada
                dist_func = getattr(stats, dist_info['type'])
                value = dist_func.rvs(*dist_info['params'])
            
            # Aplicar factor de estrés (solo para variables positivas)
            if var in ['accel_magnitude', 'speed'] and factor > 1.0:
                value = min(value * factor, dist_info.get('max', 10.0))
            elif var == 'jerk':
                value = value * factor
            
            # Asegurar valores no negativos para accel y speed
            if var in ['accel_magnitude', 'speed']:
                value = max(0.0, value)
            
            scenario[var] = float(value)
        
        scenarios.append(scenario)
    
    return pd.DataFrame(scenarios)


def export_to_sumo(scenarios_df: pd.DataFrame, output_path: str, driver_stats: dict):
    """Exportar escenarios a formato SUMO (.rou.xml) con flujos masivos de tráfico mixto."""
    logger.info(f"Exportando escenarios a {output_path}...")
    
    sorted_drivers = sorted(
        driver_stats.items(),
        key=lambda x: x[1]['imprudence_score'],
        reverse=True
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n')
        
        f.write('  <!-- Tráfico Normal (Baseline) -->\n')
        f.write('  <vType id="car" length="4.5" minGap="2.5" maxSpeed="13.89" sigma="0.5" tau="1.0" color="1,1,1"/>\n\n')
        
        f.write('  <!-- Conductores Imprudentes (Quito) -->\n')
        vtype_ids = []
        for idx, (driver_id, stats_data) in enumerate(sorted_drivers):
            vtype_id = f"imprudent_{driver_id}"
            vtype_ids.append(vtype_id)
            imprudence = max(0.01, stats_data['imprudence_score'])
            sigma = max(0.1, min(1.0, 0.3 + imprudence * 1.5))
            tau = max(0.5, min(1.5, 1.5 - imprudence))
            max_speed_factor = max(1.0, min(1.5, 1.0 + imprudence * 0.3))
            accel = max(0.5, min(3.0, stats_data['avg_accel'] * 2.0))
            decel = max(0.75, min(4.5, accel * 1.5))
            
            f.write(f'  <vType id="{vtype_id}" sigma="{sigma:.3f}" tau="{tau:.3f}" ')
            f.write(f'speedFactor="{max_speed_factor:.3f}" accel="{accel:.3f}" decel="{decel:.3f}" ')
            f.write(f'color="1,{max(0, min(1, 1-imprudence)):.3f},0" />\n')
            
        f.write('\n  <!-- Distribución de Tráfico Mixto (50% normal, 50% imprudente) -->\n')
        
        all_types = ["car"] + vtype_ids
        prob_per_imprudent = 0.50 / len(vtype_ids)
        all_probs = ["0.50"] + [f"{prob_per_imprudent:.3f}" for _ in vtype_ids]
        
        f.write(f'  <vTypeDistribution id="mixed_traffic" vTypes="{" ".join(all_types)}" probabilities="{" ".join(all_probs)}"/>\n\n')

        f.write('  <!-- Rutas de la Red Hangzhou 4x4 -->\n')
        routes = [
            ("r_WE_0", "A0B0 B0C0 C0D0"), ("r_WE_1", "A1B1 B1C1 C1D1"), ("r_WE_2", "A2B2 B2C2 C2D2"), ("r_WE_3", "A3B3 B3C3 C3D3"),
            ("r_EW_0", "D0C0 C0B0 B0A0"), ("r_EW_1", "D1C1 C1B1 B1A1"), ("r_EW_2", "D2C2 C2B2 B2A2"), ("r_EW_3", "D3C3 C3B3 B3A3"),
            ("r_SN_A", "A0A1 A1A2 A2A3"), ("r_SN_B", "B0B1 B1B2 B2B3"), ("r_SN_C", "C0C1 C1C2 C2C3"), ("r_SN_D", "D0D1 D1D2 D2D3"),
            ("r_NS_A", "A3A2 A2A1 A1A0"), ("r_NS_B", "B3B2 B2B1 B1B0"), ("r_NS_C", "C3C2 C2C1 C1C0"), ("r_NS_D", "D3D2 D2D1 D1D0")
        ]
        for r_id, r_edges in routes:
            f.write(f'  <route id="{r_id}" edges="{r_edges}"/>\n')

        f.write('\n  <!-- Flujos Masivos de Tráfico (Period=10s para generar estrés pesado) -->\n')
        for i, (r_id, _) in enumerate(routes):
            # Generar tráfico mezclado continuo por 3600s
            f.write(f'  <flow id="f_mixed_{i:03d}" route="{r_id}" type="mixed_traffic" begin="0" end="3600" period="10"/>\n')

        f.write('</routes>\n')
    
    logger.info(f"Archivo exportado: {output_path} (Flujos masivos con vTypeDistribution)")


def main():
    parser = argparse.ArgumentParser(
        description='Generar conductores imprudentes basados en datos de Quito'
    )
    parser.add_argument(
        '--data-path', 
        type=str, 
        required=True,
        help='Ruta al archivo CSV con datos de comportamiento'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='results/quito_scenarios',
        help='Directorio de salida para los resultados'
    )
    parser.add_argument(
        '--n-scenarios', 
        type=int, 
        default=1000,
        help='Número de escenarios a generar por nivel de estrés'
    )
    parser.add_argument(
        '--seed', 
        type=int, 
        default=42,
        help='Semilla aleatoria'
    )
    
    args = parser.parse_args()
    
    # Crear directorio de salida
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configurar seed
    np.random.seed(args.seed)
    
    # Paso 1: Cargar datos
    df = load_data(args.data_path)
    
    # Paso 2: Analizar conductores
    driver_stats = analyze_drivers(df)
    
    # Guardar análisis
    analysis_path = output_dir / 'driver_analysis.json'
    with open(analysis_path, 'w') as f:
        json.dump(driver_stats, f, indent=2)
    logger.info(f"Análisis guardado en {analysis_path}")
    
    # Paso 3: Ajustar distribuciones
    distributions = fit_distributions(df)
    
    # Paso 4: Generar escenarios para cada nivel de estrés
    logger.info(f"Generando {args.n_scenarios} escenarios por nivel de estrés...")
    
    all_scenarios = []
    for stress_level in ['nominal', 'moderate', 'extreme']:
        scenarios = generate_scenarios(distributions, args.n_scenarios, stress_level)
        all_scenarios.append(scenarios)
    
    scenarios_df = pd.concat(all_scenarios, ignore_index=True)
    logger.info(f"Generados {len(scenarios_df)} escenarios totales")
    
    # Guardar resumen
    summary_path = output_dir / 'scenario_summary.csv'
    scenarios_df.to_csv(summary_path, index=False)
    logger.info(f"Resumen guardado en {summary_path}")
    
    # Paso 5: Exportar a SUMO
    sumo_output = output_dir / 'imprudent_drivers.rou.xml'
    export_to_sumo(scenarios_df, str(sumo_output), driver_stats)
    
    # Guardar configuración
    config = {
        'data_path': args.data_path,
        'n_scenarios': args.n_scenarios,
        'seed': args.seed,
        'output_dir': str(output_dir),
        'timestamp': datetime.now().isoformat(),
        'distributions': {k: {kk: vv for kk, vv in v.items() if kk != 'data'} 
                         for k, v in distributions.items()}
    }
    
    config_path = output_dir / 'generation_config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Configuración guardada en {config_path}")
    
    logger.info("=" * 60)
    logger.info("GENERACIÓN COMPLETADA EXITOSAMENTE")
    logger.info("=" * 60)
    logger.info(f"Escenarios generados: {len(scenarios_df)}")
    logger.info(f"Total vehículos: {len(scenarios_df) * 10}")  # Aproximado
    logger.info(f"Archivos guardados en: {output_dir}")


if __name__ == '__main__':
    main()
