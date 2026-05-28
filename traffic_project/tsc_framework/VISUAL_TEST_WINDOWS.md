# 🚦 PRUEBA VISUAL DEL FRAMEWORK - Windows PowerShell
## Guía Detallada para Demostración de Tesis Doctoral

Esta guía te permitirá ejecutar una **prueba visual completa** del framework TSC desde tu entorno local en Windows, demostrando el comportamiento de conductores imprudentes latinoamericanos en escenarios de tráfico.

---

## 📋 REQUISITOS PREVIOS

### 1. Verificar Instalación de SUMO
```powershell
# Abrir PowerShell como Administrador y ejecutar:
sumo --version
```
**Salida esperada:** `SUMO Version 1.26.0` (o superior)

Si no funciona, agregar SUMO al PATH:
```powershell
$env:Path += ";C:\Program Files (x86)\Eclipse\Sumo\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
```

### 2. Verificar Entorno Conda
```powershell
cd C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework
conda activate tsc-env
python --version
```
**Salida esperada:** `Python 3.12.x`

---

## 🔧 PASO 1: CONFIGURAR VARIABLES DE ENTORNO

### Establecer SUMO_HOME (Persistente)
```powershell
# Ejecutar UNA VEZ (configuración persistente)
[Environment]::SetEnvironmentVariable("SUMO_HOME", "C:\Program Files (x86)\Eclipse\Sumo", "User")

# Para la sesión actual
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
```

### Verificar configuración
```powershell
echo $env:SUMO_HOME
```
**Debe mostrar:** `C:\Program Files (x86)\Eclipse\Sumo`

---

## 🎯 PASO 2: ACTIVAR ENTORNO E INSTALAR PAQUETE

```powershell
# Navegar al directorio del proyecto
cd C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework

# Activar entorno conda
conda activate tsc-env

# Instalar paquete en modo editable
pip install -e .
```

**Salida esperada:** `Successfully installed tsc-framework-0.1.0`

---

## ✅ PASO 3: VERIFICAR CONEXIÓN CON SUMO

```powershell
# Ejecutar test de conexión
python scripts/test_sumo_connection.py
```

**Salida exitosa esperada:**
```
============================================================
TEST DE CONEXIÓN TRACI - tsc_framework
============================================================
✅ Archivo de red encontrado: sumo_configs/networks/hangzhou_4x4.net.xml
✅ 101 archivos de ruta encontrados
✅ ¡Conexión exitosa!
✅ TODAS LAS PRUEBAS SUPERADAS
```

⚠️ **Si falla:** Verifica que SUMO esté en PATH y SUMO_HOME configurado.

---

## 🚗 PASO 4: GENERAR ESCENARIOS CON CONDUCTORES IMPRUDENTES

### Opción A: Usar Dataset Expandido (Recomendado)
```powershell
# Generar 100 escenarios por nivel de estrés (nominal, moderate, extreme)
python scripts/generate_imprudent_drivers_simple.py `
    --data-path data/quito_behavior/micro_behavior_expanded.csv `
    --output-dir results/quito_scenarios `
    --n-scenarios 100
```

### Opción B: Usar Dataset Original
```powershell
python scripts/generate_imprudent_drivers_simple.py `
    --data-path data/quito_behavior/micro_behavior.csv `
    --output-dir results/quito_scenarios `
    --n-scenarios 50
```

**Salida esperada:**
```
Ranking de imprudencia (mayor score = más imprudente):
  imprudente_2: 0.7123
  imprudente_4: 0.6938
  imprudente_5: 0.6768
  ...
Generados 300 escenarios totales
Archivo exportado: results/quito_scenarios/imprudent_drivers.rou.xml (300 vehículos)
```

---

## 👁️ PASO 5: PRUEBA VISUAL CON SUMO-GUI

### Método 1: Visualización Directa con Configuración Existente

