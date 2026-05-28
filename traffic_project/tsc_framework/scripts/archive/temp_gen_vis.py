import random
import re
import os

random.seed(42)
net_path = 'experiments/hangzhou_robustness/scenarios/test_grid_tls.net.xml'
add_path = 'experiments/hangzhou_robustness/scenarios/visual_tls.add.xml'

if not os.path.exists(net_path):
    print(f"ERROR: No existe {net_path}")
    exit(1)

print("🔍 Leyendo bordes de la red...")
edges = []
with open(net_path, 'r', encoding='utf-8') as f:
    content = f.read()
    matches = re.findall(r'id="([^"]+)"', content)
    # Filtrar bordes válidos (no internos, no demasiado cortos)
    edges = [m for m in matches if not m.startswith(':') and len(m) > 3]

if len(edges) < 2:
    print("❌ ERROR: No se encontraron bordes válidos.")
    exit(1)

print(f"✅ Encontrados {len(edges)} bordes válidos.")

with open(add_path, 'w', encoding='utf-8') as f:
    f.write('<additional>\n')
    # Tipos de vehículos (Colores: Azul=Normal, Violeta=Imprudente)
    f.write('  <vType id="normal" color="0,0.5,1" tau="1.0" sigma="0.5" speedFactor="1.0"/>\n')
    f.write('  <vType id="imprudent" color="0.8,0,0.8" tau="0.6" sigma="0.9" speedFactor="1.3"/>\n')

    # Generar viajes
    count = 0
    for i in range(200):
        depart = random.randint(0, 3500)
        src = random.choice(edges)
        dst = random.choice(edges)
        while src == dst:
            dst = random.choice(edges)

        vtype = 'imprudent' if random.random() < 0.3 else 'normal'
        f.write(f'  <trip id="veh_{i}" type="{vtype}" depart="{depart}" from="{src}" to="{dst}"/>\n')
        count += 1
    
    f.write('</additional>\n')

print(f"✅ Archivo generado: {add_path} ({count} vehículos)")
