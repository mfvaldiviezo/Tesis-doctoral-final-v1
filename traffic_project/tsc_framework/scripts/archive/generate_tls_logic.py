#!/usr/bin/env python3
"""
Script para generar automaticamente la logica de semaforos 
para la red Hangzhou 4x4 basado en los carriles internos reales.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

def get_internal_lanes(net_file):
    """Extrae todos los carriles internos de la red."""
    tree = ET.parse(net_file)
    root = tree.getroot()
    
    junctions = {}
    for junction in root.findall('.//junction'):
        jid = junction.get('id')
        # Buscar carriles internos que comienzan con :jid_
        internal_lanes = []
        for lane in root.findall('.//lane'):
            lane_id = lane.get('id')
            if lane_id.startswith(f':{jid}_'):
                internal_lanes.append(lane_id)
        
        if internal_lanes:
            junctions[jid] = sorted(internal_lanes)
    
    return junctions

def generate_tl_logic(junctions):
    """Genera logica de semaforos para cada junction."""
    tl_logics = []
    
    for jid, lanes in sorted(junctions.items()):
        n_lanes = len(lanes)
        
        # Determinar tipo de junction
        if n_lanes == 2:
            # Esquina - 2 fases simples
            phases = [
                ('31', 'Gr'),
                ('4', 'yy'),
                ('31', 'rG'),
                ('4', 'ry'),
            ]
        elif n_lanes == 12:
            # Borde - 4 fases para 4-vias
            # Distribuir carriles en 4 direcciones
            state_len = n_lanes
            phases = [
                ('30', 'GGrrrrrrGGrr'),  # Norte-Sur recto
                ('4', 'yyrrrrrryyrr'),
                ('30', 'rrGGGGrrrrrr'),  # Este-Oeste recto
                ('4', 'rryyyyrrrrrr'),
                ('30', 'rrrrrrGGrrrr'),  # Giros Norte-Sur
                ('4', 'rrrrrryyrrrr'),
                ('30', 'rrrrrrrrrrGG'),  # Giros Este-Oeste
                ('4', 'rrrrrrrrrryy'),
            ]
        elif n_lanes == 20:
            # Centro - 6 fases completas
            state_len = n_lanes
            phases = [
                ('30', 'GGrrrrrrrrrrGGrrrrrr'),  # N-S recto
                ('4', 'yyrrrrrrrrrryyrrrrrr'),
                ('30', 'rrGGGGrrrrrrrrrrrrrr'),  # E-W recto
                ('4', 'rryyyyrrrrrrrrrrrrrr'),
                ('30', 'rrrrrrGGrrrrrrrrrrrr'),  # N-S giros
                ('4', 'rrrrrryyrrrrrrrrrrrr'),
                ('30', 'rrrrrrrrrrGGGGrrrrrr'),  # E-W giros
                ('4', 'rrrrrrrrrryyyyrrrrrr'),
                ('30', 'rrrrrrrrrrrrrrGGrrrr'),  # N-S izquierdo
                ('4', 'rrrrrrrrrrrrrryyrrrr'),
                ('30', 'rrrrrrrrrrrrrrrrGGGG'),  # E-W izquierdo
                ('4', 'rrrrrrrrrrrrrrrryyyy'),
            ]
        else:
            print(f'WARNING: Junction {jid} tiene {n_lanes} carriles (no estandar)')
            continue
        
        # Verificar longitud de estados
        for dur, state in phases:
            if len(state) != n_lanes:
                print(f'ERROR: Junction {jid} tiene {n_lanes} carriles pero estado tiene {len(state)} caracteres: {state}')
                return None
        
        tl_logics.append((jid, phases))
    
    return tl_logics

def write_additional_file(tl_logics, output_file):
    """Escribe el archivo additional.xml."""
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
    <!-- Logica de semaforos generada automaticamente para Hangzhou 4x4 -->
    <!-- Tesis Doctoral TSC Framework -->
    
'''
    
    for jid, phases in tl_logics:
        xml_content += f'    <tlLogic id="{jid}" type="static" programID="actuated" offset="0">\n'
        for duration, state in phases:
            xml_content += f'        <phase duration="{duration}" state="{state}"/>\n'
        xml_content += '    </tlLogic>\n    \n'
    
    xml_content += '</additional>\n'
    
    with open(output_file, 'w') as f:
        f.write(xml_content)
    
    print(f'Archivo guardado: {output_file}')

def main():
    base_dir = Path(__file__).parent.parent  # tsc_framework, no scripts
    net_file = base_dir / 'sumo_configs' / 'networks' / 'hangzhou_4x4.net.xml'
    output_file = base_dir / 'sumo_configs' / 'hangzhou_additional.xml'
    
    print('=== GENERANDO LOGICA DE SEMAFOROS PARA HANGZHOU ===\n')
    
    # Extraer carriles internos
    print('1. Leyendo red...')
    junctions = get_internal_lanes(net_file)
    print(f'   Encontrados {len(junctions)} junctions con carriles internos\n')
    
    # Mostrar resumen
    print('2. Resumen de junctions:')
    for jid, lanes in sorted(junctions.items()):
        print(f'   {jid}: {len(lanes)} carriles')
    print()
    
    # Generar logica
    print('3. Generando logica de semaforos...')
    tl_logics = generate_tl_logic(junctions)
    
    if tl_logics is None:
        print('ERROR: No se pudo generar la logica')
        return 1
    
    print(f'   Generados {len(tl_logics)} semaforos\n')
    
    # Escribir archivo
    print('4. Guardando archivo additional.xml...')
    write_additional_file(tl_logics, output_file)
    
    print('\n=== EXITO ===')
    print(f'El archivo {output_file} esta listo para usar.')
    print('\nComando para prueba visual:')
    print('  sumo-gui -c sumo_configs/hangzhou.sumocfg')
    
    return 0

if __name__ == '__main__':
    exit(main())
