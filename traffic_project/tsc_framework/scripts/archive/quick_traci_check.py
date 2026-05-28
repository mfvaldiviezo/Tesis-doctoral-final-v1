import sys, os, tempfile, time, subprocess
sys.path.insert(0, '.')
import traci

PORT = 8877
NET = "sumo_configs/networks/hangzhou_4x4.net.xml"
ROUTE = "sumo_configs/routes/hangzhou/hangzhou_minimal.rou.xml"

cfg = f'''<?xml version="1.0"?>
<configuration><input><net-file value="{NET}"/><route-files value="{ROUTE}"/></input>
<time><begin value="0"/><end value="3600"/></time><processing><time-to-teleport value="-1"/></processing></configuration>'''

tmp = os.path.join(tempfile.gettempdir(), "quick_test.sumocfg")
with open(tmp, 'w') as f: f.write(cfg)

proc = subprocess.Popen(['sumo', '-c', tmp, '--remote-port', str(PORT), '--no-step-log', '--no-warnings'])
time.sleep(2)

try:
    traci.connect(port=PORT)
    print("✅ Conectado. Simulando 10 pasos...")
    for i in range(10):
        traci.simulationStep()
        # Métricas directas de TraCI
        waiting = traci.vehicle.getWaitingTimeCollection() # Lista de tiempos de espera
        avg_wait = sum(waiting)/len(waiting) if waiting else 0
        vehicles = traci.vehicle.getIDList()
        print(f"Paso {i}: Vehículos={len(vehicles)}, Avg Wait={avg_wait:.2f}s")
        # Intentar obtener delay acumulado si existe
        # traci no tiene 'delay' directo global, se calcula de travelTime - edge length/speed
except Exception as e:
    print(f"Error: {e}")
finally:
    traci.close()
    proc.terminate()
