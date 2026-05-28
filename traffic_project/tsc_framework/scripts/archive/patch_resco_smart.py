import xml.etree.ElementTree as ET
import yaml
import sys
import os

net_file = "tsc_framework/sumo_configs/networks/hangzhou_4x4.net.xml"
signal_file = "baselines/RESCO/resco_benchmark/config/signal.yaml"

tree = ET.parse(net_file)
root = tree.getroot()

edges = {}
for edge in root.findall('edge'):
    if 'from' in edge.attrib and 'to' in edge.attrib:
        edges[edge.attrib['id']] = {
            'from': edge.attrib['from'],
            'to': edge.attrib['to']
        }

def get_node_coords(node_id):
    if not node_id or len(node_id) != 2:
        return 0, 0
    x_map = {'A': 0, 'B': 500, 'C': 1000, 'D': 1500}
    y_map = {'0': 0, '1': 500, '2': 1000, '3': 1500}
    return x_map.get(node_id[0], 0), y_map.get(node_id[1], 0)

# Build hangzhou config
keep = ["A1", "A2", "B0", "B1", "B2", "B3", "C0", "C1", "C2", "C3", "D1", "D2"]

hangzhou = {
    'phase_pairs': [ ['S-S', 'N-N'], ['S-E', 'N-W'], ['S-S', 'S-E'], ['N-N', 'N-W'], ['W-W', 'E-E'], ['W-S', 'E-N'], ['E-E', 'E-N'], ['W-W', 'W-S'] ],
    'pair_to_act_map': None
}

for node in keep:
    node_x, node_y = get_node_coords(node)
    
    # Find incoming edges to this node
    incoming = {'N': None, 'S': None, 'E': None, 'W': None}
    
    for edge_id, edge_data in edges.items():
        if edge_data['to'] == node:
            from_node = edge_data['from']
            fx, fy = get_node_coords(from_node)
            if fy > node_y: incoming['N'] = edge_id
            elif fy < node_y: incoming['S'] = edge_id
            elif fx > node_x: incoming['E'] = edge_id
            elif fx < node_x: incoming['W'] = edge_id

    # Find outgoing edges from this node to set downstream
    downstream = {'N': None, 'S': None, 'E': None, 'W': None}
    for edge_id, edge_data in edges.items():
        if edge_data['from'] == node:
            to_node = edge_data['to']
            if to_node in keep:
                tx, ty = get_node_coords(to_node)
                if ty > node_y: downstream['N'] = to_node
                elif ty < node_y: downstream['S'] = to_node
                elif tx > node_x: downstream['E'] = to_node
                elif tx < node_x: downstream['W'] = to_node

    def get_lanes(direction):
        edge = incoming[direction]
        return [f"{edge}_0"] if edge else []

    lane_sets = {
        'S-W': get_lanes('N'), 'S-S': get_lanes('N'), 'S-E': get_lanes('N'),
        'W-N': get_lanes('E'), 'W-W': get_lanes('E'), 'W-S': get_lanes('E'),
        'N-E': get_lanes('S'), 'N-N': get_lanes('S'), 'N-W': get_lanes('S'),
        'E-S': get_lanes('W'), 'E-E': get_lanes('W'), 'E-N': get_lanes('W')
    }
    
    hangzhou[node] = {
        'lane_sets': lane_sets,
        'downstream': downstream,
        'fixed_timings': [ 4, 2, 4, 2, 4, 2, 4, 2 ],
        'fixed_phase_order_idx': 0
    }

hangzhou['management'] = {
    'bot_left_mgr': [n for n in ['B0', 'B1', 'A1'] if n in keep],
    'bot_right_mgr': [n for n in ['C0', 'D1', 'C1'] if n in keep],
    'top_right_mgr': [n for n in ['C2', 'D2', 'C3'] if n in keep],
    'top_left_mgr': [n for n in ['A2', 'B2', 'B3'] if n in keep]
}

hangzhou['management_neighbors'] = {
    'bot_left_mgr': ['bot_right_mgr', 'top_left_mgr'],
    'bot_right_mgr': ['bot_left_mgr', 'top_right_mgr'],
    'top_right_mgr': ['bot_right_mgr', 'top_left_mgr'],
    'top_left_mgr': ['top_right_mgr', 'bot_left_mgr']
}

import json

# Dump to string using json (since quik_config parses python/json-like syntax better)
json_str = json.dumps(hangzhou, indent=2)
# Replace top level braces so we just get the inner content or just assign it directly
final_str = f"\n'hangzhou': {json_str}\n"

# Clean previous hangzhou block if it exists
with open(signal_file, "r") as f:
    content = f.read()

if "'hangzhou':" in content:
    # Just remove the block that was added
    content = content.split("'hangzhou':")[0].strip()
    with open(signal_file, "w") as f:
        f.write(content)

# Append new clean block
with open(signal_file, "a") as f:
    f.write(final_str)

print("✅ Generado bloque Hangzhou perfecto e inyectado en signal.yaml")
