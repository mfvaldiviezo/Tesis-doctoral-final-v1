#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para inyectar vehículos con comportamiento imprudente (Quito) 
en la red de tráfico de Hangzhou.

Este script mezcla vehículos normales con vehículos imprudentes generados
a partir de datos reales de Quito, permitiendo evaluar la robustez de 
agentes de RL frente a comportamientos de conducción latinoamericanos.
"""

import argparse
import json
import logging
import os
import random
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parsear argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Inyectar vehículos imprudentes en una red SUMO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplo de uso:
  python inject_imprudent_traffic.py \\
    --net-file sumo_configs/hangzhou/hangzhou.net.xml \\
    --route-file sumo_configs/hangzhou/hangzhou.rou.xml \\
    --imprudent-file results/quito_scenarios/imprudent_drivers.rou.xml \\
    --output-dir experiments/hangzhou_robustness/scenarios \\
    --mix-ratio 0.3 \\
    --scenario-name imprudent_30pct
        """
    )
    
    parser.add_argument(
        '--net-file',
        type=str,
        required=True,
        help='Ruta al archivo .net.xml de la red SUMO'
    )
    
    parser.add_argument(
        '--route-file',
        type=str,
        required=True,
        help='Ruta al archivo .rou.xml con rutas originales'
    )
    
    parser.add_argument(
        '--imprudent-file',
        type=str,
        required=True,
        help='Ruta al archivo .rou.xml con vehículos imprudentes'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Directorio de salida para los escenarios generados'
    )
    
    parser.add_argument(
        '--mix-ratio',
        type=float,
        default=0.3,
        help='Proporción de vehículos imprudentes (0.0 a 1.0). Default: 0.3'
    )
    
    parser.add_argument(
        '--scenario-name',
        type=str,
        default='imprudent_mixed',
        help='Nombre del escenario generado. Default: imprudent_mixed'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Semilla aleatoria para reproducibilidad. Default: 42'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Activar logging detallado'
    )
    
    return parser.parse_args()


def load_vehicle_types(imprudent_file: str) -> Dict[str, Dict]:
    """
    Cargar los tipos de vehículos imprudentes desde el archivo .rou.xml.
    
    Returns:
        Diccionario con los tipos de vehículos y sus parámetros
    """
    logger.info(f"Cargando tipos de vehículos imprudentes desde {imprudent_file}")
    
    vehicle_types = {}
    tree = ET.parse(imprudent_file)
    root = tree.getroot()
    
    for vtype in root.findall('vType'):
        vtype_id = vtype.get('id')
        if vtype_id:
            vehicle_types[vtype_id] = {
                'accel': float(vtype.get('accel', 2.6)),
                'decel': float(vtype.get('decel', 4.5)),
                'sigma': float(vtype.get('sigma', 0.5)),
                'tau': float(vtype.get('tau', 0.6)),
                'speedFactor': float(vtype.get('speedFactor', 1.0)),
                'speedDev': float(vtype.get('speedDev', 0.1)),
                'impatience': float(vtype.get('impatience', 0)),
                'laneChangeModel': vtype.get('laneChangeModel', 'LC2013'),
            }
    
    logger.info(f"Encontrados {len(vehicle_types)} tipos de vehículos imprudentes")
    return vehicle_types


def load_original_routes(route_file: str) -> Tuple[List[ET.Element], Dict[str, ET.Element]]:
    """
    Cargar las rutas originales y sus definiciones de vehículos.
    
    Returns:
        Tupla con (lista de rutas, diccionario de tipos de vehículos)
    """
    logger.info(f"Cargando rutas originales desde {route_file}")
    
    tree = ET.parse(route_file)
    root = tree.getroot()
    
    routes = []
    vehicle_types = {}
    
    # Extraer tipos de vehículos originales
    for vtype in root.findall('vType'):
        vtype_id = vtype.get('id')
        if vtype_id:
            vehicle_types[vtype_id] = vtype
    
    # Extraer rutas/viajes
    for element in root:
        if element.tag in ['route', 'trip', 'vehicle']:
            routes.append(element)
    
    logger.info(f"Encontradas {len(routes)} rutas y {len(vehicle_types)} tipos de vehículos originales")
    return routes, vehicle_types


