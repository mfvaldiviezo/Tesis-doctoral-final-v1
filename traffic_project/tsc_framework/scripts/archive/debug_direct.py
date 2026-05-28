import sys, os, tempfile
sys.path.insert(0, '.')
import numpy as np

print("🔍 DIAGNÓSTICO DIRECTO DE MÉTRICAS")
print("="*50)

from src.core.tsc_env import TSCEnv

# Configuración manual hardcodeada para evitar leer YAML corrupto
NET_FILE = "sumo_configs/networks/hangzhou_4x4.net.xml"
ROUTE_FILE = "sumo_configs/routes/hangzhou/hangzhou_minimal.rou.xml"
TLS_ID = "B1"
DELTA_T = 5
MAX_STEPS = 720 # 3600s / 5s

# Crear sumocfg temporal limpio
sumocfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NET_FILE}"/>
        <route-files value="{ROUTE_FILE}"/>
    </input>
    <time><begin value="0"/><end value="3600"/></time>
    <processing><time-to-teleport value="-1"/></processing>
    <report><no-warnings value="true"/></report>
</configuration>'''

tmp_cfg = os.path.join(tempfile.gettempdir(), "debug_diag.sumocfg")
with open(tmp_cfg, "w", encoding="utf-8") as f:
    f.write(sumocfg_content)

print(f"🏗️ Inicializando entorno con {TLS_ID}...")
env = TSCEnv(
    sumocfg_path=tmp_cfg,
    tls_id=TLS_ID,
    delta_t=DELTA_T,
    max_steps=MAX_STEPS,
    use_gui=False,
    seed=42
)

print("🔄 Ejecutando 5 pasos de prueba...")
obs, info = env.reset()
print(f"✅ Reset OK. Obs shape: {obs.shape}")

for step in range(5):
    action = 0 # Acción fija (mantener estado) para probar
    obs, reward, terminated, truncated, info = env.step(action)
    
    print(f"\n--- Paso {step+1} ---")
    print(f"Reward crudo: {reward}")
    print(f"Tipo de Info: {type(info)}")
    
    # Inspeccionar info
    if isinstance(info, dict):
        keys = list(info.keys())
        print(f"Claves en Info: {keys}")
        
        # Buscar métricas específicas
        for k in ['delay_mean', 'wait_mean', 'total_queue', 'gini']:
            if k in info:
                print(f"  ✅ {k}: {info[k]}")
            else:
                print(f"  ❌ {k}: NO ENCONTRADA")
    elif isinstance(info, (list, tuple)) and len(info) > 0:
        print(f"Info es lista/tupla. Primer elemento: {type(info[0])}")
        if isinstance(info[0], dict):
            print(f"  Claves: {list(info[0].keys())}")
    else:
        print("⚠️ Info está vacío o es de tipo desconocido.")

env.close()
print("\n🛑 Diagnóstico finalizado.")
