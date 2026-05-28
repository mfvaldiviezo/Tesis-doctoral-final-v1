import csv
import xml.etree.ElementTree as ET
from pathlib import Path

output_file = Path('results/quito_scenarios/imprudent_drivers_fixed.rou.xml')
summary_file = Path('results/quito_scenarios/scenario_summary.csv')

# Leer resumen para ver columnas disponibles
data = []
with open(summary_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    print(f"Columnas disponibles: {fieldnames}")
    for row in reader:
        data.append(row)

if len(data) == 0:
    print("ERROR: No hay datos en el CSV")
    exit(1)

# Crear XML
root = ET.Element('routes')
comment = ET.Comment(' Vehicle types based on Quito driving behavior - Fixed ')
root.append(comment)

# Identificar columnas de comportamiento (buscar por patron)
sigma_col = next((c for c in fieldnames if 'sigma' in c.lower()), 'sigma')
tau_col = next((c for c in fieldnames if 'tau' in c.lower()), 'tau')
speed_col = next((c for c in fieldnames if 'speed' in c.lower() and 'factor' in c.lower()), 'speed_factor')
accel_col = next((c for c in fieldnames if 'accel' in c.lower()), 'accel')
decel_col = next((c for c in fieldnames if 'decel' in c.lower()), 'decel')
driver_col = next((c for c in fieldnames if 'driver' in c.lower() or 'id' in c.lower()), None)
stress_col = next((c for c in fieldnames if 'stress' in c.lower()), 'stress_level')
color_col = next((c for c in fieldnames if 'color' in c.lower()), 'color_g')

print(f"Mapeo de columnas: sigma={sigma_col}, tau={tau_col}, speed={speed_col}, accel={accel_col}, decel={decel_col}, driver={driver_col}, stress={stress_col}, color={color_col}")

vtypes_added = set()

for i, row in enumerate(data):
    if driver_col and driver_col in row:
        driver_id = row[driver_col]
    else:
        driver_id = f"driver_{i % 7}"
    
    stress = row.get(stress_col, 'nominal')
    vtype_id = f"imprudent_{driver_id}_{stress}"
    
    if vtype_id not in vtypes_added and i < 50:  # Solo primeros 50 para no saturar
        vtype = ET.SubElement(root, 'vType')
        vtype.set('id', vtype_id)
        vtype.set('sigma', str(row.get(sigma_col, '0.5')))
        vtype.set('tau', str(row.get(tau_col, '1.0')))
        vtype.set('speedFactor', str(row.get(speed_col, '1.0')))
        vtype.set('accel', str(row.get(accel_col, '0.5')))
        vtype.set('decel', str(row.get(decel_col, '0.5')))
        color_g = row.get(color_col, '0.5')
        vtype.set('color', f"1,{color_g},0")
        vtypes_added.add(vtype_id)

# Añadir algunas rutas y vehiculos de prueba
for i in range(min(20, len(data))):
    route = ET.SubElement(root, 'route')
    route.set('id', f'route_{i}')
    route.set('edges', 'edge_0 edge_1 edge_2 edge_3')
    
    vehicle = ET.SubElement(root, 'vehicle')
    vehicle.set('id', f'veh_test_{i}')
    vehicle.set('type', list(vtypes_added)[i % len(vtypes_added)])
    vehicle.set('route', f'route_{i}')
    vehicle.set('depart', str(i * 30))

tree = ET.ElementTree(root)
with open(output_file, 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print(f'\nArchivo corregido generado: {output_file}')
print('Validando XML...')
try:
    ET.parse(output_file)
    print('XML valido!')
except Exception as e:
    print(f'ERROR en XML: {e}')
