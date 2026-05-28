import random
import xml.etree.ElementTree as ET
from sumolib import net
import os
import subprocess
import sys

# Configuración
NET_FILE = 'experiments/hangzhou_robustness/scenarios/test_grid.net.xml'
OUTPUT_ROU = 'experiments/hangzhou_robustness/scenarios/test_grid_direct.rou.xml'
IMPRUDENT_FILE = 'results/quito_scenarios/imprudent_drivers_fixed.rou.xml'
N_VEHICLES = 300
RATIO_IMPRUDENT = 0.3

print(f"1. Leyendo red: {NET_FILE}...")
try:
    n = net.readNet(NET_FILE)
    # Obtener todos los edges que NO son de salida (fringe) para usar como origen/destino interno si es necesario
    # Pero para tráfico de paso, usamos los fringe
    all_edges = [e.getID() for e in n.getEdges()]
    fringe_in = [e.getID() for e in n.getEdges() if e.is_fringe() and len(e.getOutgoing()) > 0]
    fringe_out = [e.getID() for e in n.getEdges() if e.is_fringe() and len(e.getIncoming()) > 0]
    
    if not fringe_in or not fringe_out:
        print("Advertencia: No se detectaron bordes periféricos claros. Usando todos los edges.")
        fringe_in = all_edges
        fringe_out = all_edges
        
    print(f"   Bordes de entrada disponibles: {len(fringe_in)}")
    print(f"   Bordes de salida disponibles: {len(fringe_out)}")
except Exception as e:
    print(f"ERROR fatal leyendo la red: {e}")
    sys.exit(1)

print(f"2. Generando {N_VEHICLES} vehículos directamente en {OUTPUT_ROU}...")
random.seed(42)

root = ET.Element('routes')
root.set('xmlns', 'http://sumo.dlr.de')

# Añadir tipos de vehículos normales
normal_type = ET.SubElement(root, 'vType')
normal_type.set('id', 'normal_car')
normal_type.set('color', '0,0.5,1')  # Azul
normal_type.set('sigma', '0.5')
normal_type.set('tau', '1.0')

# Cargar tipos imprudentes si existe el archivo
imprudent_types = []
if os.path.exists(IMPRUDENT_FILE):
    try:
        imp_tree = ET.parse(IMPRUDENT_FILE)
        imp_root = imp_tree.getroot()
        for vtype in imp_root.findall('vType'):
            # Copiar el tipo
            new_vtype = ET.SubElement(root, 'vType')
            for k, v in vtype.attrib.items():
                new_vtype.set(k, v)
            imprudent_types.append(vtype.get('id'))
        print(f"   Cargados {len(imprudent_types)} tipos de vehículos imprudentes.")
    except Exception as e:
        print(f"Advertencia: No se pudieron cargar tipos imprudentes: {e}")

# Generar vehículos
vehicles_added = 0
for i in range(N_VEHICLES):
    is_imprudent = (random.random() < RATIO_IMPRUDENT) and (len(imprudent_types) > 0)
    
    # Elegir origen y destino aleatorios distintos
    from_edge = random.choice(fringe_in)
    to_edge = random.choice(fringe_out)
    attempts = 0
    while from_edge == to_edge and attempts < 10:
        to_edge = random.choice(fringe_out)
        attempts += 1
    
    if from_edge == to_edge:
        continue # Saltar si no hay par válido
        
    depart = random.randint(0, 3500)
    
    vehicle = ET.SubElement(root, 'vehicle')
    vid = f"veh_{i}"
    vehicle.set('id', vid)
    vehicle.set('depart', str(depart))
    
    if is_imprudent:
        vtype_id = random.choice(imprudent_types)
        vehicle.set('type', vtype_id)
    else:
        vehicle.set('type', 'normal_car')
        
    # Definir ruta explícita (SUMO intentará calcularla si no encuentra path, pero es mejor dar una si se puede)
    # Para simplificar, usamos un elemento <route> con from/to y dejamos que SUMO calcule el path al cargar
    # O mejor, definimos la ruta aquí mismo si conocemos el path, pero como no tenemos el grafo completo en memoria fácil:
    # Usaremos la estrategia de definir el vehículo con from/to y dejar que duarouter o el propio sumo lo resuelva?
    # No, el formato directo de vehículo requiere 'route' o 'from'/'to' si se usa junto con --routing-algorithm en suma
    # La forma más compatible es definir un <route> separado y referenciarlo.
    
    route_id = f"route_{i}"
    route = ET.SubElement(root, 'route')
    route.set('id', route_id)
    route.set('edges', from_edge) # Truco: si solo ponemos un edge, a veces falla. Necesitamos path.
    
    # CORRECCIÓN: La forma infalible sin calcular path manual es usar <trip> dentro del archivo .rou.xml y pasar --routing-algorithm a sumo
    # O mejor, generar un archivo .trip.xml y usar duarouter correctamente.
    # Dado que duarouter falló antes, intentemos la vía directa con <vehicle> y atributos from/to, que SUMO-GUI soporta si se le indica.
    # Pero el estándar estricto requiere edges.
    
    # ESTRATEGIA FINAL ROBUSTA:
    # Eliminar el route anterior y usar atributos 'from' y 'to' en el vehículo. 
    # SUMO los aceptará y calculará la ruta al vuelo si la red tiene conexión.
    root.remove(route) # Quitar el route incompleto
    
    vehicle.set('from', from_edge)
    vehicle.set('to', to_edge)
    
    vehicles_added += 1

print(f"   Vehículos generados: {vehicles_added}")

# Escribir archivo
tree = ET.ElementTree(root)
with open(OUTPUT_ROU, 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print(f"3. Archivo guardado: {OUTPUT_ROU}")

# 4. Lanzar SUMO-GUI
print("4. Iniciando SUMO-GUI...")
cmd = [
    'sumo-gui',
    '-n', NET_FILE,
    '-r', OUTPUT_ROU,
    '--end', '3600',
    '--start',
    '--collision.action', 'none', # Evitar teletransporte excesivo por errores de ruta
    '--routing-algorithm', 'dijkstra'
]

subprocess.run(cmd)
