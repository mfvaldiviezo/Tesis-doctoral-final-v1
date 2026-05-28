import os
import sys
import time
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import gymnasium as gym
from stable_baselines3 import PPO

from src.core.tsc_env import TSCEnv

def main():
    print("🚀 Iniciando prueba visual del modelo entrenado...")
    
    # 1. Configuración manual (ya que no usamos el loader roto)
    sumocfg_path = ROOT_DIR / "sumo_configs" / "hangzhou.sumocfg"
    tls_id = "B1"  # El ID que aparecía en tus logs anteriores
    use_gui = True
    delta_t = 5
    max_steps = 3600
    
    # Verificar que el archivo .sumocfg existe
    if not sumocfg_path.exists():
        print(f"❌ Error: No se encontró el archivo de configuración en: {sumocfg_path}")
        print("   Asegúrate de haber ejecutado fix_all.py o de tener hangzhou.sumocfg en sumo_configs/")
        return

    print(f"📂 Usando configuración: {sumocfg_path}")
    print(f"🚦 Controlando semáforo: {tls_id}")
    print(f"💻 Usando dispositivo: CPU")
    
    # 2. Crear entorno con la firma CORRECTA
    try:
        env = TSCEnv(
            sumocfg_path=str(sumocfg_path),
            tls_id=tls_id,
            use_gui=use_gui,
            delta_t=delta_t,
            max_steps=max_steps,
            seed=42
        )
        print("✅ Entorno inicializado correctamente.")
    except Exception as e:
        print(f"❌ Error al inicializar el entorno: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Cargar modelo
    model_path = ROOT_DIR / "outputs" / "models" / "ppo_final.zip"
    if not model_path.exists():
        print(f"❌ Error: No se encontró el modelo en {model_path}")
        return
    print(f"📥 Cargando modelo desde {model_path}...")
    
    try:
        model = PPO.load(str(model_path), device="cpu")
        # Asignar el entorno al modelo cargado
        model.set_env(env) 
        print("✅ Modelo cargado y vinculado al entorno.")
    except Exception as e:
        print(f"❌ Error al cargar el modelo: {e}")
        env.close()
        return
    
    # 4. Ejecutar episodio
    print("🎬 Iniciando simulación... (Cierra la ventana SUMO para detener)")
    
    obs, info = env.reset()
    done = False
    total_reward = 0.0
    step = 0
    
    try:
        while not done:
            # Predecir acción
            action, _states = model.predict(obs, deterministic=True)
            
            # Ejecutar paso
            obs, reward, terminated, truncated, info = env.step(action)
            
            done = terminated or truncated
            total_reward += float(reward)
            step += 1
            
            # Feedback cada 50 pasos
            if step % 50 == 0:
                print(f"⏱️  Paso: {step} | Reward acumulado: {total_reward:.2f}")
                
    except KeyboardInterrupt:
        print("\n⛔ Simulación interrumpida por el usuario.")
    except Exception as e:
        print(f"\n❌ Error durante la simulación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n🏁 Episodio finalizado.")
        print(f"📊 Pasos totales: {step}")
        print(f"🏆 Recompensa total: {total_reward:.2f}")
        env.close()
        print("👋 Entorno cerrado correctamente.")

if __name__ == "__main__":
    main()
