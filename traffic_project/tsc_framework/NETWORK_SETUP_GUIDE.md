# Guía de Configuración de Redes para tsc_framework

**Referencia Académica**: Capítulos 4.4.1 (Benchmark) y 5.5 (Validación OSM) de la Tesis Doctoral

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Modo Benchmark: Hangzhou 4×4](#modo-benchmark-hangzhou-4×4)
3. [Modo Custom: Importación desde OpenStreetMap](#modo-custom-importación-desde-openstreetmap)
4. [Solución de Problemas](#solución-de-problemas)
5. [Comandos Rápidos](#comandos-rápidos)

---

## 🎯 Visión General

El framework `tsc_framework` soporta **dos modos de operación** para simulación de tráfico:

| Modo | Propósito | Red | Uso Principal |
|------|-----------|-----|---------------|
| **BENCHMARK** | Comparativa con estado del arte (SOTA) | Hangzhou 4×4 grid | Validación reproducibilidad, comparación con papers |
| **CUSTOM** | Validación en contextos reales | Cualquier red OSM | Aplicación en ciudades latinoamericanas, casos reales |

### Arquitectura de Configuración

```yaml
network:
  mode: "benchmark"  # o "custom"
  
  benchmark:
    name: "hangzhou_4x4"
    network_file: "sumo_configs/networks/hangzhou_4x4.net.xml"
    route_files_dir: "sumo_configs/routes/hangzhou/"
    num_scenarios: 100  # Domain randomization
  
  custom:
    osm_file: "data/osm/mi_ciudad.osm"
    net_output: "sumo_configs/networks/mi_ciudad.net.xml"
    tls_mode: "actuated"
    projection: "EPSG:4326"
```

---

## 🔬 Modo Benchmark: Hangzhou 4×4

### Propósito Académico

**Capítulo 4.4.1**: El benchmark Hangzhou 4×4 es el estándar de facto en investigación de control semafórico con RL. Permite:

- ✅ Comparación directa con 50+ papers del estado del arte
- ✅ Validación de reproducibilidad experimental
- ✅ Domain randomization con 100 escenarios de demanda variable
- ✅ Aislamiento de variables en entorno controlado

### Características de la Red

| Parámetro | Valor |
|-----------|-------|
| Topología | Grid 4×4 intersecciones |
| Semáforos | 16 (IDs: J0, J1, ..., J15) |
| Longitud entre cruces | 500 metros |
| Carriles por dirección | 1-3 según configuración |
| Escenarios de ruta | 100 archivos `.rou.xml` |

### Pasos de Configuración

#### Paso 1: Verificar Instalación de SUMO

```bash
# Windows PowerShell
sumo --version

# Linux/Mac
sumo --version
which netgenerate
```

**Si no encuentra los comandos**:
- Windows: Instalar desde https://sumo.dlr.de/docs/Installing.html
- Linux: `sudo apt-get install sumo sumo-tools sumo-data`

#### Paso 2: Generar Red Hangzhou Automáticamente

```bash
cd C:\Proyecto_Tesis_Final_V1\traffic_project\tsc_framework

# Opción A: Usar script automático (recomendado)
python scripts/prepare_network.py --mode benchmark

# Opción B: Generar manualmente con netgenerate
netgenerate --grid --grid.number=4 --grid.length=500 \
  --tls.default-type=actuated \
  --junctions.uniform=true \
  --tls.all-off=false \
  --seed=42 \
  --output-file=sumo_configs/networks/hangzhou_4x4.net.xml
```

#### Paso 3: Generar Rutas para Domain Randomization

```bash
# El script prepare_network.py genera automáticamente 100 archivos
python scripts/prepare_network.py --mode benchmark

# Los archivos se guardan en:
# sumo_configs/routes/hangzhou/scenario_000_hangzhou.rou.xml
# sumo_configs/routes/hangzhou/scenario_001_hangzhou.rou.xml
# ...
# sumo_configs/routes/hangzhou/scenario_099_hangzhou.rou.xml
```

#### Paso 4: Validar Configuración

```bash
# Dry-run para verificar configuración
python scripts/prepare_network.py --mode benchmark --dry-run

# Debería mostrar:
# ✅ Configuración válida
#    Mode: benchmark
#    Network file: sumo_configs/networks/hangzhou_4x4.net.xml
#    Routes dir: sumo_configs/routes/hangzhou/
```

#### Paso 5: Ejecutar Entrenamiento de Prueba

```bash
# Entrenamiento mínimo (100 timesteps) para validación
python scripts/train.py --timesteps 100 --n-envs 1 --seed 42

# Salida esperada:
# ℹ️ Inicializando entorno Hangzhou 4×4
# ℹ️ Espacio de observación: (34,)
# ℹ️ Espacio de acción: Discrete(4)
# ✅ PPO inicializado correctamente
# ✅ Entrenamiento completado: 100/100 steps
```

### Configuración YAML para Benchmark

```yaml
# config/default_config.yaml
network:
  mode: "benchmark"
  
  benchmark:
    name: "hangzhou_4x4"
    tls_id: "J0"
    network_file: "sumo_configs/networks/hangzhou_4x4.net.xml"
    route_files_dir: "sumo_configs/routes/hangzhou/"
    num_scenarios: 100

sumo:
  sumo_home: ""  # Se usa $SUMO_HOME del sistema
  sumo_binary: "sumo"
  step_length: 5
```

---

## 🌍 Modo Custom: Importación desde OpenStreetMap

### Propósito Académico

**Capítulo 5.5**: Validación del framework en contextos urbanos reales, específicamente ciudades latinoamericanas con:

- ✅ Topologías irregulares (no grid)
- ✅ Intersecciones complejas (rotondas, múltiples carriles)
- ✅ Patrones de tráfico heterogéneos
- ✅ Restricciones geométricas reales

### Fuentes de Datos OSM Recomendadas

| Fuente | URL | Mejor Para | Tamaño Máximo |
|--------|-----|------------|---------------|
| **GeoFabrik** | https://download.geofabrik.de/ | Ciudades completas | Ilimitado |
| **BBBike** | https://extract.bbbike.org/ | Áreas personalizadas | ~50 MB |
| **OSM Direct** | https://www.openstreetmap.org/export | Zonas pequeñas (< 1 km²) | ~10 MB |

#### Ejemplo: Descargar Bogotá Centro

1. Ir a https://extract.bbbike.org/
2. Dibujar rectángulo sobre área de interés
3. Seleccionar formato "OSM XML"
4. Esperar email con link de descarga
5. Guardar en `data/osm/bogota_centro.osm`

### Pasos de Importación

#### Paso 1: Preparar Archivo OSM

```bash
# Crear directorio para datos OSM
mkdir data\osm

# Colocar archivo descargado en:
# data/osm/mi_ciudad.osm
```

#### Paso 2: Ejecutar Importación

```bash
# Importación básica (recomendado para primera vez)
python scripts/import_osm.py --osm data/osm/bogota_centro.osm --name bogota

# Con parámetros personalizados
python scripts/import_osm.py \
  --osm data/osm/medellin.osm \
  --name medellin \
  --tls-mode actuated \
  --projection EPSG:4326 \
  --generate-routes \
  --validate

# Dry-run para ver comando sin ejecutar
python scripts/import_osm.py --osm data/osm/city.osm --name city --dry-run
```

#### Paso 3: Verificar Salida

```bash
# Archivos generados:
ls sumo_configs/networks/bogota.net.xml
ls sumo_configs/routes/bogota_minimal.rou.xml

# Validar estructura
python -c "from pathlib import Path; p = Path('sumo_configs/networks/bogota.net.xml'); print(f'Tamaño: {p.stat().st_size / 1024:.1f} KB')"
```

#### Paso 4: Ajustar Rutas (Importante)

El archivo de rutas generado es un **template genérico** que requiere ajuste manual:

**Opción A: Usar NetEdit (Recomendado)**

```bash
# Abrir red en NetEdit
netedit sumo_configs/networks/bogota.net.xml

# Pasos en NetEdit:
# 1. File → Save additional files (genera .add.xml con detectores)
# 2. Edit → Select edges (identificar edges de entrada/salida)
# 3. Anotar IDs de edges principales
# 4. Editar manualmente bogota_minimal.rou.xml con los IDs correctos
```

**Opción B: Usar duarouter para rutas automáticas**

```bash
# Generar rutas basadas en demanda aleatoria
duarouter \
  --net-file sumo_configs/networks/bogota.net.xml \
  --route-files sumo_configs/routes/bogota_minimal.rou.xml \
  --output-file sumo_configs/routes/bogota_routes.rou.xml \
  --flows 500 \
  --random-trip-factor 0.8 \
  --begin 0 \
  --end 3600
```

#### Paso 5: Actualizar Configuración

```yaml
# config/default_config.yaml
network:
  mode: "custom"
  
  custom:
    osm_file: "data/osm/bogota_centro.osm"
    net_output: "sumo_configs/networks/bogota.net.xml"
    tls_mode: "actuated"
    projection: "EPSG:4326"
    route_file: "sumo_configs/routes/bogota_routes.rou.xml"
```

#### Paso 6: Validar Conexión

```bash
# Prueba de conexión TraCI
python scripts/import_osm.py \
  --osm data/osm/bogota_centro.osm \
  --name bogota \
  --validate

# Salida esperada:
# ✅ Conversión completada exitosamente
# ✅ Conexión TraCI exitosa
#    Paso actual: 0.0s
#    Vehículos cargados: 0
```

### Parámetros de Importación Avanzados

#### Tipos de Semáforos

| Modo | Descripción | Uso Recomendado |
|------|-------------|-----------------|
| `actuated` | Semáforos reactivos al tráfico | Ciudades grandes, avenidas principales |
| `static` | Tiempos fijos predefinidos | Centros históricos, zonas residenciales |
| `none` | Sin semáforos | Zonas rurales, validation de topología |

```bash
# Ejemplos por tipo
python scripts/import_osm.py --osm data/osm/area.osm --name area --tls-mode actuated
python scripts/import_osm.py --osm data/osm/centro.osm --name centro --tls-mode static
python scripts/import_osm.py --osm data/osm/rural.osm --name rural --tls-mode none
```

#### Proyecciones Geográficas

| Región | EPSG Code | Ejemplo |
|--------|-----------|---------|
| Global (GPS) | EPSG:4326 | Por defecto |
| Colombia | EPSG:3116 | MAGNA-SIRGAS |
| México | EPSG:6366 | ITRF2008 |
| Argentina | EPSG:5347 | POSGAR 2007 |
| Chile | EPSG:5359 | Chile Central |

```bash
# Ejemplo con proyección local
python scripts/import_osm.py \
  --osm data/osm/bogota.osm \
  --name bogota \
  --projection EPSG:3116
```

---

## 🛠️ Solución de Problemas

### Error: "netconvert no encontrado"

**Causa**: SUMO no está instalado o no está en el PATH

**Solución Windows**:
```powershell
# Verificar instalación
sumo --version

# Si no funciona, agregar al PATH manualmente
$env:PATH += ";C:\Program Files (x86)\Eclipse\Sumo\bin"

# Hacer permanente (PowerShell como administrador)
[Environment]::SetEnvironmentVariable(
  "Path", 
  $env:Path + ";C:\Program Files (x86)\Eclipse\Sumo\bin", 
  "Machine"
)
```

**Solución Linux**:
```bash
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-data
```

### Error: "Could not connect in 11 tries"

**Causa**: SUMO no inicia o puerto ocupado

**Soluciones**:
1. Verificar que `$SUMO_HOME` esté configurada:
   ```bash
   echo $SUMO_HOME  # Linux/Mac
   echo $env:SUMO_HOME  # Windows
   ```

2. Matar procesos SUMO zombis:
   ```bash
   taskkill /F /IM sumo.exe  # Windows
   killall sumo  # Linux/Mac
   ```

3. Usar puerto diferente:
   ```bash
   # El framework usa puertos aleatorios automáticamente
   # Pero puede forzar un puerto específico si hay conflictos
   ```

### Error: "No se detectaron semáforos"

**Causa**: La red OSM no tiene intersecciones semafóricas detectadas

**Soluciones**:
1. Forzar detección de semáforos:
   ```bash
   python scripts/import_osm.py \
     --osm data/osm/area.osm \
     --name area \
     --tls-mode static
   ```

2. Editar manualmente en NetEdit:
   ```bash
   netedit sumo_configs/networks/area.net.xml
   # Añadir semáforos manualmente en intersecciones clave
   ```

3. Usar red de ejemplo mientras tanto:
   ```bash
   python scripts/prepare_network.py --mode benchmark
   ```

### Error: "Archivo OSM muy grande"

**Causa**: Timeout de 5 minutos excedido

**Soluciones**:
1. Usar extracto más pequeño:
   - BBBike: limitar a ~10 km²
   - GeoFabrik: usar sub-regiones en lugar de países completos

2. Aumentar timeout (editar `scripts/import_osm.py`):
   ```python
   timeout=600  # 10 minutos en lugar de 5
   ```

3. Pre-procesar OSM con JOSM o QGIS para simplificar

### Error: "Rutas no compatibles con la red"

**Causa**: Edge IDs en `.rou.xml` no existen en `.net.xml`

**Solución**:
1. Identificar edges válidos:
   ```bash
   # Listar todos los edges
   python -c "
   import xml.etree.ElementTree as ET
   tree = ET.parse('sumo_configs/networks/bogota.net.xml')
   root = tree.getroot()
   edges = [e.attrib['id'] for e in root.findall('.//edge')]
   print('\n'.join(edges[:20]))  # Primeros 20 edges
   "
   ```

2. Regenerar rutas con duarouter:
   ```bash
   duarouter --net-file sumo_configs/networks/bogota.net.xml \
             --output-file sumo_configs/routes/bogota_fixed.rou.xml \
             --flows 300
   ```

3. Usar NetEdit para generar rutas visualmente

---

## ⚡ Comandos Rápidos

### Benchmark (Hangzhou)

```bash
# Generar red y rutas
python scripts/prepare_network.py --mode benchmark

# Entrenar (1000 timesteps)
python scripts/train.py --timesteps 1000 --n-envs 2

# Evaluar modelo
python scripts/evaluate.py --model outputs/models/ppo_final.zip
```

### Custom (OSM)

```bash
# Importar red desde OSM
python scripts/import_osm.py --osm data/osm/city.osm --name city --generate-routes

# Validar importación
python scripts/import_osm.py --osm data/osm/city.osm --name city --validate

# Entrenar con red custom
python scripts/train.py \
  --config config/default_config.yaml \
  --network.mode custom \
  --network.custom.osm_file data/osm/city.osm \
  --timesteps 1000
```

### Validación General

```bash
# Test de configuración
python scripts/prepare_network.py --mode benchmark --dry-run
python scripts/import_osm.py --osm data/osm/test.osm --name test --dry-run

# Test de conexión TraCI
python -c "
import traci
print('TraCI disponible:', traci is not None)
"

# Test de entorno RL
python -c "
from src.core.tsc_env import TSCEnv
env = TSCEnv()
obs, _ = env.reset()
assert obs.shape == (34,), f'Estado debe ser 34D, got {obs.shape}'
print('✅ Entorno RL validado: estado 34D')
"
```

---

## 📚 Referencias Académicas

1. **Capítulo 4.4.1**: Benchmark Hangzhou 4×4 para comparativa SOTA
2. **Capítulo 5.5**: Validación en redes reales desde OpenStreetMap
3. **Sección 3.2**: Pipeline de preprocesamiento de redes viales
4. **Apéndice A.2**: Configuración detallada de SUMO y TraCI

### Enlaces Externos

- Eclipse SUMO Documentation: https://sumo.dlr.de/docs/
- OpenStreetMap Wiki: https://wiki.openstreetmap.org/
- GeoFabrik Downloads: https://download.geofabrik.de/
- BBBike Extracts: https://extract.bbbike.org/

---

**Última actualización**: 2025
**Versión del framework**: 1.0.0 (Fase 5: Reproducibilidad)
