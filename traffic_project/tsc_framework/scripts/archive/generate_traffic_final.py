# scripts/generate_traffic_final.py
import random, re, os

random.seed(42)

# Rutas fijas para evitar problemas con variables de PowerShell
base_net = 'experiments/hangzhou_robustness/scenarios/base_grid.net.xml'
add_file = 'experiments/hangzhou_robustness/scenarios/visual_final.add.xml'

print(f"🔍 Leyendo red desde: {base_net}...")

if not os.path.exists(base_net):
    print("❌ ERROR: No se encuentra el archivo de red base.")
    exit(1)

edges = []
with open(base_net, 'r', encoding='utf-8') as f:
    content = f.read()
    # Buscar IDs que parezcan bordes normales (tienen guion bajo, no empiezan con :)
    matches = re.findall(r'id="([^"]+)"', content)
    edges = [m for m in matches if not m.startswith(':') and '_' in m and len(m) < 15]

edges = list(set(edges))
print(f'✅ Bordes encontrados: {len(edges)}')

if len(edges) >= 2:
    print(f"📝 Generando archivo de tráfico en: {add_file}...")
    with open(add_file, 'w', encoding='utf-8') as f:
        f.write('<additional>\n')
        # Tipos: Normal (Azul), Imprudente (Violeta)
        f.write('  <vType id="normal" color="0,0.5,1" tau="1.0" sigma="0.5" speedFactor="1.0"/>\n')
        f.write('  <vType id="imprudent" color="0.9,0,0.9" tau="0.7" sigma="0.95" speedFactor="1.4"/>\n')

        for i in range(150):
            src = random.choice(edges)
            dst = random.choice(edges)
            while src == dst:
                dst = random.choice(edges)

            vtype = 'imprudent' if random.random() < 0.3 else 'normal'
            f.write(f'  <trip id="veh_{i}" type="{vtype}" depart="{random.randint(0, 1800)}" from="{src}" to="{dst}"/>\n')

        f.write('</additional>\n')
    print('✅ Archivo generado correctamente.')
    
    # Paso opcional: Lanzar SUMO automáticamente si todo salió bien
    print("\n🚀 Para iniciar la simulación, ejecuta:")
    print(f"sumo-gui -n {base_net} -a {add_file} --start --delay 10")
else:
    print('❌ Error: No se encontraron bordes suficientes para generar tráfico.')