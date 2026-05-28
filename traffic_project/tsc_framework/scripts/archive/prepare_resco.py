import os
import shutil
import yaml

def prepare_resco():
    print("🚦 Preparando entorno de Hangzhou para RESCO...")
    
    # Rutas base
    base_dir = r"C:\Proyecto_Tesis_Final_V1\traffic_project"
    resco_envs_dir = os.path.join(base_dir, "baselines", "RESCO", "resco_benchmark", "environments")
    hangzhou_resco_dir = os.path.join(resco_envs_dir, "hangzhou")
    
    # Crear directorio si no existe
    os.makedirs(hangzhou_resco_dir, exist_ok=True)
    
    # 1. Copiar archivos de red y rutas
    src_net = os.path.join(base_dir, "tsc_framework", "sumo_configs", "networks", "hangzhou_4x4.net.xml")
    dst_net = os.path.join(hangzhou_resco_dir, "hangzhou.net.xml")
    
    src_route = os.path.join(base_dir, "tsc_framework", "sumo_configs", "routes", "hangzhou", "hangzhou_dense.rou.xml")
    dst_route = os.path.join(hangzhou_resco_dir, "hangzhou.rou.xml")
    
    shutil.copy2(src_net, dst_net)
    print(f"✅ Copiado {src_net} -> {dst_net}")
    
    shutil.copy2(src_route, dst_route)
    print(f"✅ Copiado {src_route} -> {dst_route}")

    # 2. Modificar config.yaml de RESCO
    config_path = os.path.join(base_dir, "baselines", "RESCO", "resco_benchmark", "config", "config.yaml")
    
    with open(config_path, 'r') as f:
        config_content = f.read()
        
    if "hangzhou:" not in config_content:
        hangzhou_config = """
        hangzhou:     
            network: hangzhou.net.xml
            route: hangzhou.rou.xml
            start_time: 0    
            end_time: 3600
"""
        with open(config_path, 'a') as f:
            f.write(hangzhou_config)
        print("✅ Agregado hangzhou a config.yaml")
    else:
        print("ℹ️ hangzhou ya existe en config.yaml")

    print("🎉 Preparación finalizada.")

if __name__ == "__main__":
    prepare_resco()
