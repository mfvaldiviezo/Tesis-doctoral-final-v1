import xml.etree.ElementTree as ET
import random

random.seed(42)
net_file = 'experiments/hangzhou_robustness/scenarios/test_grid.net.xml'
output_add = 'experiments/hangzhou_robustness/scenarios/imprudent_scenario_fixed.add.xml'

# Leer la red para obtener bordes válidos
from sumolib import net
try:
    n = net.readNet(net_file)
    edges = [e.getID() for e in n.getEdges()]
    print(f"Red cargada: {len(edges)} bordes encontrados.")
except Exception as e:
    print(f"Error leyendo red: {e}")
    edges = [f"edge_{i}" for i in range(9)]

with open(output_add, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<additional xmlns="http://sumo.dlr.de">\n')
    
    # 1. Tipos de vehículos (Normales vs Imprudentes)
    # Normal: sigma bajo (0.5), tau normal (1.0)
    f.write('  <vType id="normal" sigma="0.5" tau="1.0" speedFactor="1.0" accel="2.6" decel="4.5" color="0,0.5,1"/>\n')
    # Imprudente: sigma alto (0.9 = muy nervioso), tau bajo (0.6), speedFactor alto
    # NOTA: sigma debe estar entre 0 y 1. Usamos 0.9 que es el máximo permitido.
    f.write('  <vType id="imprudent" sigma="0.9" tau="0.6" speedFactor="1.3" accel="3.5" decel="6.0" color="0.8,0,0.8"/>\n')
    
    # 2. Generar 300 viajes (Trips)
    # SUMO calculará la ruta automáticamente al iniciar
    num_vehicles = 300
    imprudent_ratio = 0.3
    
    for i in range(num_vehicles):
        is_imprudent = (i < int(num_vehicles * imprudent_ratio))
        v_type = "imprudent" if is_imprudent else "normal"
        
        depart = random.randint(0, 3500)
        from_edge = random.choice(edges)
        to_edge = random.choice(edges)
        
        # Asegurar que origen y destino sean diferentes
        while to_edge == from_edge:
            to_edge = random.choice(edges)
            
        f.write(f'  <trip id="veh_{i}" type="{v_type}" depart="{depart}" from="{from_edge}" to="{to_edge}"/>\n')
    
    f.write('</additional>\n')

print(f"✅ Archivo generado: {output_add}")
print(f"   - Total vehículos: {num_vehicles}")
print(f"   - Imprudentes (Violeta): {int(num_vehicles * imprudent_ratio)}")
print(f"   - Normales (Azul): {num_vehicles - int(num_vehicles * imprudent_ratio)}")
print("\n🚀 Ejecutando simulación...")
