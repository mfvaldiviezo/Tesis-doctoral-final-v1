"""
fix_all.py — Script Maestro de Reparación (v3 — netgenerate + diagnóstico)
===========================================================================
Referencia: Tesis Doctoral Cap. 4.2.1, 4.4.1, 4.5.1

SOLUCIÓN CORRECTA:
  Regenerar la red desde cero con netgenerate usando los flags adecuados
  que generan TLS de forma nativa (evita el problema de inyección XML
  que no preserva los atributos tl/linkIndex en connections).

  Estrategia en cascada:
    1. netgenerate con --tls.default-type=actuated (genera TLS correcto)
    2. netconvert --tls.guess=true sobre la red backup (si 1 falla)
    3. Diagnóstico SUMO con stderr visible (si 2 falla)

Uso:
    python scripts/fix_all.py
    python scripts/fix_all.py --skip-test
    python scripts/fix_all.py --diagnose   (muestra stderr de SUMO)
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tsc.fix_all")

# ── Archivos clave ────────────────────────────────────────────────────────────
NET_FILE   = PROJECT_ROOT / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
NET_BAK    = NET_FILE.with_suffix(".xml.bak")
ROUTE_DIR  = PROJECT_ROOT / "sumo_configs" / "routes" / "hangzhou"
MINIMAL    = ROUTE_DIR / "hangzhou_minimal.rou.xml"
N_SCEN     = 100
BASE_SEED  = 42

# ── Rutas válidas (edge IDs del grid A0–D3) ───────────────────────────────────
ROUTES = {
    "r_WE_0": "A0B0 B0C0 C0D0",  "r_WE_1": "A1B1 B1C1 C1D1",
    "r_WE_2": "A2B2 B2C2 C2D2",  "r_WE_3": "A3B3 B3C3 C3D3",
    "r_EW_0": "D0C0 C0B0 B0A0",  "r_EW_1": "D1C1 C1B1 B1A1",
    "r_EW_2": "D2C2 C2B2 B2A2",  "r_EW_3": "D3C3 C3B3 B3A3",
    "r_SN_A": "A0A1 A1A2 A2A3",  "r_SN_B": "B0B1 B1B2 B2B3",
    "r_SN_C": "C0C1 C1C2 C2C3",  "r_SN_D": "D0D1 D1D2 D2D3",
    "r_NS_A": "A3A2 A2A1 A1A0",  "r_NS_B": "B3B2 B2B1 B1B0",
    "r_NS_C": "C3C2 C2C1 C1C0",  "r_NS_D": "D3D2 D2D1 D1D0",
}
EW = [r for r in ROUTES if "WE" in r or "EW" in r]
NS = [r for r in ROUTES if "SN" in r or "NS" in r]

ALL_TLS = ["B1","B2","C1","C2","A1","A2","B0","B3","C0","C3","D1","D2"]


# ═══════════════════════════════════════════════════════════════════════════════
# Búsqueda de binarios SUMO
# ═══════════════════════════════════════════════════════════════════════════════

def _find_sumo_binary(name: str) -> str:
    """
    Busca el binario SUMO (sumo, netgenerate, netconvert).

    PRIORIDAD para netgenerate/netconvert:
      1. SUMO_HOME/bin  (instalación nativa — produce TLS correctos)
      2. Rutas comunes Windows
      3. PATH del sistema (conda suele tener stubs sin funcionalidad TLS)

    Para 'sumo' (simulador), PATH es suficiente.
    """
    sumo_home = os.environ.get("SUMO_HOME", "")

    # Para netgenerate/netconvert: priorizar SUMO_HOME sobre conda PATH
    if name in ("netgenerate", "netconvert", "netedit"):
        # 1. SUMO_HOME primero (instalación nativa completa)
        if sumo_home:
            for ext in [".exe", ""]:
                c = Path(sumo_home) / "bin" / (name + ext)
                if c.exists():
                    return str(c)

        # 2. Rutas comunes Windows
        common_paths = [
            Path("C:/Program Files (x86)/Eclipse/Sumo/bin"),
            Path("C:/Program Files/Eclipse/Sumo/bin"),
            Path("C:/sumo/bin"),
            Path("C:/SUMO/bin"),
        ]
        for d in common_paths:
            for ext in [".exe", ""]:
                c = d / (name + ext)
                if c.exists():
                    return str(c)

        # 3. PATH (puede ser stub de conda)
        found = shutil.which(name)
        if found:
            return found
    else:
        # Para 'sumo': PATH primero
        found = shutil.which(name)
        if found:
            return found
        if sumo_home:
            for ext in [".exe", ""]:
                c = Path(sumo_home) / "bin" / (name + ext)
                if c.exists():
                    return str(c)

    return name


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1: Regenerar red con TLS correctos
# ═══════════════════════════════════════════════════════════════════════════════

def fase1_build_network() -> bool:
    """
    Construye hangzhou_4x4.net.xml con semáforos correctos.

    Estrategia en cascada:
      A. netgenerate --tls.default-type=actuated  (crea red con TLS nativos)
      B. netconvert --tls.guess=true sobre backup  (añade TLS a red existente)
    """
    log.info("══ FASE 1: Construcción de red con semáforos ══")
    NET_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Verificar si la red actual ya tiene TLS VÁLIDOS (con linkIndex en connections)
    if NET_FILE.exists():
        with open(NET_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        n_tl = content.count("<tlLogic ")
        has_link_idx = 'linkIndex="' in content
        log.info(f"  Red actual: {n_tl} tlLogic | linkIndex en connections: {has_link_idx}")
        if n_tl >= len(ALL_TLS) and has_link_idx:
            log.info("  ✅ Red ya tiene TLS correctos con linkIndex — sin cambios.")
            return True
        if n_tl > 0 and not has_link_idx:
            log.warning("  ⚠️  TLS inyectados sin linkIndex — regenerando red...")

    # Archivar original si existe
    if NET_FILE.exists() and not NET_BAK.exists():
        shutil.copy2(NET_FILE, NET_BAK)
        log.info(f"  📦 Backup: {NET_BAK.name}")

    # ── Estrategia A: netgenerate ─────────────────────────────────────────────
    if _try_netgenerate():
        return True

    # ── Estrategia B: netconvert sobre backup ─────────────────────────────────
    if NET_BAK.exists() and _try_netconvert():
        return True

    log.error("  ❌ No se pudo generar red con TLS válidos")
    log.error("     Verifica que SUMO 1.26.0 esté instalado y en el PATH")
    log.error("     o que SUMO_HOME apunte al directorio de instalación")
    return False


def _try_netgenerate() -> bool:
    """
    Genera red 4x4 con TLS usando pipeline de dos pasos:
      Paso 1: netgenerate  → red base sin TLS (esto es normal)
      Paso 2: netconvert --tls.guess=true → añade TLS con linkIndex correcto

    NOTA: --tls.guess=true es flag de netconvert, no de netgenerate.
    netgenerate sólo asigna TLS automáticamente a junctions de 4 vías,
    pero sin los atributos tl/linkIndex en connections que SUMO necesita.
    """
    ng  = _find_sumo_binary("netgenerate")
    nc  = _find_sumo_binary("netconvert")
    tmp = NET_FILE.with_name("hangzhou_base.net.xml")  # red intermedia

    log.info(f"  Paso 1 — netgenerate (red base): {ng}")

    # Paso 1: Generar red base (sin TLS nativos en la mayoría de versiones)
    cmd1 = [
        ng,
        "--grid",
        "--grid.number=4",
        "--grid.length=500",
        "--tls.default-type=actuated",   # Tipo de TLS para los que se añadan
        "--seed=42",
        f"--output-file={tmp}",
    ]
    try:
        r1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30,
                            cwd=str(PROJECT_ROOT))
        log.info(f"  netgenerate returncode: {r1.returncode}")
        if r1.stderr.strip():
            log.info(f"  netgenerate stderr: {r1.stderr[:400]}")
        if not tmp.exists() or r1.returncode != 0:
            log.warning("  netgenerate no produjo archivo de salida")
            return False
    except FileNotFoundError:
        log.warning(f"  netgenerate no encontrado: {ng}")
        return False
    except subprocess.TimeoutExpired:
        log.warning("  netgenerate timeout")
        return False

    # Paso 2: netconvert con --tls.set para forzar TLS en los 12 nodos
    # NOTA: --tls.guess=true no añade TLS a intersecciones de una sola vía.
    # --tls.set lista explícitamente los junction IDs que deben ser semáforos.
    tls_set = ",".join(ALL_TLS)  # "B1,B2,C1,C2,A1,A2,B0,B3,C0,C3,D1,D2"
    log.info(f"  Paso 2 — netconvert --tls.set={tls_set[:40]}...: {nc}")
    cmd2 = [
        nc,
        f"--sumo-net-file={tmp}",
        f"--output-file={NET_FILE}",
        f"--tls.set={tls_set}",
        "--tls.default-type=actuated",
    ]
    try:
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60,
                            cwd=str(PROJECT_ROOT))
        log.info(f"  netconvert returncode: {r2.returncode}")
        if r2.stderr.strip():
            # Mostrar solo líneas relevantes
            for line in r2.stderr.splitlines()[:10]:
                if line.strip():
                    log.info(f"  netconvert: {line.strip()}")
    except FileNotFoundError:
        log.warning(f"  netconvert no encontrado: {nc}")
        # Usar la red base sin TLS (al menos funciona la simulación)
        shutil.copy2(tmp, NET_FILE)
        return False
    except subprocess.TimeoutExpired:
        log.warning("  netconvert timeout")
        return False
    finally:
        # Limpiar archivo temporal
        if tmp.exists():
            tmp.unlink()

    # Verificar resultado — buscar DESPUÉS del comentario XML de netconvert
    if NET_FILE.exists():
        with open(NET_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # El archivo tiene: <!-- <netconvertConfiguration>...</netconvertConfiguration> -->
        # seguido del <net ...> real. Buscar en el contenido completo.
        n_tl   = content.count("<tlLogic")  # Sin espacio - funciona en comentario Y fuera
        # Buscar SOLO después del cierre del comentario (-->)
        comment_end = content.find("-->")
        net_content = content[comment_end:] if comment_end >= 0 else content
        n_tl_real   = net_content.count("<tlLogic")
        has_li      = "linkIndex" in net_content
        log.info(f"  Resultado final: {n_tl_real} tlLogic (fuera comentario) | linkIndex: {has_li}")
        if n_tl_real >= 4:
            log.info(f"  ✅ Red generada con {n_tl_real} semáforos correctos")
            return True
        else:
            log.warning(f"  ⚠️  Solo {n_tl_real} tlLogic reales (esperados >= 4)")
            log.info(f"  Fragmento red: {net_content[50:300]}")
            return False
    return False


def _try_netconvert() -> bool:
    """
    Añade TLS a la red backup usando netconvert --tls.guess=true.
    Se usa como fallback si netgenerate falla.
    """
    nc = _find_sumo_binary("netconvert")
    src = NET_BAK
    if not src.exists():
        log.warning("  Backup no encontrado para netconvert")
        return False

    # Usar --tls.set para forzar TLS en los 12 nodos conocidos de Hangzhou 4x4
    tls_set = ",".join(ALL_TLS)
    log.info(f"  Intentando netconvert --tls.set sobre backup: {nc}")
    cmd = [
        nc,
        f"--sumo-net-file={src}",
        f"--output-file={NET_FILE}",
        f"--tls.set={tls_set}",
        "--tls.default-type=actuated",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           cwd=str(PROJECT_ROOT))
        log.info(f"  netconvert returncode: {r.returncode}")
        if r.stderr.strip():
            for line in r.stderr.splitlines()[:8]:
                if line.strip():
                    log.info(f"  netconvert: {line.strip()}")

        if NET_FILE.exists():
            with open(NET_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            comment_end = content.find("-->")
            net_content = content[comment_end:] if comment_end >= 0 else content
            n_tl   = net_content.count("<tlLogic")
            has_li = "linkIndex" in net_content
            log.info(f"  Resultado: {n_tl} tlLogic | linkIndex: {has_li}")
            if n_tl >= 4:
                log.info(f"  ✅ netconvert: {n_tl} semáforos añadidos")
                return True
    except FileNotFoundError:
        log.warning(f"  netconvert no encontrado: {nc}")
    except subprocess.TimeoutExpired:
        log.warning("  netconvert timeout")
    except Exception as e:
        log.warning(f"  netconvert error: {e}")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2: Rutas
# ═══════════════════════════════════════════════════════════════════════════════

def fase2_generate_routes() -> bool:
    log.info("══ FASE 2: Generación de rutas ══")
    ROUTE_DIR.mkdir(parents=True, exist_ok=True)
    _write_minimal()
    _write_scenarios()
    _verify_edges()
    return True


def _write_minimal() -> None:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">',
        '  <!-- Rutas minimas Hangzhou 4x4 — Cap. 4.4.1 -->',
        '  <!-- NOTA: en SUMO <flow> usa type= (no vType=) para referenciar vType -->',
        '  <vType id="car" length="4.5" minGap="2.5" maxSpeed="13.89" sigma="0.5" tau="1.0"/>',
    ]
    for rid, edges in ROUTES.items():
        lines.append(f'  <route id="{rid}" edges="{edges}"/>')
    for i, rid in enumerate(ROUTES):
        # CORRECTO: <flow> usa type= (no vType=) para referenciar el tipo
        lines.append(f'  <flow id="f_{i:03d}" route="{rid}" type="car" begin="0" end="1800" period="12"/>')
    lines += [
        '  <vehicle id="vs0" type="car" route="r_WE_1" depart="0"/>',
        '  <vehicle id="vs1" type="car" route="r_EW_1" depart="5"/>',
        '  <vehicle id="vs2" type="car" route="r_SN_B" depart="10"/>',
        '</routes>',
    ]
    with open(MINIMAL, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines) + '\n')
    log.info(f"  ✅ {MINIMAL.name} creado")


def _write_scenarios() -> None:
    existing = list(ROUTE_DIR.glob("scenario_*.rou.xml"))
    if len(existing) >= N_SCEN:
        # Verificar que usen edge IDs correctos Y atributo type= correcto
        with open(existing[0], "r", encoding="utf-8") as f:
            sample = f.read()
        has_correct_edges = "A0B0" in sample or "A1B1" in sample
        has_correct_attr  = 'type="car"' in sample and 'vType=' not in sample
        if has_correct_edges and has_correct_attr:
            log.info(f"  ✅ {len(existing)} escenarios ya existen con edge IDs y type= correctos")
            return
        if not has_correct_attr:
            log.warning("  ⚠️  Escenarios usan vType= en lugar de type= — regenerando...")
        log.warning("  Escenarios existentes tienen edge IDs incorrectos — regenerando...")

    sim_t = 1800
    for i in range(N_SCEN):
        if i < N_SCEN // 3:
            d_ew, d_ns = 0.6 + i / (N_SCEN // 3) * 1.1, 0.4 + i / (N_SCEN // 3) * 0.4
        elif i < 2 * N_SCEN // 3:
            t = (i - N_SCEN // 3) / (N_SCEN // 3)
            d_ew = d_ns = 0.7 + t * 0.6
        else:
            t = (i - 2 * N_SCEN // 3) / (N_SCEN // 3)
            d_ew, d_ns = 0.4 + t * 0.4, 0.6 + t * 1.1

        rng = random.Random(BASE_SEED + i)
        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">',
            f'  <!-- Escenario {i:03d} Hangzhou 4x4 seed={BASE_SEED+i} -->',
            '  <vType id="car" accel="2.6" decel="4.5" length="5.0" minGap="2.5" maxSpeed="13.89" sigma="0.5"/>',
        ]
        for rid, edges in ROUTES.items():
            lines.append(f'  <route id="{rid}" edges="{edges}"/>')
        fi = 0
        for rid in EW:
            p = max(3.0, (9.0 / max(d_ew, 0.1)) * rng.uniform(0.8, 1.2))
            n = int(sim_t / p)
            # CORRECTO: <flow> usa type= (no vType=)
            lines.append(f'  <flow id="f_{fi:03d}" route="{rid}" type="car" begin="0" end="{sim_t}" period="{p:.2f}" number="{n}"/>')
            fi += 1
        for rid in NS:
            p = max(3.0, (9.0 / max(d_ns, 0.1)) * rng.uniform(0.8, 1.2))
            n = int(sim_t / p)
            lines.append(f'  <flow id="f_{fi:03d}" route="{rid}" type="car" begin="0" end="{sim_t}" period="{p:.2f}" number="{n}"/>')
            fi += 1
        lines += [
            '  <vehicle id="v000" type="car" route="r_WE_1" depart="0"/>',
            '  <vehicle id="v001" type="car" route="r_SN_B" depart="5"/>',
            '</routes>',
        ]
        out = ROUTE_DIR / f"scenario_{i:03d}_hangzhou.rou.xml"
        with open(out, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines) + '\n')
    log.info(f"  ✅ {N_SCEN} escenarios generados")


def _verify_edges() -> None:
    if not NET_FILE.exists():
        return
    with open(NET_FILE, "r", encoding="utf-8") as f:
        net = f.read()
    missing = [e for edges in ROUTES.values() for e in edges.split() if f'id="{e}"' not in net]
    if missing:
        log.warning(f"  ⚠️  Edge IDs no encontrados ({len(missing)}): {list(set(missing))[:8]}")
    else:
        log.info(f"  ✅ Todos los edge IDs existen en la red")


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3: Diagnóstico SUMO + Test TraCI
# ═══════════════════════════════════════════════════════════════════════════════

def _free_port(start=8813) -> int:
    for p in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p)); return p
            except OSError:
                pass
    return start


def fase3_test_traci(diagnose: bool = False) -> bool:
    log.info("══ FASE 3: Prueba de conexión TraCI ══")

    try:
        import traci
    except ImportError:
        log.error("  TraCI no disponible: pip install traci sumolib")
        return False

    # Cerrar conexión huérfana
    try:
        if traci.isLoaded():
            traci.close(); time.sleep(0.5)
    except Exception:
        pass

    route_file = MINIMAL if MINIMAL.exists() else next(iter(ROUTE_DIR.glob("*.rou.xml")), None)
    if not route_file:
        log.error("  No hay archivos de rutas"); return False

    sumo_bin = _find_sumo_binary("sumo")
    port = _free_port()

    cmd = [
        sumo_bin,
        "--net-file", str(NET_FILE),
        "--route-files", str(route_file),
        "--remote-port", str(port),
        "--step-length", "1",
        "--no-step-log", "true",
        "--start",
        "--quit-on-end",
    ]
    log.info(f"  sumo binary : {sumo_bin}")
    log.info(f"  net-file    : {NET_FILE.name}")
    log.info(f"  route-files : {Path(route_file).name}")
    log.info(f"  puerto      : {port}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
    except FileNotFoundError:
        log.error(f"  'sumo' no encontrado. Verifica PATH o SUMO_HOME.")
        return False

    time.sleep(2.5)

    # Verificar que SUMO sigue vivo
    if proc.poll() is not None:
        out, err = proc.communicate()
        log.error("  SUMO terminó prematuramente:")
        log.error(f"  STDERR:\n{err.decode('utf-8','replace')}")
        return False

    log.info(f"  SUMO iniciado (PID {proc.pid})")

    ok = False
    stderr_content = ""
    try:
        for attempt in range(12):
            try:
                if traci.isLoaded():
                    traci.close(); time.sleep(0.3)
                traci.init(port=port, numRetries=1)
                log.info(f"  ✅ TraCI conectado (intento {attempt+1})")
                ok = True
                break
            except ConnectionRefusedError:
                time.sleep(1.0)
            except Exception as e:
                emsg = str(e)
                if "already active" in emsg:
                    try: traci.close()
                    except Exception: pass
                    time.sleep(0.5)
                else:
                    log.error(f"  Error TraCI: {emsg}")
                    # Capturar stderr de SUMO para diagnóstico
                    time.sleep(0.5)
                    if proc.poll() is not None:
                        _, err_bytes = proc.communicate()
                        stderr_content = err_bytes.decode("utf-8", "replace")
                    break

        if ok:
            for _ in range(5):
                traci.simulationStep()
            t   = traci.simulation.getTime()
            veh = len(traci.vehicle.getIDList())
            tls = traci.trafficlight.getIDList()
            log.info(f"  simulationStep x5 → tiempo={t}s | vehículos={veh}")
            log.info(f"  Semáforos ({len(tls)}): {', '.join(tls)}")
            present = [x for x in ALL_TLS if x in tls]
            log.info(f"  TLS esperados presentes: {len(present)}/{len(ALL_TLS)}")

    finally:
        try:
            if traci.isLoaded(): traci.close()
        except Exception: pass
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill()

        # Obtener stderr si SUMO ya terminó
        if proc.poll() is not None and not stderr_content:
            try:
                _, err_bytes = proc.communicate(timeout=2)
                stderr_content = err_bytes.decode("utf-8", "replace")
            except Exception:
                pass

    # Mostrar diagnóstico si hay errores
    if not ok or diagnose:
        if stderr_content.strip():
            log.info("\n" + "─" * 50)
            log.info("SALIDA DE ERROR DE SUMO (diagnóstico):")
            # Filtrar solo líneas de error/warning relevantes
            for line in stderr_content.splitlines():
                if any(kw in line for kw in ["Error", "error", "Warning", "Cannot", "unknown"]):
                    log.info(f"  SUMO: {line.strip()}")
            log.info("─" * 50)
        else:
            log.warning("  Sin stderr de SUMO disponible para diagnóstico")
            # Intentar validar la red manualmente
            log.info("  Ejecutando validación manual de la red...")
            _validate_network_dry_run(sumo_bin, route_file)

    return ok


def _validate_network_dry_run(sumo_bin: str, route_file) -> None:
    """Ejecuta SUMO sin TraCI para ver errores de carga de red."""
    cmd = [
        sumo_bin,
        "--net-file", str(NET_FILE),
        "--route-files", str(route_file),
        "--step-length", "1",
        "--no-step-log", "true",
        "--end", "10",
    ]
    log.info("  Validación SUMO (sin TraCI, end=10s):")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                           cwd=str(PROJECT_ROOT))
        if r.stderr.strip():
            log.info("  SUMO output:")
            for line in r.stderr.splitlines()[:30]:
                log.info(f"    {line}")
        if r.returncode == 0:
            log.info("  ✅ SUMO puede cargar la red sin TraCI")
        else:
            log.error(f"  ❌ SUMO falló (code {r.returncode})")
    except Exception as e:
        log.warning(f"  Error en validación: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Reparación completa TSC framework v3")
    parser.add_argument("--skip-test", action="store_true")
    parser.add_argument("--diagnose", action="store_true",
                        help="Mostrar stderr de SUMO aunque la prueba pase")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("\n" + "=" * 60)
    print("REPARACIÓN TSC FRAMEWORK v3")
    print("Referencia: Tesis Doctoral Cap. 4.2.1, 4.4.1, 4.5.1")
    print("=" * 60)

    # Mostrar qué herramientas SUMO están disponibles
    for tool in ["sumo", "netgenerate", "netconvert"]:
        p = _find_sumo_binary(tool)
        found = shutil.which(p) or (Path(p).exists() if Path(p).is_absolute() else False)
        log.info(f"  {tool:15s}: {p} ({'OK' if found else 'no en PATH'})")
    print()

    results = {}
    results["fase1_red"]   = fase1_build_network()
    print()
    results["fase2_rutas"] = fase2_generate_routes()
    print()
    if not args.skip_test:
        results["fase3_traci"] = fase3_test_traci(diagnose=args.diagnose)
        print()

    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for fase, ok in results.items():
        print(f"  {fase}: {'✅ OK' if ok else '❌ FALLO'}")

    if all(results.values()):
        print("\n✅ Framework listo:")
        print("   python scripts/test_sumo_connection.py --mode benchmark")
        sys.exit(0)
    else:
        print("\n⚠️  Ejecuta con --diagnose para ver errores de SUMO:")
        print("   python scripts/fix_all.py --diagnose")
        sys.exit(1)


if __name__ == "__main__":
    main()
