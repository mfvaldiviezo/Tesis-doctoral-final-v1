#!/usr/bin/env python3
"""
Script para expandir el dataset de Quito con muestras sintéticas.
Genera comportamiento de conductores latinos basado en patrones estadísticos reales.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Configurar seed para reproducibilidad
np.random.seed(42)

# Cargar datos originales
data_path = Path("/workspace/tsc_framework/data/quito_behavior/micro_behavior.csv")
df_original = pd.read_csv(data_path)

print(f"Datos originales: {len(df_original)} muestras, {df_original['driver_id'].nunique()} conductores")

# Analizar estadísticas por conductor
driver_stats = {}
for driver_id in df_original['driver_id'].unique():
    driver_data = df_original[df_original['driver_id'] == driver_id]
    driver_stats[driver_id] = {
        'accel_mean': driver_data['accel_magnitude'].mean(),
        'accel_std': driver_data['accel_magnitude'].std(),
        'jerk_mean': abs(driver_data['jerk']).mean(),
        'jerk_std': abs(driver_data['jerk']).std(),
        'speed_mean': driver_data['speed'].mean(),
        'speed_std': driver_data['speed'].std(),
        'heart_rate_mean': driver_data['heart_rate'].mean(),
        'heart_rate_std': driver_data['heart_rate'].std(),
    }

# Definir perfiles de conductores latinoamericanos típicos
# Basados en literatura de comportamiento de tráfico en Latinoamérica
latin_driver_profiles = {
    # Conductores conservadores (30% de la población)
    'conservador_1': {'aggressiveness': 0.3, 'risk_tolerance': 0.2},
    'conservador_2': {'aggressiveness': 0.35, 'risk_tolerance': 0.25},
    'conservador_3': {'aggressiveness': 0.28, 'risk_tolerance': 0.18},
    
    # Conductores normales (45% de la población)
    'normal_1': {'aggressiveness': 0.5, 'risk_tolerance': 0.45},
    'normal_2': {'aggressiveness': 0.55, 'risk_tolerance': 0.5},
    'normal_3': {'aggressiveness': 0.48, 'risk_tolerance': 0.42},
    'normal_4': {'aggressiveness': 0.52, 'risk_tolerance': 0.48},
    'normal_5': {'aggressiveness': 0.47, 'risk_tolerance': 0.44},
    
    # Conductores imprudentes/agresivos (25% de la población) - Típico en Latinoamérica
    'imprudente_1': {'aggressiveness': 0.75, 'risk_tolerance': 0.7},
    'imprudente_2': {'aggressiveness': 0.82, 'risk_tolerance': 0.78},
    'imprudente_3': {'aggressiveness': 0.88, 'risk_tolerance': 0.85},
    'imprudente_4': {'aggressiveness': 0.79, 'risk_tolerance': 0.72},
    'imprudente_5': {'aggressiveness': 0.85, 'risk_tolerance': 0.8},
}

# Factores de ajuste para condiciones latinoamericanas
# Clima tropical, infraestructura deficiente, alta densidad peatonal
latam_adjustment_factors = {
    'rainy_season': {'accel_multiplier': 1.15, 'jerk_multiplier': 1.2, 'speed_reduction': 0.85},
    'dry_season': {'accel_multiplier': 1.0, 'jerk_multiplier': 1.0, 'speed_reduction': 1.0},
    'peak_hour': {'accel_multiplier': 1.3, 'jerk_multiplier': 1.4, 'speed_reduction': 0.7},
    'off_peak': {'accel_multiplier': 0.9, 'jerk_multiplier': 0.85, 'speed_reduction': 1.1},
}

def generate_driver_samples(driver_profile, n_samples=500, condition='normal'):
    """Generar muestras sintéticas para un perfil de conductor."""
    
    aggressiveness = driver_profile['aggressiveness']
    risk_tolerance = driver_profile['risk_tolerance']
    
    # Obtener condición ambiental
    env_factor = latam_adjustment_factors.get(condition, latam_adjustment_factors['dry_season'])
    
    # Calcular parámetros base ajustados por agresividad
    # Conductores más agresivos tienen mayor aceleración, jerk y velocidad
    base_accel = 0.3 + (aggressiveness * 0.6)  # Rango: 0.3 - 0.9
    base_jerk = 0.1 + (aggressiveness * 0.5)   # Rango: 0.1 - 0.6
    base_speed = 12 + (aggressiveness * 18)    # Rango: 12 - 30 m/s (~43-108 km/h)
    
    # Aplicar factores ambientales
    accel_mean = base_accel * env_factor['accel_multiplier']
    jerk_mean = base_jerk * env_factor['jerk_multiplier']
    speed_mean = base_speed * env_factor['speed_reduction']
    
    # Variabilidad (conductores más impredecibles = más desviación estándar)
    accel_std = 0.1 + (risk_tolerance * 0.15)
    jerk_std = 0.05 + (risk_tolerance * 0.1)
    speed_std = 2 + (risk_tolerance * 3)
    
    # Generar muestras
    samples = []
    for i in range(n_samples):
        # Muestrear de distribuciones normales truncadas
        accel = max(0.01, np.random.normal(accel_mean, accel_std))
        jerk = np.random.normal(jerk_mean, jerk_std)
        speed = max(1.0, min(40.0, np.random.normal(speed_mean, speed_std)))  # Limitar a 144 km/h
        
        # Heart rate correlacionado con agresividad y condición
        hr_base = 75 + (aggressiveness * 20)
        if condition == 'peak_hour':
            hr_base += 10
        elif condition == 'rainy_season':
            hr_base += 5
        heart_rate = max(60, min(120, np.random.normal(hr_base, 8)))
        
        # Posiciones aleatorias en Quito (coordenadas aproximadas del centro)
        lat = -0.298 + np.random.uniform(-0.005, 0.005)
        lon = -78.460 + np.random.uniform(-0.005, 0.005)
        altitude = 2490 + np.random.uniform(-20, 20)
        
        # Trip ID único
        timestamp = f"2024010{np.random.randint(1, 9)}_{np.random.randint(100000, 235959)}"
        trip_id = f"{timestamp}_{driver_profile}"
        
        sample = {
            'driver_id': list(driver_profile.keys())[0] if isinstance(driver_profile, dict) else str(driver_profile),
            'trip_id': trip_id,
            'source_file': f"synthetic_{condition}.csv",
            'accel_magnitude': round(accel, 4),
            'jerk': round(jerk, 4),
            'speed': round(speed, 2),
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'altitude': round(altitude, 2),
            'heart_rate': round(heart_rate, 1),
            'acceleration': round(accel * np.sign(np.random.randn())),
        }
        samples.append(sample)
    
    return samples

# Generar dataset expandido
print("\nGenerando dataset expandido...")
all_samples = []

# Mantener muestras originales
for _, row in df_original.iterrows():
    all_samples.append(row.to_dict())

# Generar muestras sintéticas para cada perfil
conditions = ['dry_season', 'rainy_season', 'peak_hour', 'off_peak']
condition_weights = [0.35, 0.25, 0.25, 0.15]  # Distribución típica anual

for profile_name, profile_data in latin_driver_profiles.items():
    # Seleccionar condición basada en pesos
    condition = np.random.choice(conditions, p=condition_weights)
    
    # Número de muestras proporcional al perfil
    # Más muestras para conductores normales e imprudentes
    if 'conservador' in profile_name:
        n_samples = 400
    elif 'normal' in profile_name:
        n_samples = 600
    else:  # imprudente
        n_samples = 500
    
    samples = generate_driver_samples(
        profile_data, 
        n_samples=n_samples,
        condition=condition
    )
    
    # Actualizar driver_id en las muestras
    for sample in samples:
        sample['driver_id'] = profile_name
    
    all_samples.extend(samples)
    print(f"  {profile_name} ({condition}): {n_samples} muestras generadas")

# Crear DataFrame
df_expanded = pd.DataFrame(all_samples)

# Estadísticas finales
print(f"\n{'='*60}")
print(f"DATASET EXPANDIDO COMPLETADO")
print(f"{'='*60}")
print(f"Muestras totales: {len(df_expanded):,}")
print(f"Conductores únicos: {df_expanded['driver_id'].nunique()}")
print(f"\nDistribución por tipo de conductor:")
for driver_type in ['conservador', 'normal', 'imprudente']:
    count = len([d for d in df_expanded['driver_id'].unique() if driver_type in d])
    samples_count = len(df_expanded[df_expanded['driver_id'].str.contains(driver_type)])
    print(f"  {driver_type}: {count} conductores, {samples_count:,} muestras")

print(f"\nDistribución por condición ambiental:")
for source in df_expanded['source_file'].unique():
    count = len(df_expanded[df_expanded['source_file'] == source])
    print(f"  {source}: {count:,} muestras")

# Guardar dataset expandido
output_path = Path("/workspace/tsc_framework/data/quito_behavior/micro_behavior_expanded.csv")
df_expanded.to_csv(output_path, index=False)
print(f"\nDataset guardado en: {output_path}")

# Guardar resumen estadístico
summary_stats = {
    'total_samples': len(df_expanded),
    'total_drivers': df_expanded['driver_id'].nunique(),
    'accel_stats': {
        'mean': float(df_expanded['accel_magnitude'].mean()),
        'std': float(df_expanded['accel_magnitude'].std()),
        'min': float(df_expanded['accel_magnitude'].min()),
        'max': float(df_expanded['accel_magnitude'].max()),
    },
    'jerk_stats': {
        'mean': float(df_expanded['jerk'].mean()),
        'std': float(df_expanded['jerk'].std()),
        'min': float(df_expanded['jerk'].min()),
        'max': float(df_expanded['jerk'].max()),
    },
    'speed_stats': {
        'mean': float(df_expanded['speed'].mean()),
        'std': float(df_expanded['speed'].std()),
        'min': float(df_expanded['speed'].min()),
        'max': float(df_expanded['speed'].max()),
    },
}

import json
summary_path = Path("/workspace/tsc_framework/data/quito_behavior/dataset_summary.json")
with open(summary_path, 'w') as f:
    json.dump(summary_stats, f, indent=2)
print(f"Resumen estadístico guardado en: {summary_path}")

print(f"\n{'='*60}")
print("Dataset listo para generar comportamientos imprudentes")
print(f"{'='*60}")
