import xml.etree.ElementTree as ET
import random
import subprocess
import os

random.seed(42)

net_file = 'experiments/hangzhou_robustness/scenarios/base_grid.net.xml'
trips_file = 'experiments/hangzhou_robustness/scenarios/sim.trips.xml'
routes_file = 'experiments/hangzhou_robustness/scenarios/sim.rou.xml'
add_file = 'experiments/hangzhou_robustness/scenarios/sim_types.add.xml'

print("🔍 Leyendo red directamente con ElementTree...")
tree = ET.parse(net_file)
root = tree.getroot()

# Extraer todos los IDs de edges que no sean internos (no empiezan con :)
edges = []
for elem in root.iter('edge'):
    eid = elem.get('id')
    if eid and not eid.startswith(':'):
        edges.append(eid)

print(f"✅ Encontrados {len(edges)} bordes válidos: {edges[:5]}...")

if len(edges) < 2:
    print("❌ Error: No hay suficientes bordes.")
    exit(1)

# 1. Generar archivo de trips (solo origen/destino, sin tipos aún)
print("📝 Generando archivo de viajes (trips)...")
with open(trips_file, 'w', encoding='utf-8') as f:
    f.write('<routes xmlns="http://sumo.dlr.de">\n')
    for i in range(100):
        src = random.choice(edges)
        dst = random.choice(edges)
        while src == dst:
            dst = random.choice(edges)
        depart = random.randint(0, 1800)
        f.write(f'  <trip id="trip_{i}" depart="{depart}" from="{src}" to="{dst}"/>\n')
    f.write('</routes>\n')
print(f"   -> {trips_file}")

# 2. Calcular rutas con duarouter
print("🔄 Calculando rutas con duarouter...")
try:
    subprocess.run([
        'duarouter',
        '--net-file', net_file,
        '--route-files', trips_file,
        '--output-file', routes_file,
        '--ignore-errors',
        '--begin', '0',
        '--end', '3600'
    ], check=True, capture_output=True, text=True)
    
    # Verificar si se generaron rutas
    if os.path.getsize(routes_file) < 1000:
        print("⚠️ Advertencia: El archivo de rutas es muy pequeño.")
    else:
        print("   -> Rutas calculadas correctamente.")
except Exception as e:
    print(f"❌ Error en duarouter: {e}")
    # Crear un archivo de rutas vacío válido para no romper el siguiente paso
    with open(routes_file, 'w') as f:
        f.write('<routes xmlns="http://sumo.dlr.de"></routes>')

# 3. Generar archivo adicional SOLO con tipos de vehículos (sin trips)
print("🎨 Generando definición de tipos de vehículos...")
with open(add_file, 'w', encoding='utf-8') as f:
    f.write('<additional xmlns="http://sumo.dlr.de">\n')
    f.write('  <!-- Vehículos Normales (Azules) -->\n')
    f.write('  <vType id="normal" color="0,0.5,1" tau="1.0" sigma="0.5" speedFactor="1.0" guiShape="passenger"/>\n')
    f.write('  <!-- Vehículos Imprudentes (Violetas) -->\n')
    f.write('  <vType id="imprudent" color="0.9,0,0.9" tau="0.8" sigma="0.9" speedFactor="1.3" guiShape="sport"/>\n')
    f.write('</additional>\n')
print(f"   -> {add_file}")

# 4. Post-procesar rutas para asignar tipos aleatorios
print("🎲 Asignando tipos de vehículos a las rutas...")
# Leemos las rutas calculadas
routes_tree = ET.parse(routes_file)
routes_root = routes_tree.getroot()

# Buscamos todos los elementos vehicle o trip que tengan ruta
count = 0
for vehicle in routes_root.findall('.//vehicle'):
    if count < 100: # Limitar a 100 vehículos
        vtype = 'imprudent' if random.random() < 0.3 else 'normal'
        vehicle.set('type', vtype)
        # Asegurar color individual si el tipo no carga bien
        if vtype == 'imprudent':
            vehicle.set('color', '0.9,0,0.9')
        else:
            vehicle.set('color', '0,0.5,1')
        count += 1

# Guardar rutas modificadas
final_routes = 'experiments/hangzhou_robustness/scenarios/sim_final.rou.xml'
routes_tree.write(final_routes, encoding='utf-8', xml_declaration=True)
print(f"   -> {final_routes} ({count} vehículos)")

# 5. Lanzar SUMO
print("\n🚀 Iniciando SUMO-GUI...")
print("💡 Tips:")
print("   - Presiona 'L' si los semáforos se ven grises.")
print("   - Violeta = Imprudente, Azul = Normal.")
print("   - Cierra la ventana para terminar.")

subprocess.run([
    'sumo-gui',
    '-n', net_file,
    '-r', final_routes,
    '--additional-files', add_file,
    '--start',
    '--end', '3600',
    '--delay', '20'
])