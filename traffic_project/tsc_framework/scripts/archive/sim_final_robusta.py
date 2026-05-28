import os
import random
import subprocess
import xml.etree.ElementTree as ET
import re

random.seed(42)

# Rutas
NET_FILE = "experiments/hangzhou_robustness/scenarios/base_grid.net.xml"
TRIPS_FILE = "experiments/hangzhou_robustness/scenarios/final_trips.xml"
ROUTES_FILE = "experiments/hangzhou_robustness/scenarios/final_routes.rou.xml"
ADD_FILE = "experiments/hangzhou_robustness/scenarios/final_types.add.xml"
SUMO_GUI_CMD = "sumo-gui"

def get_edges_from_netxml(net_path):
    """Extrae IDs de bordes válidos leyendo el XML directamente (sin sumolib)."""
    edges = []
    try:
        tree = ET.parse(net_path)
        root = tree.getroot()
        # Buscar todos los elementos 'edge'
        for elem in root.iter('edge'):
            eid = elem.get('id')
            if eid and not eid.startswith(':'): # Ignorar bordes internos de intersecciones
                # Filtrar solo bordes de carriles (suelen tener sufijo _0, _1, etc.)
                if '_' in eid:
                    edges.append(eid)
        
        # Eliminar duplicados si los hubiera
        edges = list(set(edges))
        print(f"✅ Encontrados {len(edges)} bordes válidos en la red.")
        return edges
    except Exception as e:
        print(f"❌ Error leyendo XML: {e}")
        return []

def generate_trips(edges, output_path):
    """Genera archivo de viajes (.trips.xml)."""
    if len(edges) < 2:
        return False
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<routes xmlns="http://sumo.dlr.de">\n')
        
        count = 0
        for i in range(200): # 200 vehículos
            src = random.choice(edges)
            dst = random.choice(edges)
            attempts = 0
            while src == dst and attempts < 10:
                dst = random.choice(edges)
                attempts += 1
            
            if src != dst:
                depart = random.randint(0, 3500)
                f.write(f'  <trip id="trip_{i}" depart="{depart}" from="{src}" to="{dst}"/>\n')
                count += 1
        
        f.write('</routes>\n')
    
    print(f"📝 Generados {count} viajes en {output_path}")
    return True

