import xml.etree.ElementTree as ET
from pathlib import Path

net_file = Path("sumo_configs/networks/hangzhou_4x4.net.xml")
route_file = Path("experiments/hangzhou_robustness/scenarios/hangzhou_quito_imprudent_30pct_dense.rou.xml")
output_route = Path("experiments/hangzhou_robustness/scenarios/hangzhou_quito_imprudent_30pct_dense_FIXED.rou.xml")
output_net = Path("experiments/hangzhou_robustness/scenarios/hangzhou_4x4_fixed.net.xml")

print("Reparando archivos...")

# --- PASO A: Arreglar la RED (Semáforos) ---
try:
    tree_net = ET.parse(net_file)
    root_net = tree_net.getroot()
    
    # Buscar todos los elementos <tlLogic>
    tl_logics = root_net.findall(".//tlLogic")
    if not tl_logics:
        print("ADVERTENCIA: No se encontraron lógicas de semáforo en la red original.")
    else:
        print(f"Encontradas {len(tl_logics)} lógicas de semáforo. Asegurando estado 'on'.")
        for logic in tl_logics:
            # Forzar que el programa esté activo si tiene un atributo de estado
            if logic.get("programID") == "off":
                logic.set("programID", "0") # Cambiar a programa 0 (usualmente el activo)
    
    tree_net.write(output_net, encoding="utf-8", xml_declaration=True)
    print(f"Red reparada guardada en: {output_net}")
except Exception as e:
    print(f"Error al reparar la red: {e}")
    output_net = net_file # Usar la original si falla

# --- PASO B: Arreglar las RUTAS (Colores) ---
try:
    tree_route = ET.parse(route_file)
    root_route = tree_route.getroot()
    
    # Definir colores para los tipos imprudentes (Naranja/Rojo)
    # Buscamos si ya existen vType, si no, los creamos antes del primer vehicle
    existing_vtypes = {vt.get('id'): vt for vt in root_route.findall(".//vType")}
    
    colors_added = 0
    # Iterar sobre todos los vehículos para asegurar que su tipo tenga color
    vehicles = root_route.findall(".//vehicle")
    for veh in vehicles:
        vtype_id = veh.get('type')
        if vtype_id and "imprudent" in vtype_id:
            if vtype_id not in existing_vtypes:
                # Crear el vType faltante con color Naranja
                new_vtype = ET.Element("vType")
                new_vtype.set("id", vtype_id)
                new_vtype.set("color", "1,0.5,0") # Rojo, Verde(0.5), Azul(0) = Naranja fuerte
                new_vtype.set("sigma", "0.8") # Comportamiento más errático visual
                new_vtype.set("tau", "0.6")
                # Insertar al inicio del archivo (después de cualquier comentario o vType existente)
                root_route.insert(0, new_vtype)
                existing_vtypes[vtype_id] = new_vtype
                colors_added += 1
    
    if colors_added > 0:
        print(f"Añadidos {colors_added} tipos de vehículos con color NARANJA.")
    else:
        print("Los tipos de vehículos ya existían o no se detectaron imprudentes.")

    tree_route.write(output_route, encoding="utf-8", xml_declaration=True)
    print(f"Rutas reparadas guardadas en: {output_route}")

except Exception as e:
    print(f"Error al reparar rutas: {e}")
    output_route = route_file

print("\n¡Listo! Usa los archivos '_FIXED' para visualizar.")