def create_mixed_scenario(
    original_routes: List[ET.Element],
    original_vtypes: Dict[str, ET.Element],
    imprudent_vtypes: Dict[str, Dict],
    mix_ratio: float,
    seed: int,
    scenario_name: str
) -> ET.Element:
    """
    Crear un escenario mezclado con vehículos normales e imprudentes.
    
    Args:
        original_routes: Lista de elementos de rutas originales
        original_vtypes: Diccionario de tipos de vehículos originales
        imprudent_vtypes: Diccionario de parámetros de vehículos imprudentes
        mix_ratio: Proporción de vehículos imprudentes
        seed: Semilla aleatoria
        scenario_name: Nombre del escenario
        
    Returns:
        Elemento XML raíz del nuevo escenario
    """
    random.seed(seed)
    
    # Crear elemento raíz
    root = ET.Element('routes')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    
    # Añadir tipos de vehículos originales
    for vtype_id, vtype_elem in original_vtypes.items():
        root.append(vtype_elem)
    
    # Añadir tipos de vehículos imprudentes
    stress_levels = ['nominal', 'moderate', 'extreme']
    for idx, (vtype_id, params) in enumerate(imprudent_vtypes.items()):
        # Si el ID ya existe, añadir sufijo
        if vtype_id in original_vtypes:
            vtype_id = f"{vtype_id}_imprudent"
        
        vtype_elem = ET.SubElement(root, 'vType')
        vtype_elem.set('id', vtype_id)
        
        # Copiar parámetros del vehículo imprudente
        for param, value in params.items():
            if isinstance(value, str):
                vtype_elem.set(param, value)
            else:
                vtype_elem.set(param, f"{value:.4f}")
    
    # Procesar rutas y asignar tipos de vehículos
    vehicle_count = 0
    imprudent_count = 0
    
    for route_elem in original_routes:
        new_route = ET.SubElement(root, route_elem.tag)
        
        # Copiar atributos de la ruta
        for attr, value in route_elem.attrib.items():
            new_route.set(attr, value)
        
        # Si es un vehículo, decidir si hacerlo imprudente
        if route_elem.tag == 'vehicle':
            vehicle_count += 1
            
            # Determinar si este vehículo será imprudente
            is_imprudent = random.random() < mix_ratio
            
            if is_imprudent:
                imprudent_count += 1
                # Seleccionar un tipo de vehículo imprudente aleatorio
                imprudent_ids = list(imprudent_vtypes.keys())
                selected_vtype = random.choice(imprudent_ids)
                
                # Si hubo conflicto de nombres, usar el sufijo
                if selected_vtype in original_vtypes:
                    selected_vtype = f"{selected_vtype}_imprudent"
                
                # Actualizar o añadir el atributo type
                if 'type' in new_route.attrib:
                    new_route.set('type', selected_vtype)
                else:
                    new_route.set('type', selected_vtype)
                
                # Añadir variabilidad adicional en parámetros de conducción
                # Esto simula la impredecibilidad de conductores imprudentes
                if 'speedFactor' not in new_route.attrib:
                    speed_factor = float(new_route.get('speedFactor', 1.0)) if 'speedFactor' in [a for a in route_elem.attrib] else 1.0
                    # Conductores imprudentes tienden a exceder límites de velocidad
                    new_speed_factor = min(1.8, max(1.1, speed_factor + random.uniform(0.2, 0.5)))
                    new_route.set('speedFactor', f"{new_speed_factor:.3f}")
                
                if 'sigma' not in new_route.attrib:
                    # Mayor variabilidad en aceleración/desaceleración
                    new_route.set('sigma', f"{random.uniform(0.3, 0.7):.3f}")
        
        # Copiar elementos hijos (rutas definidas explícitamente)
        for child in route_elem:
            new_child = ET.SubElement(new_route, child.tag)
            for attr, value in child.attrib.items():
                new_child.set(attr, value)
    
    logger.info(f"Vehículos totales: {vehicle_count}, Imprudentes: {imprudent_count} ({imprudent_count/vehicle_count*100:.1f}%)")
    
    return root


