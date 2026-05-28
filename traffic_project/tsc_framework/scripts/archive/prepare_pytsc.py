import os
import shutil

# Paths
SRC_NET = "tsc_framework/sumo_configs/hangzhou/hangzhou_pedestrian.net.xml"
SRC_ROU_NORMAL = "tsc_framework/experiments/hangzhou_robustness/scenarios/hangzhou_normal_drivers.rou.xml"
SRC_ROU_LATAM = "tsc_framework/experiments/hangzhou_robustness/scenarios/latam_imprudent_drivers.rou.xml"
SRC_ADD = "tsc_framework/experiments/hangzhou_robustness/scenarios/latam_infrastructure.add.xml"

PYTSC_SCENARIO_DIR = "baselines/pytsc/pytsc/scenarios/sumo/hangzhou"

os.makedirs(PYTSC_SCENARIO_DIR, exist_ok=True)

# Copiar archivos
shutil.copy(SRC_NET, os.path.join(PYTSC_SCENARIO_DIR, "hangzhou.net.xml"))
shutil.copy(SRC_ROU_NORMAL, os.path.join(PYTSC_SCENARIO_DIR, "hangzhou_normal.rou.xml"))
shutil.copy(SRC_ROU_LATAM, os.path.join(PYTSC_SCENARIO_DIR, "hangzhou_latam.rou.xml"))
shutil.copy(SRC_ADD, os.path.join(PYTSC_SCENARIO_DIR, "latam_infrastructure.add.xml"))

# Create sumocfg for NORMAL
with open(os.path.join(PYTSC_SCENARIO_DIR, "hangzhou_normal.sumocfg"), "w") as f:
    f.write("""<configuration>
    <input>
        <net-file value="hangzhou.net.xml"/>
        <route-files value="hangzhou_normal.rou.xml"/>
        <additional-files value="latam_infrastructure.add.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>""")

# Create sumocfg for LATAM
with open(os.path.join(PYTSC_SCENARIO_DIR, "hangzhou_latam.sumocfg"), "w") as f:
    f.write("""<configuration>
    <input>
        <net-file value="hangzhou.net.xml"/>
        <route-files value="hangzhou_latam.rou.xml"/>
        <additional-files value="latam_infrastructure.add.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>""")

print("✅ Escenario Hangzhou (Normal y LATAM) copiado exitosamente dentro de PyTSC.")
