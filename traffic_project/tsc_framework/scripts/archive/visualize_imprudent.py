#!/usr/bin/env python3
"""
Script para visualización de conductores imprudentes en SUMO-GUI.
Referencia: Tesis Doctoral - Comportamiento de conductores latinoamericanos
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Ruta al proyecto
    project_root = Path(__file__).parent.parent
    
    # Archivos requeridos
    net_file = project_root / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
    route_file = project_root / "results" / "quito_scenarios" / "imprudent_drivers.rou.xml"
    sumo_cfg = project_root / "sumo_configs" / "test_visual.sumocfg"
    
    # Verificar existencia
    if not net_file.exists():
        print(f"❌ Red no encontrada: {net_file}")
        print("💡 Ejecuta: python scripts/prepare_network.py --mode benchmark")
        sys.exit(1)
    
    if not route_file.exists():
        print(f"❌ Rutas no generadas: {route_file}")
        print("💡 Ejecuta primero: python scripts/generate_imprudent_drivers_simple.py")
        print("   con --data-path data/quito_behavior/micro_behavior_expanded.csv")
        sys.exit(1)
    
    # Crear configuración temporal
    config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumo_config.xsd">
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
        <waiting-time-memory value="1000"/>
    </processing>
    <report>
        <no-warnings value="true"/>
        <no-step-log value="false"/>
    </report>
    <gui_only>
        <start value="true"/>
        <game-mode value="false"/>
        <tracker-interval value="1"/>
    </gui_only>
    <view>
        <view zoom="400" x="0" y="0"/>
    </view>
</configuration>
"""
    
    with open(sumo_cfg, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    # Imprimir información
    print("=" * 70)
    print("🚦 SIMULACIÓN VISUAL DE CONDUCTORES IMPRUDENTES - QUITO")
    print("   Referencia: Tesis Doctoral - IA para Tráfico Latinoamericano")
    print("=" * 70)
    print()
    print("📊 CONFIGURACIÓN:")
    print(f"   📍 Red:           {net_file.name}")
    print(f"   🚗 Rutas:         {route_file.name}")
    print(f"   ⏱️  Duración:      3600 segundos (1 hora simulada)")
    print(f"   🎮 GUI:           Habilitada")
    print()
    print("=" * 70)
    print("🎨 LEYENDA DE COLORES DE VEHÍCULOS:")
    print("=" * 70)
    print("   🔴 ROJO/NARANJA   : Conductores IMPRUDENTES (agresivos)")
    print("      - sigma bajo   : Conducción errática")
    print("      - tau bajo     : Poco tiempo de reacción")
    print("      - speedFactor>1: Exceden límite de velocidad")
    print()
    print("   🟡 AMARILLO/VERDE : Conductores NORMALES")
    print("      - sigma medio  : Variabilidad moderada")
    print("      - comportamiento típico urbano")
    print()
    print("   🟢 VERDE CLARO    : Conductores CONSERVADORES")
    print("      - sigma alto   : Conducción suave, predecible")
    print("      - tau alto     : Mayor tiempo de reacción")
    print("      - speedFactor≈1: Respetan límites")
    print()
    print("=" * 70)
    print("💡 CONTROLES DE SUMO-GUI:")
    print("=" * 70)
    print("   🖱️  Click derecho   : Cambiar tipo de vista")
    print("   🖱️  Rueda ratón     : Zoom in/out")
    print("   ⌨️  Barra espaciadora: Pausar/Continuar simulación")
    print("   ⌨️  Ctrl + T        : Mostrar/Ocultar semáforos")
    print("   ⌨️  Ctrl + V        : Mostrar/Ocultar vehículos")
    print("   ⌨️  Ctrl + I        : Mostrar información de vehículo")
    print("   ⌨️  F5              : Recargar vista")
    print("   ⌨️  Esc             : Salir")
    print()
    print("=" * 70)
    print("🔬 QUÉ OBSERVAR DURANTE LA SIMULACIÓN:")
    print("=" * 70)
    print("   1. Formación de colas por frenazos bruscos")
    print("   2. Efecto 'accordión' en el tráfico")
    print("   3. Conflictos en intersecciones")
    print("   4. Diferencias en tiempo de viaje entre conductores")
    print("   5. Cómo responden los semáforos al tráfico impredecible")
    print()
    print("=" * 70)
    print("📊 DATASET DE REFERENCIA:")
    print("=" * 70)
    print("   - Datos reales de Quito, Ecuador")
    print("   - 20 perfiles de conductores identificados")
    print("   - 3 niveles de estrés: nominal, moderate, extreme")
    print("   - Condiciones: lluvia, hora pico, temporada seca")
    print()
    print("=" * 70)
    print("🚀 INICIANDO SUMO-GUI...")
    print("=" * 70)
    print()
    
    # Lanzar SUMO-GUI
    try:
        # Intentar diferentes comandos según el sistema operativo
        if os.name == 'nt':  # Windows
            subprocess.run(["sumo-gui", "-c", str(sumo_cfg)], check=True)
        else:  # Linux/Mac
            subprocess.run(["sumo-gui", "-c", str(sumo_cfg)], check=True)
    except FileNotFoundError:
        print("❌ ERROR: sumo-gui no encontrado en el PATH")
        print()
        print("💡 SOLUCIÓN:")
        if os.name == 'nt':
            print("   1. Verifica que SUMO esté instalado en:")
            print("      C:\\Program Files (x86)\\Eclipse\\Sumo")
            print("   2. Agrega SUMO al PATH:")
            print('      $env:Path += ";C:\\Program Files (x86)\\Eclipse\\Sumo\\bin"')
            print("   3. Reinicia PowerShell e intenta nuevamente")
        else:
            print("   Instala SUMO: sudo apt install sumo sumo-gui")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("✅ Simulación finalizada por el usuario")
        print("   Los resultados se guardaron en:", sumo_cfg.parent)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
