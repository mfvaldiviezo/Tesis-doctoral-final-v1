import sys
import os
import subprocess
import time
import traci

# Forzar rutas absolutas
ROOT = os.path.abspath(os.path.dirname(__file__))
NET_FILE = os.path.join(ROOT, "sumo_configs", "networks", "hangzhou_4x4.net.xml")
ROUTE_FILE = os.path.join(ROOT, "sumo_configs", "routes", "hangzhou", "hangzhou_minimal.rou.xml")
SUMO_BINARY = "sumo"  # Asumiendo que está en PATH

print(f"🔍 Probando conexión TraCI con rutas absolutas...")
print(f"   Net: {NET_FILE}")
print(f"   Route: {ROUTE_FILE}")

# Crear archivo .sumocfg temporal con rutas absolutas
import tempfile
tmp_cfg = os.path.join(tempfile.gettempdir(), "test_abs_conn.sumocfg")
cfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NET_FILE}"/>
        <route-files value="{ROUTE_FILE}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="100"/>
        <step-length value="5"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
    <report>
        <no-warnings value="true"/>
        <no-step-log value="true"/>
    </report>
</configuration>'''

with open(tmp_cfg, "w", encoding="utf-8") as f:
    f.write(cfg_content)

PORT = 8899
cmd = [SUMO_BINARY, "-c", tmp_cfg, "--remote-port", str(PORT), "--no-step-log", "--no-warnings"]

print(f"🚀 Lanzando SUMO en puerto {PORT}...")
try:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # Esperar a que SUMO inicie
    
    print("📡 Conectando a TraCI...")
    traci.connect(port=PORT)
    
    # Probar obtener información básica
    sim_time = traci.simulation.getTime()
    vehicles = traci.vehicle.getIDList()
    print(f"✅ Conexión exitosa!")
    print(f"   Tiempo simulación: {sim_time}s")
    print(f"   Vehículos activos: {len(vehicles)}")
    
    # Probar semáforo B1
    tls_list = traci.trafficlight.getIDList()
    if "B1" in tls_list:
        lanes = traci.trafficlight.getControlledLanes("B1")
        print(f"   Semáforo B1 encontrado con {len(lanes)} carriles controlados")
        
        # Obtener métricas de un carril
        if len(lanes) > 0:
            queue = traci.lane.getLastStepHaltingNumber(lanes[0])
            print(f"   Cola en carril {lanes[0]}: {queue} vehículos")
    
    traci.close()
    print("🛑 Conexión cerrada correctamente.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        proc.terminate()
        proc.wait(timeout=3)
        print("✅ Proceso SUMO terminado.")
    except:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
