import sys, os
sys.path.insert(0, '.')
from src.core.tsc_env import TSCEnv
from stable_baselines3 import PPO

# Configuración manual
SUMOCFG_PATH = "sumo_configs/hangzhou.sumocfg"
TLS_ID = "B1"
IMPRUDENT_ROUTES = "results/quito_scenarios/imprudent_drivers_0.rou.xml"

print("🚀 Prueba con conductores IMPRUDENTES (Quito)...")

# NOTA: Debes modificar el .sumocfg o pasar la ruta de rutas al entorno
# Si tu TSCEnv lo soporta, usa el parámetro route_files
# Si no, edita temporalmente hangzhou.sumocfg para apuntar a la ruta imprudente

env = TSCEnv(
    sumocfg_path=SUMOCFG_PATH,
    tls_id=TLS_ID,
    use_gui=True,
    delta_t=5,
    max_steps=720,
    seed=42
)

model = PPO.load("outputs/models/ppo_final.zip", env=env, device="cpu")

obs, _ = env.reset()
done = False
total_reward = 0
step = 0

while not done:
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
    total_reward += reward
    step += 1
    if step % 50 == 0:
        print(f"⏱️ Paso: {step} | Reward: {total_reward:.2f}")

print(f"🏁 Finalizado | Reward Total: {total_reward:.2f}")
env.close()