```powershell
# Crear archivo de configuración temporal para prueba visual
$sumocfg = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumo_config.xsd">
    <input>
        <net-file value="sumo_configs/networks/hangzhou_4x4.net.xml"/>
        <route-files value="results/quito_scenarios/imprudent_drivers.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
        <waiting-time-memory value="1000"/>
    </processing>
    <report>
        <no-warnings value="true"/>
    </report>
    <gui_only>
        <start value="true"/>
        <game-mode value="false"/>
    </gui_only>
</configuration>
"@

# Guardar configuración
$sumocfg | Out-File -FilePath "sumo_configs/test_visual.sumocfg" -Encoding UTF8

# Lanzar SUMO-GUI con conductores imprudentes
sumo-gui -c sumo_configs/test_visual.sumocfg
```

### Método 2: Comando Directo (Más Simple)

```powershell
# Lanzar directamente con suma-gui
sumo-gui `
    -c sumo_configs/hangzhou.sumocfg `
    --route-files results/quito_scenarios/imprudent_drivers.rou.xml `
    --start
```

### Método 3: Script Dedicado de Visualización

Crear archivo `scripts/visualize_imprudent.py`:

```python
#!/usr/bin/env python3
"""
Script para visualización de conductores imprudentes en SUMO-GUI.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Ruta al proyecto
    project_root = Path(__file__).parent.parent
    
    # Archivos requeridos
    net_file = project_root / "sumo_configs" / "networks" / "hangzhou_4x4.net.xml"
    route_file = project_root / "results" / "quito_scenarios" / "imprudent_drivers.rou.xml"
    sumo_cfg = project_root / "sumo_configs" / "test_visual.sumocfg"
    
    # Verificar existencia
    if not net_file.exists():
        print(f"❌ Red no encontrada: {net_file}")
        sys.exit(1)
    
    if not route_file.exists():
        print(f"❌ Rutas no generadas: {route_file}")
        print("💡 Ejecuta primero: python scripts/generate_imprudent_drivers_simple.py")
        sys.exit(1)
    
    # Crear configuración temporal
    config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <gui_only>
        <start value="true"/>
    </gui_only>
</configuration>
"""
    
    with open(sumo_cfg, 'w') as f:
        f.write(config_content)
    
    print("=" * 60)
    print("🚦 INICIANDO SIMULACIÓN VISUAL")
    print("=" * 60)
    print(f"📍 Red: {net_file.name}")
    print(f"🚗 Rutas: {route_file.name}")
    print(f"🎮 GUI: Habilitada")
    print("=" * 60)
    print("\n💡 Controles de SUMO-GUI:")
    print("   - Click derecho: Cambiar vista")
    print("   - Rueda del ratón: Zoom")
    print("   - Barra espaciadora: Pausar/Continuar")
    print("   - Ctrl + T: Mostrar semáforos")
    print("   - Ctrl + V: Mostrar vehículos")
    print("=" * 60)
    
    # Lanzar SUMO-GUI
    try:
        subprocess.run(["sumo-gui", "-c", str(sumo_cfg)], check=True)
    except FileNotFoundError:
        print("❌ ERROR: sumo-gui no encontrado")
        print("💡 Asegúrate de tener SUMO instalado y en PATH")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✅ Simulación finalizada por el usuario")

if __name__ == "__main__":
    main()
