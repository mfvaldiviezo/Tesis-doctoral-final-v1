import sys, os
sys.path.insert(0, '.')
import yaml
from src.core.tsc_env import TSCEnv
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
import tempfile

# Cargar config básica
with open('config/default_config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)

net_cfg = cfg.get('network', {}).get('benchmark', {})
sumo_cfg = cfg.get('sumo', {})
NETWORK = net_cfg.get('network_file', 'sumo_configs/networks/hangzhou_4x4.net.xml')
ROUTE_DIR = net_cfg.get('route_files_dir', 'sumo_configs/routes/hangzhou')
TLS_ID = net_cfg.get('tls_id', 'B1')
DELTA_T = int(sumo_cfg.get('step_length', 5))
MAX_STEPS = int(sumo_cfg.get('end_time', 3600)) // DELTA_T
END_TIME = int(sumo_cfg.get('end_time', 3600))

# Buscar ruta
from pathlib import Path
route_files = sorted(Path(ROUTE_DIR).glob('*.rou.xml'))
ROUTE_FILE = str(route_files[0]) if route_files else 'sumo_configs/routes/hangzhou/hangzhou_minimal.rou.xml'

# Crear sumocfg temporal
tmp_cfg = os.path.join(tempfile.gettempdir(), 'diag_test.sumocfg')
with open(tmp_cfg, 'w') as f:
    f.write(f'''<?xml version="1.0"?>
<configuration>
    <input><net-file value="{NETWORK}"/><route-files value="{ROUTE_FILE}"/></input>
    <time><begin value="0"/><end value="{END_TIME}"/></time>
    <processing><time-to-teleport value="-1"/></processing>
    <report><no-warnings value="true"/></report>
</configuration>''')

print("🔍 Iniciando entorno SIN wrappers para diagnóstico...")
env = TSCEnv(sumocfg_path=tmp_cfg, tls_id=TLS_ID, delta_t=DELTA_T, max_steps=MAX_STEPS, use_gui=False, seed=42)

obs, info = env.reset()
print(f"✅ Reset OK. Obs shape: {obs.shape}")
print(f"📦 Info inicial keys: {list(info.keys()) if isinstance(info, dict) else 'No es dict'}")

print("\n🚀 Ejecutando 5 pasos manuales...")
for step in range(5):
    action = env.action_space.sample() # Acción aleatoria
    obs, reward, terminated, truncated, info = env.step(action)
    
    print(f"\n--- Paso {step+1} ---")
    print(f"Reward crudo: {reward}")
    print(f"Terminated: {terminated}, Truncated: {truncated}")
    
    if isinstance(info, dict):
        print(f"Keys en Info: {list(info.keys())}")
        print(f"delay_mean: {info.get('delay_mean', 'NO EXISTE')}")
        print(f"wait_mean: {info.get('wait_mean', 'NO EXISTE')}")
        print(f"total_queue: {info.get('total_queue', 'NO EXISTE')}")
    elif isinstance(info, list) and len(info) > 0:
        i0 = info[0]
        if isinstance(i0, dict):
            print(f"Keys en Info[0]: {list(i0.keys())}")
            print(f"delay_mean: {i0.get('delay_mean', 'NO EXISTE')}")
        else:
            print("Info[0] no es diccionario")
    else:
        print("⚠️ Info no es dict ni lista válida")

env.close()
print("\n✅ Diagnóstico finalizado.")
