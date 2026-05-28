import csv
import xml.etree.ElementTree as ET
from pathlib import Path

output_file = Path('results/quito_scenarios/imprudent_drivers.rou.xml')
summary_file = Path('results/quito_scenarios/scenario_summary.csv')

# Leer resumen
data = []
with open(summary_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

# Crear XML manualmente asegurando codificación correcta
root = ET.Element('routes')

# Comentario seguro (sin caracteres especiales)
comment = ET.Comment(' Vehicle types based on Quito driving behavior ')
root.append(comment)

# Tipos únicos de conductores
drivers = set(row['driver_id'] for row in data)
vtypes_added = set()

for row in data:
    vtype_id = f"imprudent_{row['driver_id']}_{row['stress_level']}"
    if vtype_id not in vtypes_added:
        vtype = ET.SubElement(root, 'vType')
        vtype.set('id', vtype_id)
        vtype.set('sigma', str(row['sigma']))
        vtype.set('tau', str(row['tau']))
        vtype.set('speedFactor', str(row['speed_factor']))
        vtype.set('accel', str(row['accel']))
        vtype.set('decel', str(row['decel']))
        vtype.set('color', f"1,{row['color_g']},0")
        vtypes_added.add(vtype_id)

# Añadir rutas y vehículos de ejemplo (solo 10 para validar)
for i, row in enumerate(data[:10]):
    route = ET.SubElement(root, 'route')
    route.set('id', f'route_{i}')
    route.set('edges', 'edge_0 edge_1 edge_2 edge_3')

    vehicle = ET.SubElement(root, 'vehicle')
    vehicle.set('id', f'veh_{i}')
    vehicle.set('type', f"imprudent_{row['driver_id']}_{row['stress_level']}")
    vehicle.set('route', f'route_{i}')
    vehicle.set('depart', str(i * 10))

tree = ET.ElementTree(root)
with open(output_file, 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print(f'Archivo corregido generado: {output_file}')
print('Validando XML...')
ET.parse(output_file)
print('XML válido!')
