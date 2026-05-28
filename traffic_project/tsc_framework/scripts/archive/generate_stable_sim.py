import os
import random
import subprocess
import sys

# Configuración
NET_FILE = "experiments/hangzhou_robustness/scenarios/base_grid.net.xml"
TRIPS_FILE = "experiments/hangzhou_robustness/scenarios/stable.trips.xml"
ROUTES_FILE = "experiments/hangzhou_robustness/scenarios/stable_routes.rou.xml"
ADD_FILE = "experiments/hangzhou_robustness/scenarios/stable_final.add.xml"

random.seed(42)

print(f"🔍 Leyendo red con sumolib: {NET_FILE}...")
try:
    from sumolib import net
    n = net.readNet(NET_FILE)
    
    # Obtener bordes de entrada (fuente) y salida (destino) reales
    # Esto evita errores de rutas imposibles
    from_edges = [e.getID() for e in n.getEdges() if e.is_fringe() and e.getDirection() == '<' or e.getDirection() == '>'] 
    # Nota: is_fringe() devuelve los bordes del borde de la red. 
    # Para simplificar en grids, tomamos todos los fringe como posibles orígenes y destinos cruzados.
    
    # Estrategia robusta: Todos los fringe son posibles orígenes y destinos
    fringe_edges = [e.getID() for e in n.getEdges() if e.is_fringe()]
    
    if len(fringe_edges) < 2:
        print("⚠️ Pocos bordes fringe detectados. Usando todos los bordes no internos.")
        valid_edges = [e.getID() for e in n.getEdges() if not e.is_internal()]
        from_edges = valid_edges
        to_edges = valid_edges
    else:
        from_edges = fringe_edges
        to_edges = fringe_edges

    print(f"✅ Red cargada. {len(from_edges)} orígenes posibles, {len(to_edges)} destinos posibles.")

    # 1. Generar archivo de viajes (.trips.xml)
    print("📝 Generando archivo de viajes...")
    with open(TRIPS_FILE, 'w', encoding='utf-8') as f:
        f.write('<routes xmlns="http://sumo.dlr.de">\n')
        for i in range(200): # 200 vehículos
            src = random.choice(from_edges)
            dst = random.choice(to_edges)
            if src != dst:
                # Asignar tipo directamente en el trip
                v_type = "imprudent" if random.random() < 0.3 else "normal"
                depart = random.randint(0, 3500)
                f.write(f'  <trip id="veh_{i}" type="{v_type}" depart="{depart}" from="{src}" to="{dst}"/>\n')
        f.write('</routes>\n')
    print(f"   -> {TRIPS_FILE} creado.")

    # 2. Calcular rutas con duarouter (Esto garantiza que las rutas existen)
    print("🔄 Calculando rutas explícitas con duarouter...")
    # Nota: duarouter lee los trips y genera un .rou.xml con rutas completas (edge por edge)
    cmd = [
        "duarouter",
        "--net-file", NET_FILE,
        "--route-files", TRIPS_FILE, # Argumento corregido
        "--output-file", ROUTES_FILE,
        "--ignore-errors",
        "--begin", "0",
        "--end", "3600"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚠️ duarouter reportó advertencias/errores: {result.stderr}")
        # Continuamos si el archivo se generó aunque haya warnings
    
    if not os.path.exists(ROUTES_FILE) or os.path.getsize(ROUTES_FILE) < 100:
        print("❌ ERROR CRÍTICO: duarouter no generó rutas válidas. El archivo está vacío.")
        sys.exit(1)
    
    print(f"   -> {ROUTES_FILE} creado con rutas válidas.")

    # 3. Generar archivo adicional solo con definiciones de vehículos (Colores)
    # Ya no necesitamos <trip> aquí, solo los <vType> para que sumo-gui sepa los colores
    print("🎨 Generando definiciones de vehículos (colores)...")
    with open(ADD_FILE, 'w', encoding='utf-8') as f:
        f.write('<additional>\n')
        f.write('  <!-- Definiciones de tipos para visualización -->\n')
        f.write('  <vType id="normal" color="0,0.5,1" tau="1.0" sigma="0.5" speedFactor="1.0"/>\n')
        f.write('  <vType id="imprudent" color="0.9,0,0.9" tau="0.7" sigma="0.95" speedFactor="1.4"/>\n')
        f.write('</additional>\n')
    print(f"   -> {ADD_FILE} creado.")

    print("\n✅ ¡TODO LISTO! Ejecuta el siguiente comando para abrir SUMO:")
    print(f'sumo-gui -n "{NET_FILE}" -r "{ROUTES_FILE}" --additional-files "{ADD_FILE}" --start --delay 20')

except Exception as e:
    print(f"❌ Error fatal: {e}")
    import traceback
    traceback.print_exc()