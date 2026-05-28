import os
import sys
import subprocess
import time
import traci

# Configuración
NET_FILE = "sumo_configs/networks/hangzhou_4x4.net.xml"
PORT = 8888  # Puerto fijo para evitar conflictos aleatorios

def main():
    print(f"🔍 Iniciando SUMO para inspeccionar la red (Puerto {PORT})...")
    
    # 1. Iniciar SUMO en segundo plano
    # Usamos 'sumo' directamente ya que está en el PATH del entorno conda
    cmd = [
        "sumo",
        "-n", NET_FILE,
        "--remote-port", str(PORT),
        "--step-length", "1000",  # Pausa larga para darnos tiempo a conectar
        "--no-step-log",
        "--no-warnings"
    ]
    
    print(f"   Comando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    
    # 2. Esperar a que SUMO arranque
    time.sleep(2)
    
    try:
        # 3. Conectar (¡Importante: PORT como int!)
        traci.connect(port=PORT)
        print("✅ Conexión exitosa.")
        
        # 4. Obtener lista de todos los semáforos
        tls_list = traci.trafficlight.getIDList()
        print(f"🚦 Semáforos encontrados: {len(tls_list)}")
        print(f"   IDs: {tls_list}")
        
        if not tls_list:
            print("❌ No se encontraron semáforos. Verifica el archivo .net.xml")
            return

        # 5. Inspeccionar el primer semáforo (o B1 si existe)
        target_tls = "B1" if "B1" in tls_list else tls_list[0]
        print(f"\n�� Inspeccionando semáforo objetivo: {target_tls}")
        
        lanes = traci.trafficlight.getControlledLanes(target_tls)
        print(f"   Carriles controlados: {lanes}")
        
        # Extraer edges únicos
        edges = set()
        for lane in lanes:
            # El formato usual es 'edge_laneIndex', ej: 'B1-B2_0'
            edge_id = lane.rsplit('_', 1)[0] 
            edges.add(edge_id)
            
        print(f"   Edges únicos detectados: {sorted(edges)}")
        
        # 6. Sugerir una ruta válida (conectando 2-3 edges)
        edges_list = sorted(list(edges))
        if len(edges_list) >= 2:
            suggested_route = " ".join(edges_list[:3]) # Toma los primeros 3
            print(f"\n💡 Ruta sugerida para tu archivo .rou.xml:")
            print(f'   <route id="r0" edges="{suggested_route}" />')
        else:
            print("⚠️ No hay suficientes edges conectados visibles desde este semáforo.")
            
    except Exception as e:
        print(f"❌ Error durante la inspección: {e}")
    finally:
        # 7. Limpiar
        try:
            traci.close()
            print("👋 Conexión cerrada.")
        except:
            pass
        
        # Matar el proceso SUMO si sigue vivo
        if proc.poll() is None:
            proc.terminate()
            print("🛑 Proceso SUMO terminado.")

if __name__ == "__main__":
    main()
