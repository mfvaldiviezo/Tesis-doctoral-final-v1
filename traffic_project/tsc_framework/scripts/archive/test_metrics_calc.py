import sys, os, tempfile, time
sys.path.insert(0, '.')
import traci
from src.core.tsc_env import TSCEnv

print("🔍 PRUEBA DE CÁLCULO DE MÉTRICAS EN VIVO")
print("="*50)

# Configurar entorno manual
NET = "sumo_configs/networks/hangzhou_4x4.net.xml"
ROUTE = "sumo_configs/routes/hangzhou/hangzhou_minimal.rou.xml"
TLS = "B1"

sumocfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NET}"/>
        <route-files value="{ROUTE}"/>
    </input>
    <time><begin value="0"/><end value="3600"/></time>
    <processing><time-to-teleport value="-1"/></processing>
    <report><no-warnings value="true"/></report>
</configuration>'''

tmp_cfg = os.path.join(tempfile.gettempdir(), "test_metrics.sumocfg")
with open(tmp_cfg, "w", encoding="utf-8") as f:
    f.write(sumocfg_content)

env = TSCEnv(sumocfg_path=tmp_cfg, tls_id=TLS, delta_t=5, max_steps=720, use_gui=False, seed=42)
obs, info = env.reset()

print(f"✅ Entorno iniciado. Simulación corriendo.")

for step in range(10):
    # Antes de hacer step, leer datos CRUDOS de TraCI directamente desde el objeto env si es posible
    # Como TSCEnv encapsula traci, intentaremos acceder a través de métodos públicos o atributos protegidos
    
    # Hacemos el step con acción 0
    obs, reward, term, trunc, info = env.step(0)
    
    # Lectura DIRECTA de TraCI (asumiendo que env.traci existe tras el reset/step)
    # Si no existe, usaremos los valores de info que ya sabemos que son 0
    try:
        # Intentar acceder al objeto traci interno (comúnmente self.traci en TSCEnv)
        t = env.traci 
        vehicles = t.vehicle.getIDList()
        queues = []
        delays = []
        
        for v in vehicles:
            wait = t.vehicle.getWaitingTime(v)
            speed = t.vehicle.getSpeed(v)
            queues.append(1 if wait > 0 else 0) # Simplificación
            # Delay es más complejo, depende de tiempo ideal vs real
            
        print(f"Paso {step+1}: Vehículos={len(vehicles)}, Esperando={sum(queues)}, Info.Delay={info.get('delay', 'N/A')}")
        
    except AttributeError:
        print(f"Paso {step+1}: No se pudo acceder a env.traci directamente. Info.Delay={info.get('delay')}")

env.close()
print("✅ Prueba finalizada.")