```

Ejecutar visualización:
```powershell
python scripts/visualize_imprudent.py
```

---

## 🎬 PASO 6: OBSERVAR COMPORTAMIENTOS CLAVE

Durante la simulación visual, identifica:

### Conductores Conservadores (Color Verde Claro)
- `sigma` alto (~2.0-2.5): Conducción suave, predecible
- `tau` alto (~1.3-1.5): Mayor tiempo de reacción
- `speedFactor` bajo (~1.0-1.05): Respetan límites de velocidad
- **Comportamiento**: Mantienen distancia, frenan suavemente

### Conductores Normales (Color Amarillo-Verdoso)
- `sigma` medio (~1.4-1.7): Variabilidad moderada
- `tau` medio (~0.95-1.1): Tiempo de reacción promedio
- `speedFactor` medio (~1.13-1.16): Exceden ligeramente el límite
- **Comportamiento**: Típico de tráfico urbano

### Conductores Imprudentes (Color Rojo-Naranja) ⚠️
- `sigma` bajo (~1.0-1.2): Conducción errática, impredecible
- `tau` bajo (~0.78-0.87): Poco tiempo de reacción
- `speedFactor` alto (~1.17-1.21): Exceden significativamente el límite
- **Comportamiento**: Frenazos bruscos, acelerones, cercanía peligrosa

### Métricas Visuales a Observar:
1. **Formación de colas**: ¿Los imprudentes causan más congestión?
2. **Frenado en cadena**: Efecto "accordión" por comportamientos erráticos
3. **Conflictos en intersecciones**: ¿Mayor número de situaciones de riesgo?
4. **Tiempo de viaje**: Comparar entre diferentes tipos de conductores

---

## 📊 PASO 7: EJECUTAR ENTRENAMIENTO RL (OPCIONAL)

Para demostrar que los modelos RL tradicionales fallan con conductores imprudentes:

```powershell
# Entrenamiento rápido para demostración (10,000 pasos)
python scripts/train.py `
    --timesteps 10000 `
    --n-envs 1 `
    --seed 42 `
    --experiment-name demo_imprudent

# Entrenamiento completo (1 millón de pasos)
python scripts/train.py `
    --timesteps 1000000 `
    --n-envs 4 `
    --seed 42 `
    --experiment-name hangzhou_robustness
```

**Monitorear entrenamiento:**
```powershell
# En otra terminal PowerShell
tensorboard --logdir outputs/logs
```
Navegar a: http://localhost:6006

---

## 📈 PASO 8: EVALUAR MODELOS Y GENERAR MÉTRICAS

```powershell
# Evaluar modelo entrenado
python scripts/evaluate.py `
    --model outputs/models/demo_imprudent/ppo_tsc_final.zip `
    --episodes 50 `
    --render

# Generar reporte comparativo
python scripts/evaluate.py `
    --model outputs/models/demo_imprudent/ppo_tsc_final.zip `
    --baseline fixed_time `
    --episodes 100 `
    --output-file results/comparison_report.csv
```

---

## 🎥 PASO 9: GRABAR SIMULACIÓN PARA PRESENTACIÓN

