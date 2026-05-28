hangzhou_block = """
'hangzhou': {
  'phase_pairs': [ ['S-S', 'N-N'], ['S-E', 'N-W'], ['S-S', 'S-E'], ['N-N', 'N-W'], ['W-W', 'E-E'], ['W-S', 'E-N'], ['E-E', 'E-N'], ['W-W', 'W-S'] ],
  'pair_to_act_map': null,
  'A1': {
    'lane_sets': { 'S-W': [ 'A2A1_0' ], 'S-S': [ 'A2A1_0' ], 'S-E': [ 'A2A1_0' ], 'W-N': [ 'B1A1_0' ], 'W-W': [ 'B1A1_0' ], 'W-S': [ 'B1A1_0' ], 'N-E': [ 'A0A1_0' ], 'N-N': [ 'A0A1_0' ], 'N-W': [ 'A0A1_0' ], 'E-S': [ 'left1A1_0' ], 'E-E': [ 'left1A1_0' ], 'E-N': [ 'left1A1_0' ] },
    'downstream': { 'N': 'A2', 'E': 'B1', 'S': null, 'W': null },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'A2': {
    'lane_sets': { 'S-W': [ 'A3A2_0' ], 'S-S': [ 'A3A2_0' ], 'S-E': [ 'A3A2_0' ], 'W-N': [ 'B2A2_0' ], 'W-W': [ 'B2A2_0' ], 'W-S': [ 'B2A2_0' ], 'N-E': [ 'A1A2_0' ], 'N-N': [ 'A1A2_0' ], 'N-W': [ 'A1A2_0' ], 'E-S': [ 'left2A2_0' ], 'E-E': [ 'left2A2_0' ], 'E-N': [ 'left2A2_0' ] },
    'downstream': { 'N': null, 'E': 'B2', 'S': 'A1', 'W': null },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'B0': {
    'lane_sets': { 'S-W': [ 'B1B0_0' ], 'S-S': [ 'B1B0_0' ], 'S-E': [ 'B1B0_0' ], 'W-N': [ 'C0B0_0' ], 'W-W': [ 'C0B0_0' ], 'W-S': [ 'C0B0_0' ], 'N-E': [ 'bottom1B0_0' ], 'N-N': [ 'bottom1B0_0' ], 'N-W': [ 'bottom1B0_0' ], 'E-S': [ 'A0B0_0' ], 'E-E': [ 'A0B0_0' ], 'E-N': [ 'A0B0_0' ] },
    'downstream': { 'N': 'B1', 'E': 'C0', 'S': null, 'W': null },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'B1': {
    'lane_sets': { 'S-W': [ 'B2B1_0' ], 'S-S': [ 'B2B1_0' ], 'S-E': [ 'B2B1_0' ], 'W-N': [ 'C1B1_0' ], 'W-W': [ 'C1B1_0' ], 'W-S': [ 'C1B1_0' ], 'N-E': [ 'B0B1_0' ], 'N-N': [ 'B0B1_0' ], 'N-W': [ 'B0B1_0' ], 'E-S': [ 'A1B1_0' ], 'E-E': [ 'A1B1_0' ], 'E-N': [ 'A1B1_0' ] },
    'downstream': { 'N': 'B2', 'E': 'C1', 'S': 'B0', 'W': 'A1' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'B2': {
    'lane_sets': { 'S-W': [ 'B3B2_0' ], 'S-S': [ 'B3B2_0' ], 'S-E': [ 'B3B2_0' ], 'W-N': [ 'C2B2_0' ], 'W-W': [ 'C2B2_0' ], 'W-S': [ 'C2B2_0' ], 'N-E': [ 'B1B2_0' ], 'N-N': [ 'B1B2_0' ], 'N-W': [ 'B1B2_0' ], 'E-S': [ 'A2B2_0' ], 'E-E': [ 'A2B2_0' ], 'E-N': [ 'A2B2_0' ] },
    'downstream': { 'N': 'B3', 'E': 'C2', 'S': 'B1', 'W': 'A2' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'B3': {
    'lane_sets': { 'S-W': [ 'top1B3_0' ], 'S-S': [ 'top1B3_0' ], 'S-E': [ 'top1B3_0' ], 'W-N': [ 'C3B3_0' ], 'W-W': [ 'C3B3_0' ], 'W-S': [ 'C3B3_0' ], 'N-E': [ 'B2B3_0' ], 'N-N': [ 'B2B3_0' ], 'N-W': [ 'B2B3_0' ], 'E-S': [ 'A3B3_0' ], 'E-E': [ 'A3B3_0' ], 'E-N': [ 'A3B3_0' ] },
    'downstream': { 'N': null, 'E': 'C3', 'S': 'B2', 'W': null },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'C0': {
    'lane_sets': { 'S-W': [ 'C1C0_0' ], 'S-S': [ 'C1C0_0' ], 'S-E': [ 'C1C0_0' ], 'W-N': [ 'D0C0_0' ], 'W-W': [ 'D0C0_0' ], 'W-S': [ 'D0C0_0' ], 'N-E': [ 'bottom2C0_0' ], 'N-N': [ 'bottom2C0_0' ], 'N-W': [ 'bottom2C0_0' ], 'E-S': [ 'B0C0_0' ], 'E-E': [ 'B0C0_0' ], 'E-N': [ 'B0C0_0' ] },
    'downstream': { 'N': 'C1', 'E': null, 'S': null, 'W': 'B0' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'C1': {
    'lane_sets': { 'S-W': [ 'C2C1_0' ], 'S-S': [ 'C2C1_0' ], 'S-E': [ 'C2C1_0' ], 'W-N': [ 'D1C1_0' ], 'W-W': [ 'D1C1_0' ], 'W-S': [ 'D1C1_0' ], 'N-E': [ 'C0C1_0' ], 'N-N': [ 'C0C1_0' ], 'N-W': [ 'C0C1_0' ], 'E-S': [ 'B1C1_0' ], 'E-E': [ 'B1C1_0' ], 'E-N': [ 'B1C1_0' ] },
    'downstream': { 'N': 'C2', 'E': 'D1', 'S': 'C0', 'W': 'B1' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'C2': {
    'lane_sets': { 'S-W': [ 'C3C2_0' ], 'S-S': [ 'C3C2_0' ], 'S-E': [ 'C3C2_0' ], 'W-N': [ 'D2C2_0' ], 'W-W': [ 'D2C2_0' ], 'W-S': [ 'D2C2_0' ], 'N-E': [ 'C1C2_0' ], 'N-N': [ 'C1C2_0' ], 'N-W': [ 'C1C2_0' ], 'E-S': [ 'B2C2_0' ], 'E-E': [ 'B2C2_0' ], 'E-N': [ 'B2C2_0' ] },
    'downstream': { 'N': 'C3', 'E': 'D2', 'S': 'C1', 'W': 'B2' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'C3': {
    'lane_sets': { 'S-W': [ 'top2C3_0' ], 'S-S': [ 'top2C3_0' ], 'S-E': [ 'top2C3_0' ], 'W-N': [ 'D3C3_0' ], 'W-W': [ 'D3C3_0' ], 'W-S': [ 'D3C3_0' ], 'N-E': [ 'C2C3_0' ], 'N-N': [ 'C2C3_0' ], 'N-W': [ 'C2C3_0' ], 'E-S': [ 'B3C3_0' ], 'E-E': [ 'B3C3_0' ], 'E-N': [ 'B3C3_0' ] },
    'downstream': { 'N': null, 'E': null, 'S': 'C2', 'W': 'B3' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'D1': {
    'lane_sets': { 'S-W': [ 'D2D1_0' ], 'S-S': [ 'D2D1_0' ], 'S-E': [ 'D2D1_0' ], 'W-N': [ 'right1D1_0' ], 'W-W': [ 'right1D1_0' ], 'W-S': [ 'right1D1_0' ], 'N-E': [ 'D0D1_0' ], 'N-N': [ 'D0D1_0' ], 'N-W': [ 'D0D1_0' ], 'E-S': [ 'C1D1_0' ], 'E-E': [ 'C1D1_0' ], 'E-N': [ 'C1D1_0' ] },
    'downstream': { 'N': 'D2', 'E': null, 'S': null, 'W': 'C1' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'D2': {
    'lane_sets': { 'S-W': [ 'D3D2_0' ], 'S-S': [ 'D3D2_0' ], 'S-E': [ 'D3D2_0' ], 'W-N': [ 'right2D2_0' ], 'W-W': [ 'right2D2_0' ], 'W-S': [ 'right2D2_0' ], 'N-E': [ 'D1D2_0' ], 'N-N': [ 'D1D2_0' ], 'N-W': [ 'D1D2_0' ], 'E-S': [ 'C2D2_0' ], 'E-E': [ 'C2D2_0' ], 'E-N': [ 'C2D2_0' ] },
    'downstream': { 'N': null, 'E': null, 'S': 'D1', 'W': 'C2' },
    fixed_timings: [ 4, 2, 4, 2, 4, 2, 4, 2 ],
    fixed_phase_order_idx: 0
  },
  'management': {
    'bot_left_mgr': [ 'B0', 'B1', 'A1' ],
    'bot_right_mgr': [ 'C0', 'D1', 'C1' ],
    'top_right_mgr': [ 'C2', 'D2', 'C3' ],
    'top_left_mgr': [ 'A2', 'B2', 'B3' ]
  },
  'management_neighbors': {
    'bot_left_mgr': [ 'bot_right_mgr', 'top_left_mgr' ],
    'bot_right_mgr': [ 'bot_left_mgr', 'top_right_mgr' ],
    'top_right_mgr': [ 'bot_right_mgr', 'top_left_mgr' ],
    'top_left_mgr': [ 'top_right_mgr', 'bot_left_mgr' ]
  }
}
"""

with open("baselines/RESCO/resco_benchmark/config/signal.yaml", "r") as f:
    content = f.read()

if "'hangzhou':" not in content:
    with open("baselines/RESCO/resco_benchmark/config/signal.yaml", "a") as f:
        f.write("\n" + hangzhou_block)
    print("✅ Bloque Hangzhou inyectado con éxito en signal.yaml")
else:
    print("✅ Hangzhou ya está en signal.yaml")
