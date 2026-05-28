import sys, os, tempfile
sys.path.insert(0, '.')
from src.core.tsc_env import TSCEnv
import numpy as np

print("🔍 INSPECCIÓN PROFUNDA DEL DICCIONARIO INFO")
print("="*60)

# Rutas absolutas
NET = os.path.abspath("sumo_configs/networks/hangzhou_4x4.net.xml")
ROUTE = os.path.abspath("sumo_configs/routes/hangzhou/hangzhou_minimal.rou.xml")
TLS = "B1"

# Crear sumocfg temporal
cfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NET}"/>
        <route-files value="{ROUTE}"/>
    </input>
    <time><begin value="0"/><end value="3600"/></time>
    <processing><time-to-teleport value="-1"/></processing>
    <report><no-warnings value="true"/></report>
</configuration>'''

tmp_path = os.path.join(tempfile.gettempdir(), "inspect_info.sumocfg")
with open(tmp_path, "w", encoding="utf-8") as f:
    f.write(cfg_content)

print(f"🏗️ Inicializando entorno (TLS={TLS})...")
env = TSCEnv(sumocfg_path=tmp_path, tls_id=TLS, delta_t=5, max_steps=720, use_gui=False, seed=42)

print("🔄 Reset...")
obs, info_reset = env.reset()
print(f"   Info en reset: {type(info_reset)} -> {info_reset if isinstance(info_reset, dict) else 'N/A'}")

print("\n🔄 Ejecutando 3 pasos e inspeccionando 'info'...")
for step in range(3):
    action = 0 # Mantener estado
    obs, reward, term, trunc, info = env.step(action)
    
    print(f"\n--- Paso {step+1} ---")
    print(f"Reward: {reward}")
    print(f"Tipo de Info: {type(info)}")
    
    if isinstance(info, dict):
        print(f"Claves disponibles ({len(info)}): {list(info.keys())}")
        # Buscar cualquier clave que parezca una métrica
        metrics_keys = [k for k in info.keys() if any(x in k.lower() for x in ['delay', 'wait', 'queue', 'gini', 'reward', 'metric'])]
        if metrics_keys:
            print(f"   🎯 Claves de métricas encontradas: {metrics_keys}")
            for k in metrics_keys:
                print(f"      {k}: {info[k]}")
        else:
            print("   ⚠️ No se encontraron claves obvias de métricas.")
            # Imprimir primeras 5 claves para depurar
            sample_keys = list(info.keys())[:5]
            if sample_keys:
                print(f"   Muestra de otras claves: {sample_keys}")
                for k in sample_keys:
                    print(f"      {k}: {info[k]}")
    elif isinstance(info, (list, tuple)) and len(info) > 0:
        print(f"Info es lista/tupla. Primer elemento: {type(info[0])}")
        if isinstance(info[0], dict):
            print(f"   Claves del primer elemento: {list(info[0].keys())[:10]}")
    else:
        print("⚠️ Info está vacío o es None.")

env.close()
print("\n✅ Inspección finalizada.")