### Opción A: Captura de Pantalla con OBS Studio
1. Instalar OBS Studio (https://obsproject.com/)
2. Configurar captura de ventana de SUMO-GUI
3. Grabar mientras se ejecuta la simulación

### Opción B: Exportar Frames desde Python
Crear script `scripts/record_simulation.py`:

```python
#!/usr/bin/env python3
"""
Grabar simulación SUMO como secuencia de imágenes.
"""

import traci
import subprocess
import os
from pathlib import Path

# Configuración
output_dir = Path("outputs/recordings")
output_dir.mkdir(parents=True, exist_ok=True)

# Iniciar SUMO
sumo_cmd = [
    "sumo-gui",
    "-c", "sumo_configs/test_visual.sumocfg",
    "--game-mode", "false",
]

proc = subprocess.Popen(sumo_cmd)

# Conectar TraCI
traci.init(port=8813)

step = 0
while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    
    # Capturar frame cada 10 steps
    if step % 10 == 0:
        # Nota: Requiere configuración adicional para screenshots
        pass
    
    step += 1

traci.close()
proc.wait()
```

---

## 📋 CHECKLIST PARA DEMOSTRACIÓN

### Antes de la Demostración:
- [ ] SUMO instalado y verificado (`sumo --version`)
- [ ] Entorno conda activado (`conda activate tsc-env`)
- [ ] Dataset expandido generado (6,710 muestras)
- [ ] Escenarios de conductores imprudentes creados
- [ ] Prueba de conexión exitosa
- [ ] SUMO-GUI abre correctamente

### Durante la Demostración:
1. [ ] Mostrar estructura del proyecto
2. [ ] Ejecutar generación de conductores imprudentes
3. [ ] Abrir SUMO-GUI con escenario visual
4. [ ] Señalar diferencias entre conductores (colores)
5. [ ] Mostrar ranking de imprudencia (JSON)
6. [ ] Explicar métricas (sigma, tau, speedFactor)
7. [ ] Demostrar formación de colas y conflictos
8. [ ] (Opcional) Mostrar entrenamiento RL en TensorBoard
9. [ ] Presentar métricas de evaluación comparativa

### Después de la Demostración:
- [ ] Guardar capturas de pantalla
- [ ] Exportar métricas a CSV/Excel
- [ ] Documentar observaciones clave
- [ ] Preparar gráficos para tesis

---

## 🔧 SOLUCIÓN DE PROBLEMAS COMUNES

### Error: "sumo-gui no se reconoce"
```powershell
# Agregar al PATH permanentemente
$env:Path += ";C:\Program Files (x86)\Eclipse\Sumo\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")

# Reiniciar PowerShell y verificar
sumo-gui --version
```

### Error: "Could not connect to TraCI"
```powershell
# Matar procesos SUMO residuales
Get-Process sumo* | Stop-Process -Force

# Intentar con otro puerto
sumo-gui -c sumo_configs/test_visual.sumocfg --remote-port 8814
```

### Error: "Archivo .rou.xml no encontrado"
```powershell
# Regenerar escenarios
python scripts/generate_imprudent_drivers_simple.py `
    --data-path data/quito_behavior/micro_behavior_expanded.csv `
    --output-dir results/quito_scenarios `
    --n-scenarios 100
```

### Error: "ModuleNotFoundError"
```powershell
# Reinstalar paquete
pip uninstall tsc-framework -y
pip install -e .
```

### SUMO-GUI se cierra inmediatamente
1. Verificar que el archivo `.sumocfg` exista
2. Asegurar que las rutas en el XML sean correctas
3. Probar abrir SUMO-GUI manualmente y cargar archivos

---

## 💡 CONSEJOS PARA PRESENTACIÓN DE TESIS

### Narrativa Sugerida:
1. **Introducción**: "Actualmente los modelos RL asumen conductores ideales..."
2. **Problema**: "En Latinoamérica, el comportamiento es más imprudente..."
3. **Solución**: "Mi framework modela conductores basados en datos reales de Quito..."
4. **Demostración**: Mostrar visualmente las diferencias
5. **Resultados**: "Los modelos tradicionales fallan X% más con conductores imprudentes"
6. **Contribución**: "Entrenar con estos comportamientos mejora la robustez Y%"

### Puntos Clave a Destacar:
- ✅ Dataset real de Quito (acelerómetros, GPS, ritmo cardíaco)
- ✅ 20 perfiles de conductores (conservadores, normales, imprudentes)
- ✅ Condiciones ambientales (lluvia, hora pico)
- ✅ 3 niveles de estrés (nominal, moderate, extreme)
- ✅ Métricas cuantitativas (Gini, CVaR, Delay)
- ✅ Validación en benchmark internacional (Hangzhou)

### Gráficos Recomendados:
1. Histograma de distribución de imprudencia
2. Comparativa de delay: conductores ideales vs. imprudentes
3. Curva de aprendizaje RL con/sin conductores imprudentes
4. Mapa de calor de conflictos en intersecciones

---

## 📞 SOPORTE Y DOCUMENTACIÓN ADICIONAL

### Archivos de Referencia:
- `AUDITORIA_COMPLETA_2024.md`: Estado actual del framework
- `QUICKSTART_WINDOWS.md`: Guía de inicio rápido
- `config/default_config.yaml`: Configuración maestra
- `results/quito_scenarios/driver_analysis.json`: Ranking de conductores

### Scripts Principales:
- `scripts/expand_quito_dataset.py`: Expande dataset sintético
- `scripts/generate_imprudent_drivers_simple.py`: Genera escenarios
- `scripts/visualize_imprudent.py`: Visualización GUI
- `scripts/train.py`: Entrenamiento RL
- `scripts/evaluate.py`: Evaluación de modelos

### Contacto:
Para soporte técnico o preguntas sobre la implementación, revisar logs en:
- `outputs/logs/`: Logs de entrenamiento
- `results/quito_scenarios/`: Resultados de generación

---

**Última actualización**: Mayo 2024  
**Versión del framework**: 1.0.0  
**Estado**: ✅ Listo para demostración de tesis doctoral
