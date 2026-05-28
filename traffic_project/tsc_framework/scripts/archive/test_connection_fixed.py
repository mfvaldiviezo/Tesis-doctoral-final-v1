import subprocess
import traci
import time
import os
import sys

# Rutas absolutas hardcodeadas (corregidas)
NET_FILE = r"C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework\sumo_configs\networks\hangzhou_4x4.net.xml"
ROUTE_FILE = r"C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework\sumo_configs\routes\hangzhou\hangzhou_minimal.rou.xml"
PORT = 8899

print(f"🔍 Probando conexión TraCI...")
print(f"   Net:   {os.path.basename(NET_FILE)}")
print(f"   Route: {os.path.basename(ROUTE_FILE)}")

# Verificar existencia de archivos antes de lanzar
if not os.path.exists(NET_FILE):
    print(f"❌ ERROR CRÍTICO: El archivo de red NO existe: {NET_FILE}")
    sys.exit(1)
if not os.path.exists(ROUTE_FILE):
    print(f"❌ ERROR CRÍTICO: El archivo de rutas NO existe: {ROUTE_FILE}")
    sys.exit(1)

# Crear config temporal
import tempfile
cfg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{NET_FILE}"/>
        <route-files value="{ROUTE_FILE}"/>
    </input>
    <time><begin value="0"/><end value="100"/></time>
    <processing><time-to-teleport value="-1"/></processing>
    <report><no-warnings value="true"/><no-step-log value="true"/></report>
</configuration>'''

tmp_cfg = os.path.join(tempfile.gettempdir(), "test_conn_fix.sumocfg")
with open(tmp_cfg, "w", encoding="utf-8") as f:
    f.write(cfg_content)

print("🚀 Lanzando SUMO...")
cmd = ["sumo", "-c", tmp_cfg, "--remote-port", str(PORT), "--no-step-log", "--no-warnings"]
try:
    sumo_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5) # Dar más tiempo a Windows para levantar el socket
    
    if sumo_proc.poll() is not None:
        print("❌ SUMO terminó inmediatamente al iniciar.")
        sys.exit(1)
        
    print("📡 Conectando a TraCI...")
    traci.connect(port=PORT)
    
    print("✅ ¡CONEXIÓN EXITOSA!")
    print(f"   Tiempo simulación: {traci.simulation.getTime():.1f}s")
    print(f"   Vehículos activos: {traci.simulation.getVehicleNumber()}")
    
    # Probar semáforo
    tls_list = traci.trafficlight.getIDList()
    if 'B1' in tls_list:
        lanes = traci.trafficlight.getControlledLanes('B1')
        print(f"   Semáforo B1: OK ({len(lanes)} carriles)")
    else:
        print(f"   Semáforos encontrados: {tls_list}")
        
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    try:
        traci.close()
    except: pass
    try:
        sumo_proc.terminate()
        sumo_proc.wait(timeout=2)
    except: 
        subprocess.run(["taskkill", "/F", "/PID", str(sumo_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("🛑 Proceso cerrado.")
