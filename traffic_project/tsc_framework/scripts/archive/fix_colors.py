import xml.etree.ElementTree as ET
import os

def fix_colors(route_file, output_file):
    tree = ET.parse(route_file)
    root = tree.getroot()
    
    count = 0
    # Buscar todos los vType y forzar colores distintos
    for vtype in root.findall('vType'):
        vtype_id = vtype.get('id', '')
        if 'imprudent' in vtype_id:
            # Color VIOLETA NEÓN para imprudentes (muy visible)
            vtype.set('color', '0.5, 0, 1') 
            count += 1
        else:
            # Color AZUL para normales
            if 'normal' in vtype_id or count == 0:
                vtype.set('color', '0, 0.5, 1')

    # Guardar
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"✅ Colores actualizados: {count} tipos imprudentes ahora son VIOLETAS.")
    print(f"📁 Archivo guardado: {output_file}")

# Rutas
input_route = "experiments/hangzhou_robustness/scenarios/hangzhou_quito_imprudent_30pct_dense_FIXED.rou.xml"
output_route = "experiments/hangzhou_robustness/scenarios/hangzhou_quito_imprudent_30pct_dense_COLORED.rou.xml"

if os.path.exists(input_route):
    fix_colors(input_route, output_route)
else:
    print(f"❌ Error: No se encuentra {input_route}")
    # Intentar con el nombre anterior si este falla
    input_route_alt = "experiments/hangzhou_robustness/scenarios/hangzhou_quito_imprudent_30pct_dense.rou.xml"
    if os.path.exists(input_route_alt):
        fix_colors(input_route_alt, output_route)
