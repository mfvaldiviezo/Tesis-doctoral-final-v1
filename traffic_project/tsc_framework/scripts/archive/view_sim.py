"""
view_sim.py — Demo visual standalone de la red Hangzhou 4x4
============================================================
Lanza sumo-gui con la configuración del framework sin necesidad
de entrenamiento ni TraCI controlado. Solo visualización pura.

Uso:
    python scripts/view_sim.py              # Velocidad normal
    python scripts/view_sim.py --delay 100  # Más lento
    python scripts/view_sim.py --regen      # Regenerar red primero
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NET_FILE   = PROJECT_ROOT / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
ROUTE_FILE = PROJECT_ROOT / "sumo_configs" / "routes" / "hangzhou" / "hangzhou_minimal.rou.xml"


def check_network() -> bool:
    """Verifica que la red tenga semáforos definidos."""
    if not NET_FILE.exists():
        print(f"❌ Red no encontrada: {NET_FILE}")
        return False
    content = NET_FILE.read_text(encoding="utf-8", errors="replace")
    # Buscar después del comentario XML de netconvert
    comment_end = content.find("-->")
    net_content = content[comment_end:] if comment_end >= 0 else content
    n_tls = net_content.count("<tlLogic")
    if n_tls == 0:
        print(f"⚠️  La red no tiene semáforos (tlLogic=0).")
        return False
    print(f"✅ Red OK | {n_tls} semáforos encontrados")
    return True


def main():
    parser = argparse.ArgumentParser(description="Demo visual SUMO-GUI Hangzhou 4x4")
    parser.add_argument("--delay", type=int, default=50,
                        help="Delay entre pasos en ms (default=50, más alto=más lento)")
    parser.add_argument("--regen", action="store_true",
                        help="Regenerar red con fix_all.py antes de lanzar")
    args = parser.parse_args()

    print("=" * 55)
    print("  Demo Visual — Red Hangzhou 4×4 con Semáforos")
    print("=" * 55)

    # Regenerar red si se pide o si no tiene semáforos
    if args.regen or not check_network():
        print("\n🔧 Regenerando red con fix_all.py...")
        result = subprocess.run(
            [sys.executable, "scripts/fix_all.py", "--skip-test"],
            cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            print("❌ fix_all.py falló. Verifica la instalación de SUMO.")
            sys.exit(1)
        if not check_network():
            print("❌ La red sigue sin semáforos después de regenerar.")
            sys.exit(1)

    if not ROUTE_FILE.exists():
        print(f"❌ Archivo de rutas no encontrado: {ROUTE_FILE}")
        sys.exit(1)

    print(f"\n🚀 Lanzando SUMO-GUI (delay={args.delay}ms)...")
    print("   💡 Presiona el botón ▶ (Play) para iniciar la simulación")
    print("   💡 Los semáforos deben aparecer en colores (verde/amarillo/rojo)")
    print("   💡 Cierra la ventana cuando termines\n")

    cmd = [
        "sumo-gui",
        "-n", str(NET_FILE),
        "-r", str(ROUTE_FILE),
        "--start",                      # Auto-iniciar al abrir
        f"--delay={args.delay}",        # Ms entre pasos para visualización
        "--quit-on-end",               # Cerrar al terminar la simulación
        "--no-step-log",
        "--time-to-teleport", "-1",    # No teletransportar vehículos
    ]

    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        print("\n✅ Simulación visual completada.")
    except FileNotFoundError:
        print("❌ sumo-gui no encontrado en PATH.")
        print("   Verifica que SUMO esté instalado y en el PATH del sistema.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹  Simulación interrumpida.")


if __name__ == "__main__":
    main()