def run_duarouter(net_path, trips_path, routes_path):
    """Ejecuta duarouter para convertir viajes en rutas."""
    cmd = [
        "duarouter",
        "--net-file", net_path,
        "--route-files", trips_path, # Usamos route-files para leer trips también
        "--output-file", routes_path,
        "--ignore-errors",
        "--begin", "0",
        "--end", "3600"
    ]
    
    print("🔄 Calculando rutas con duarouter...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stderr:
            # Imprimir warnings pero no fallar si hay rutas generadas
            for line in result.stderr.split('\n'):
                if "Warning" in line:
                    print(f"   ⚠️ {line}")
        print("✅ Rutas calculadas exitosamente.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en duarouter: {e}")
        print(f"   Detalle: {e.stderr}")
        return False

def create_vehicle_types(output_path):
    """Crea archivo adicional con tipos de vehículos (colores y comportamiento)."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<additional>\n')
        # Normal: Azul, comportamiento estándar
        f.write('  <vType id="normal" color="0,0.5,1" tau="1.0" sigma="0.5" speedFactor="1.0" />\n')
        # Imprudente: Violeta, más rápido y agresivo (sigma alto, tau bajo)
        # Ajustamos tau >= 0.7 para evitar warning crítico, pero mantenemos sigma alto
        f.write('  <vType id="imprudent" color="0.9,0,0.9" tau="0.7" sigma="0.9" speedFactor="1.3" />\n')
        f.write('</additional>\n')
    print(f"🎨 Tipos de vehículos guardados en {output_path}")

def inject_imprudent_behavior(routes_in, routes_out, add_file):
    """
    Lee las rutas generadas, asigna aleatoriamente tipo 'imprudent' al 30% 
    y crea un archivo final combinado con los tipos.
    """
    try:
        tree = ET.parse(routes_in)
        root = tree.getroot()
        
        # Añadir definiciones de tipos al inicio
        # Creamos un nuevo elemento routes si no existe, pero duarouter ya lo crea
        # Insertamos los vType antes del primer vehicle/route
        
        # Leer contenido de vTypes
        vtypes_xml = ""
        with open(add_file, 'r') as f:
            content = f.read()
            # Extraer solo los vType
            match = re.search(r'<additional>(.*)</additional>', content, re.DOTALL)
            if match:
                vtypes_xml = match.group(1)
        
        # Insertar vTypes en el root del archivo de rutas
        # Nota: duarouter genera <routes>...</routes>
        # Insertamos los vType como hijos directos de routes
        if vtypes_xml:
            # Parsear temporalmente para insertar nodos
            temp_root = ET.fromstring(f"<root>{vtypes_xml}</root>")
            for child in temp_root:
                root.insert(0, child) # Insertar al principio
        
        # Asignar tipos a los vehículos/trips
        # duarouter genera <vehicle> o mantiene <trip>? Generalmente genera <route> y <vehicle>
        # Si genera <vehicle>, les asignamos type.
        
        vehicles = root.findall('vehicle')
        if not vehicles:
            # Si no hay vehículos explícitos (solo rutas), buscamos trips originales?
            # duarouter suele expandir trips a vehicles con routedefs
            # Si el archivo tiene <trip>, los convertimos a <vehicle> con type
            trips = root.findall('trip')
            if trips:
                print(f"   Convirtiendo {len(trips)} trips a vehículos con tipos...")
                for i, trip in enumerate(trips):
                    is_imprudent = random.random() < 0.3
                    v_type = "imprudent" if is_imprudent else "normal"
                    
                    # Crear vehículo explícito
                    veh = ET.SubElement(root, 'vehicle')
                    veh.set('id', trip.get('id'))
                    veh.set('type', v_type)
                    veh.set('depart', trip.get('depart'))
                    veh.set('route', f"route_{i}") # Necesitamos asegurar que la ruta exista
                    
                    # Eliminar el trip original para evitar duplicados si SUMO lo interpreta mal
                    # Pero mejor: duarouter ya debió crear las rutas. 
                    # Estrategia alternativa: Modificar el trips.xml original antes de duarouter?
                    # No, duarouter no soporta type en trips fácilmente sin vType definido en net.
                    pass
                # Esta parte es compleja sin ver el XML exacto de duarouter.
                # Simplificación: Asumimos que duarouter genera <vehicle> con routeId.
        
        # Re-enfoque simple: 
        # 1. duarouter genera rutas perfectas.
        # 2. Leemos ese archivo.
        # 3. Buscamos todos los <vehicle> o <trip> y les ponemos type="..." aleatorio.
        
        count_imprudent = 0
        # Buscar elementos que representen vehículos (pueden ser 'vehicle' o 'trip' si no se expandieron)
        elements = root.findall('vehicle') 
        if not elements:
             elements = root.findall('trip')
        
        for elem in elements:
            if random.random() < 0.3:
                elem.set('type', 'imprudent')
                count_imprudent += 1
            else:
                elem.set('type', 'normal')
        
        print(f"   🎲 Asignados {count_imprudent} vehículos imprudentes ({len(elements)} total).")
        
        tree.write(routes_out, encoding="UTF-8", xml_declaration=True)
        print(f"✅ Escenario final guardado en {routes_out}")
        return True
        
    except Exception as e:
        print(f"❌ Error procesando rutas: {e}")
        return False

def main():
    print("🚀 Iniciando generación de simulación robusta...")
    
    # 1. Obtener bordes
    edges = get_edges_from_netxml(NET_FILE)
    if not edges:
        return

    # 2. Generar Trips
    if not generate_trips(edges, TRIPS_FILE):
        return

    # 3. Calcular Rutas (Importante: duarouter necesita que los trips sean válidos)
    if not run_duarouter(NET_FILE, TRIPS_FILE, ROUTES_FILE):
        print("⚠️ duarouter falló o no generó rutas. Verifica los IDs de bordes.")
        # Fallback: intentar usar el trips directo si duarouter falla por alguna razón menor
        # Pero mejor detenerse aquí para debug.
        return

    # 4. Crear Tipos
    create_vehicle_types(ADD_FILE)

    # 5. Inyectar Comportamiento (Asignar tipos a vehículos)
    FINAL_ROUTES = "experiments/hangzhou_robustness/scenarios/final_scenario.rou.xml"
    if not inject_imprudent_behavior(ROUTES_FILE, FINAL_ROUTES, ADD_FILE):
        return

    # 6. Lanzar SUMO
    print("\n🚀 LANZANDO SUMO-GUI...")
    print("   - Violeta: Conductores Imprudentes")
    print("   - Azul: Conductores Normales")
    print("   - Presiona 'L' si no ves los semáforos.")
    
    subprocess.run([
        SUMO_GUI_CMD,
        "-n", NET_FILE,
        "-r", FINAL_ROUTES,
        "--start",
        "--delay", "20",
        "--end", "3600"
    ])

if __name__ == "__main__":
    main()