def save_scenario(root: ET.Element, output_path: str) -> None:
    """Guardar el escenario en un archivo XML."""
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Escribir archivo XML con formato bonito
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!-- Escenario generado con inyección de tráfico imprudente -->\n')
        f.write(f'<!-- Fecha: {datetime.now().isoformat()} -->\n')
        tree.write(f, encoding='unicode')
    
    logger.info(f"Escenario guardado en {output_path}")


def generate_summary(
    output_dir: str,
    scenario_name: str,
    mix_ratio: float,
    total_vehicles: int,
    imprudent_vehicles: int,
    config: Dict
) -> None:
    """Generar un archivo JSON con el resumen del escenario."""
    summary = {
        'scenario_name': scenario_name,
        'generation_timestamp': datetime.now().isoformat(),
        'configuration': {
            'mix_ratio': mix_ratio,
            'seed': config.get('seed', 42),
            'net_file': config.get('net_file', ''),
            'route_file': config.get('route_file', ''),
            'imprudent_file': config.get('imprudent_file', ''),
        },
        'statistics': {
            'total_vehicles': total_vehicles,
            'imprudent_vehicles': imprudent_vehicles,
            'normal_vehicles': total_vehicles - imprudent_vehicles,
            'imprudent_percentage': (imprudent_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        },
        'description': (
            f"Escenario con {mix_ratio*100:.0f}% de vehículos con comportamiento imprudente "
            "basado en datos reales de Quito, Ecuador."
        )
    }
    
    summary_path = os.path.join(output_dir, f'{scenario_name}_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Resumen guardado en {summary_path}")


def main():
    """Función principal."""
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validar archivos de entrada
    for file_path, desc in [
        (args.net_file, 'archivo de red'),
        (args.route_file, 'archivo de rutas'),
        (args.imprudent_file, 'archivo de vehículos imprudentes')
    ]:
        if not os.path.exists(file_path):
            logger.error(f"No se encontró el {desc}: {file_path}")
            return 1
    
    # Crear directorio de salida
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("INYECCIÓN DE TRÁFICO IMPRUDENTE EN RED HANGZHOU")
    logger.info("=" * 70)
    logger.info(f"Red: {args.net_file}")
    logger.info(f"Rutas originales: {args.route_file}")
    logger.info(f"Vehículos imprudentes: {args.imprudent_file}")
    logger.info(f"Proporción de imprudentes: {args.mix_ratio*100:.0f}%")
    logger.info(f"Semilla: {args.seed}")
    logger.info("=" * 70)
    
    # Cargar datos
    imprudent_vtypes = load_vehicle_types(args.imprudent_file)
    original_routes, original_vtypes = load_original_routes(args.route_file)
    
    # Crear escenario mezclado
    mixed_root = create_mixed_scenario(
        original_routes=original_routes,
        original_vtypes=original_vtypes,
        imprudent_vtypes=imprudent_vtypes,
        mix_ratio=args.mix_ratio,
        seed=args.seed,
        scenario_name=args.scenario_name
    )
    
    # Guardar escenario
    output_file = os.path.join(
        args.output_dir, 
        f'hangzhou_{args.scenario_name}.rou.xml'
    )
    save_scenario(mixed_root, output_file)
    
    # Contar vehículos para el resumen
    total_vehicles = sum(1 for elem in original_routes if elem.tag == 'vehicle')
    imprudent_vehicles = int(total_vehicles * args.mix_ratio)
    
    # Generar resumen
    generate_summary(
        output_dir=args.output_dir,
        scenario_name=args.scenario_name,
        mix_ratio=args.mix_ratio,
        total_vehicles=total_vehicles,
        imprudent_vehicles=imprudent_vehicles,
        config={
            'seed': args.seed,
            'net_file': args.net_file,
            'route_file': args.route_file,
            'imprudent_file': args.imprudent_file,
        }
    )
    
    logger.info("=" * 70)
    logger.info("INYECCIÓN COMPLETADA EXITOSAMENTE")
    logger.info("=" * 70)
    logger.info(f"Archivo de salida: {output_file}")
    logger.info(f"Total vehículos: {total_vehicles}")
    logger.info(f"Vehículos imprudentes: {imprudent_vehicles} ({args.mix_ratio*100:.0f}%)")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    exit(main())
