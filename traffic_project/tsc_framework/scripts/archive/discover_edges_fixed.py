import subprocess
import traci
import time
import sys
import os

PORT = 8812
CFG_PATH = "sumo_configs/inspect_network.sumocfg"
SUMO_BINARY = "sumo"  # Usa el del PATH

print(f"🔍 Iniciando SUMO en puerto {PORT}...")

# Iniciar SUMO como proceso hijo
cmd = [SUMO_BINARY, "-c", CFG_PATH, "--remote-port", str(PORT), "--no-step-log", "--no-warnings"]
print(f"   Comando: {' '.join(cmd)}")

try:
    sumo_proc = subprocess.Popen(cmd)
    
    # Esperar a que SUMO arranque (crucial en Windows)
    time.sleep(2) 
    
    # Intentar conectar
    print("📡 Conectando a TraCI...")
    traci.connect(port=PORT)
    print("✅ Conexión establecida.")

    # Obtener lista de semáforos
    tls_list = traci.trafficlight.getIDList()
    print(f"💡 Semáforos encontrados: {len(tls_list)}")
    if tls_list:
        print(f"   IDs: {tls_list}")
        
        # Inspeccionar el primero (ej. B1 o el que exista)
        target_tls = tls_list[0] 
        if 'B1' in tls_list:
            target_tls = 'B1'
            
        lanes = traci.trafficlight.getControlledLanes(target_tls)
        print(f"🛣️  Carriles controlados por '{target_tls}': {lanes}")
        
        # Extraer edges únicos
        edges = list(set([lane.split('_')[0] for lane in lanes]))
        print(f"🔗 Edges únicos detectados: {edges}")
        
        # Intentar inferir una ruta simple (Edge actual -> Siguiente)
        # Nota: Esto es una heurística simple. Para una ruta perfecta se necesita el grafo completo.
        if len(edges) >= 2:
            suggested_route = " ".join(edges[:2])
            print(f"💡 Ruta sugerida para XML: <route id='r0' edges='{suggested_route}' />")
        else:
            print("⚠️  No hay suficientes edges para sugerir una ruta automática.")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    print("🛑 Cerrando conexión...")
    try:
        traci.close()
    except: pass
    
    print("🛑 Terminando proceso SUMO...")
    try:
        sumo_proc.terminate()
        sumo_proc.wait(timeout=3)
    except: 
        # Forzar muerte si no responde
        subprocess.run(["taskkill", "/F", "/PID", str(sumo_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Limpieza completada.")
