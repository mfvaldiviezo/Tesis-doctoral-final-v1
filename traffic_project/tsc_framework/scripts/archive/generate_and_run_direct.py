import xml.etree.ElementTree as ET
import random
import os
from sumolib import net

random.seed(42)
net_file = 'experiments/hangzhou_robustness/scenarios/test_grid.net.xml'
output_add = 'experiments/hangzhou_robustness/scenarios/imprudent_scenario.add.xml'

print("Leyendo red para obtener bordes válidos...")
n = net.readNet(net_file)
edges = [e.getID() for e in n.getEdges()]
fringe_in = [e.getID() for e in n.getEdges() if e.is_fringe() and not e.is_fringe_output()]
fringe_out = [e.getID() for e in n.getEdges() if e.is_fringe() and e.is_fringe_output()]

if not fringe_in or not fringe_out:
    print("Usando todos los bordes como fallback...")
    fringe_in = edges
    fringe_out = edges

print(f"Bordes entrada: {len(fringe_in)}, salida: {len(fringe_out)}")

root = ET.Element('additional')
root.set('xmlns', 'http://sumo.dlr.de')

# 1. Definir Tipos de Vehículos (Colores)
# Normal (Azul)
vtype_normal = ET.SubElement(root, 'vType')
vtype_normal.set('id', 'normal_car')
vtype_normal.set('sigma', '0.5')
vtype_normal.set('tau', '1.0')
vtype_normal.set('speedFactor', '1.0')
vtype_normal.set('accel', '0.8')
vtype_normal.set('decel', '0.8')
vtype_normal.set('color', '0,0.5,1') # Azul

# Imprudente (Violeta Neón) - Basado en datos de Quito
vtype_imprudent = ET.SubElement(root, 'vType')
vtype_imprudent.set('id', 'imprudent_quito')
vtype_imprudent.set('sigma', '1.8')   # Más variabilidad
vtype_imprudent.set('tau', '0.6')     # Menor tiempo de reacción
vtype_imprudent.set('speedFactor', '1.3') # Más rápido
vtype_imprudent.set('accel', '1.5')   # Acelera fuerte
vtype_imprudent.set('decel', '2.5')   # Frena brusco
vtype_imprudent.set('color', '0.9,0,0.9') # Violeta

# 2. Generar Trips (SUMO calculará la ruta)
total_vehicles = 300
imprudent_ratio = 0.3

print(f"Generando {total_vehicles} trips...")
for i in range(total_vehicles):
    trip = ET.SubElement(root, 'trip')
    trip.set('id', f'veh_{i}')
    trip.set('depart', str(random.randint(0, 3500)))
    
    # Asignar tipo
    is_imprudent = random.random() < imprudent_ratio
    trip.set('type', 'imprudent_quito' if is_imprudent else 'normal_car')
    
    # Origen/Destino válidos
    from_edge = random.choice(fringe_in)
    to_edge = random.choice(fringe_out)
    
    # Asegurar que no sean el mismo
    attempts = 0
    while from_edge == to_edge and attempts < 10:
        to_edge = random.choice(fringe_out)
        attempts += 1
    
    trip.set('from', from_edge)
    trip.set('to', to_edge)

# Guardar
tree = ET.ElementTree(root)
with open(output_add, 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print(f"✅ Archivo generado: {output_add}")
print(f"   - Tipos de vehículo: 2 (Normal Azul, Imprudente Violeta)")
print(f"   - Total trips: {total_vehicles}")
print(f"   - Ratio imprudentes: ~{imprudent_ratio*100}%")

# Lanzar simulación
print("\n🚀 Iniciando sumo-gui...")
os.system(f'sumo-gui -n {net_file} -a {output_add} --end 3600 --start')
