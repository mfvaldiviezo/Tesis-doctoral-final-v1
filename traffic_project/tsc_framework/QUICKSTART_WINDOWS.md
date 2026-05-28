# 🚀 Guía de Inicio Rápido - tsc_framework

## Para Usuarios en Windows con SUMO Instalado

### ✅ Prerrequisitos Verificados
- [x] SUMO 1.26.0 instalado en `C:\Program Files (x86)\Eclipse\Sumo`
- [x] Entorno Conda `tsc-env` creado
- [x] Repositorio clonado en `C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework`

---

## 📋 PASOS DE CONFIGURACIÓN

### Paso 1: Configurar Variable de Entorno SUMO_HOME

**Opción A: PowerShell (sesión actual)**
```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
```

**Opción B: PowerShell (persistente - recomendado)**
```powershell
[Environment]::SetEnvironmentVariable("SUMO_HOME", "C:\Program Files (x86)\Eclipse\Sumo", "User")
```

**Opción C: Interfaz Gráfica**
1. Win + R → `sysdm.cpl` → Enter
2. Pestaña "Opciones avanzadas" → "Variables de entorno"
3. En "Variables de usuario", click en "Nueva"
4. Nombre: `SUMO_HOME`
5. Valor: `C:\Program Files (x86)\Eclipse\Sumo`
6. Aceptar todo y reiniciar PowerShell

---

### Paso 2: Activar Entorno e Instalar Paquete

```powershell
cd C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework
conda activate tsc-env
pip install -e .
```

---

### Paso 3: Verificar Instalación

```powershell
# Verificar SUMO
sumo --version

# Verificar TraCI
python -c "import traci; print('TraCI OK')"

# Verificar framework
python -c "from src.core.tsc_env import TSCEnv; print('TSCEnv OK')"
```

---

### Paso 4: Ejecutar Test de Conexión

```powershell
python scripts/test_sumo_connection.py
```

**Salida esperada:**
```
============================================================
TEST DE CONEXIÓN TRACI - tsc_framework
Referencia: Tesis Doctoral Cap. 4.2.1
============================================================

📄 Configuración cargada: config/default_config.yaml
   - Modo de red: benchmark
   - Seed: 42
   - Step length: 5s

============================================================
VALIDACIÓN DE ARCHIVOS
============================================================
✅ Archivo de red encontrado: sumo_configs/networks/hangzhou_4x4.net.xml
✅ 101 archivos de ruta encontrados en sumo_configs/routes/hangzhou/

============================================================
INICIANDO SERVIDOR SUMO
============================================================
🚗 Lanzando SUMO: sumo -c sumo_configs/hangzhou.sumocfg ...
✅ Proceso SUMO iniciado correctamente

============================================================
PRUEBA DE CONEXIÓN TRACI
============================================================
🔍 Intentando conectar a localhost:8813...
✅ ¡Conexión exitosa en intento 1!
✅ simulationStep() ejecutado correctamente
   - Tiempo de simulación: 0.0s
   - Vehículos en red: 4

============================================================
✅ TODAS LAS PRUEBAS SUPERADAS
============================================================

El framework está listo para entrenamiento.
Ejecuta: python scripts/train.py --timesteps 1000
```

---

## 🎯 COMANDOS DE USO FRECUENTE

### Entrenamiento Básico
```powershell
# Entrenamiento rápido (1000 pasos)
python scripts/train.py --timesteps 1000 --n-envs 1

# Entrenamiento completo (1 millón de pasos)
python scripts/train.py --timesteps 1000000 --n-envs 4
```

### Evaluación
```powershell
# Evaluar modelo entrenado
python scripts/evaluate.py --model models/ppo_tsc_final.zip --episodes 50

# Comparar con baselines
python scripts/run_baselines.py --episodes 50
```

### Generación de Escenarios
```powershell
# Regenerar 100 escenarios de Hangzhou
python scripts/generate_hangzhou_scenarios.py
```

### Importar Red desde OpenStreetMap
```powershell
# Descargar archivo .osm desde https://download.geofabrik.de/
# Luego ejecutar:
python scripts/import_osm.py --osm data/osm/mi_ciudad.osm --name mi_ciudad --validate
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS COMUNES

### Error: "sumo no se reconoce como comando"
**Solución:** Agregar SUMO al PATH
```powershell
$env:Path += ";C:\Program Files (x86)\Eclipse\Sumo\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
```

### Error: "Could not connect to TraCI"
**Posibles causas:**
1. SUMO no está en PATH → Ver paso anterior
2. Puerto 8813 bloqueado → Usar otro puerto con `--port 8814`
3. Firewall de Windows → Permitir Python en firewall

### Error: "Archivo .net.xml no encontrado"
**Solución:** Ejecutar script de preparación
```powershell
python scripts/prepare_network.py --mode benchmark
```

### Error: "ModuleNotFoundError: No module named 'src.core'"
**Solución:** Reinstalar en modo editable
```powershell
pip uninstall tsc-framework
pip install -e .
```

---

## 📊 ESTRUCTURA DE ARCHIVOS CLAVE

```
tsc_framework/
├── config/
│   └── default_config.yaml       # Configuración maestra
├── src/
│   ├── core/
│   │   ├── tsc_env.py            # Entorno RL 34D
│   │   └── reward.py             # Función de recompensa
│   ├── probabilistic/
│   │   └── vine_generator.py     # Vine Copulas
│   └── agents/
│       └── ppo_agent.py          # Agente PPO
├── scripts/
│   ├── train.py                  # Entrenamiento
│   ├── evaluate.py               # Evaluación
│   ├── test_sumo_connection.py   # Test de conexión ⭐
│   └── generate_hangzhou_scenarios.py  # 100 escenarios
├── sumo_configs/
│   ├── networks/
│   │   └── hangzhou_4x4.net.xml  # Red benchmark
│   ├── routes/
│   │   └── hangzhou/
│   │       └── scenario_XXX_hangzhou.rou.xml  # 100 archivos
│   └── hangzhou.sumocfg          # Configuración SUMO
└── models/                       # Modelos guardados
```

---

## 📚 REFERENCIAS ACADÉMICAS

- **Capítulo 4.2.1**: Integración SUMO-TraCI
- **Capítulo 4.2.2**: Estado 34D (`s_t = [q, w, p, φ, τ]`)
- **Capítulo 4.3.2**: Función de recompensa multiobjetivo
- **Capítulo 4.4.1**: Benchmark Hangzhou 4×4
- **Capítulo 5.5**: Validación en redes OpenStreetMap

---

## 💡 CONSEJOS PARA VALIDACIÓN DOCTORAL

1. **Reproducibilidad**: Siempre usa `--seed 42` para experimentos comparables
2. **Domain Randomization**: Entrena con los 100 escenarios para robustez
3. **Baselines**: Compara siempre contra FixedTime y Actuated
4. **Métricas**: Reporta Delay, Gini, CVaRα, Throughput y Travel Time
5. **CPU-Only**: El framework fuerza CPU para inferencia consistente

---

**Última actualización**: Mayo 2024  
**Versión del framework**: 1.0.0 (Fase 0 completa)
