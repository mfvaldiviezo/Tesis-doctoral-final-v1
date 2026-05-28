# Auditoría Completa del Repositorio TSC Framework
## Fecha: 2024
## Estado: Análisis Exhaustivo

---

## 📋 RESUMEN EJECUTIVO

El repositorio `tsc_framework` es un framework computacional para una tesis doctoral sobre **Control Semafórico Inteligente** basado en:
- **Reinforcement Learning (PPO)** sensible al riesgo
- **Vine Copulas** para modelado probabilístico
- **Equidad distributiva** (Índice de Gini)
- **CVaR** (Conditional Value at Risk) para gestión de riesgos

### ✅ Puntos Fuertes Identificados

1. **Arquitectura bien estructurada**: Separación clara de responsabilidades (core, rl_agent, probabilistic, copulas, data_pipeline)
2. **Documentación académica**: Referencias explícitas a capítulos de tesis (Cap 4.2.2, 4.3.2, etc.)
3. **Espacio de estados 34D**: Implementación fiel a la especificación académica
4. **CPU-only forzado**: Garantiza reproducibilidad y evita problemas de GPU
5. **Tests unitarios robustos**: 79 tests passing, validan dimensionalidad, matemáticas de recompensa y aislamiento TraCI
6. **Configuración YAML centralizada**: Permite experimentación reproducible

### ⚠️ Problemas Críticos Detectados

#### 1. Inconsistencia en Tests (`test_sumo_env.py`)
**15 tests fallando** debido a:
- Uso de `env.n_lanes` cuando el atributo es `env._n_lanes` (privado)
- Referencia a clase antigua `SumoRLEnv` en lugar de `TSCEnv`
- Método `_calculate_cvar` con signature diferente al esperado por tests

**Archivos afectados:**
- `tests/test_sumo_env.py` (líneas 291, 296, 301, 313)

#### 2. Advertencia en Entrenamiento
```
UserWarning: The environment is already wrapped with a `Monitor` wrapper
but you are wrapping it with a `VecMonitor` wrapper
```
**Ubicación:** `scripts/train.py` línea 473
**Causa:** Doble envoltura con Monitor (make_env ya retorna Monitor + VecMonitor)

#### 3. Pesos de Recompensa No Normalizados
```
[WARNING] tsc.train — Los pesos de recompensa no suman 1 (Σ=0.950). Normalizando.
```
**Causa:** Configuración en `default_config.yaml` tiene pesos inconsistentes:
```yaml
reward_weights:
  queue_length: -0.4    # Negativo (debería ser positivo)
  avg_speed: 0.3
  wait_time: -0.2       # Negativo (debería ser positivo)
  throughput: 0.1
```

#### 4. Métodos Faltantes en TSCEnv
Los tests esperan métodos que no existen:
- `_compute_pressure_scalar()` → Solo existe `_get_pressure()` 
- `__repr__()` → No implementado
- `n_lanes` property → Solo existe `_n_lanes` (privado)

---

## 🔍 ANÁLISIS DETALLADO POR COMPONENTE

### 1. Core Environment (`src/core/tsc_env.py`)

#### ✅ Correcto:
- Espacio de observación: `Box(low=0, high=1, shape=(34,), dtype=np.float32)` ✓
- Espacio de acción: `Discrete(4)` ✓
- Device CPU forzado: `torch.device("cpu")` ✓
- UUID único por instancia para aislamiento en SubprocVecEnv ✓
- Puerto TraCI dinámico para múltiples entornos paralelos ✓

#### ⚠️ Mejoras Sugeridas:
```python
# Agregar property pública para n_lanes
@property
def n_lanes(self) -> int:
    """Número de carriles controlados (público para tests)."""
    return self._n_lanes

# Agregar __repr__ para debugging
def __repr__(self) -> str:
    return f"TSCEnv(tls_id={self.tls_id}, uuid={self._instance_uuid})"

# Agregar método _compute_pressure_scalar si es requerido
def _compute_pressure_scalar(self) -> float:
    """Retorna presión como escalar (suma de valores absolutos)."""
    pressure = self._get_pressure()
    return float(np.sum(np.abs(pressure)))
```

### 2. Script de Entrenamiento (`scripts/train.py`)

#### ✅ Correcto:
- Carga de configuración YAML flexible
- Factory pattern para entornos paralelos
- Callbacks personalizados para métricas de riesgo
- Guardado de checkpoints y mejor modelo

#### ⚠️ Problemas:
```python
# Línea 170-215: make_env retorna Monitor(env)
# Línea 473: Se vuelve a envolver con VecMonitor
vec_env = VecMonitor(vec_env, filename=str(MONITOR_DIR / "monitor"))
# ❌ Esto causa double-wrapping warning

# Solución: Remover Monitor de make_env o VecMonitor de línea 473
```

### 3. Configuración (`config/default_config.yaml`)

#### ⚠️ Inconsistencias:
```yaml
# Líneas 88-92: Pesos negativos y positivos mezclados
reward_weights:
  queue_length: -0.4    # Debería ser positivo (se penaliza en reward)
  avg_speed: 0.3        # OK
  wait_time: -0.2       # Debería ser positivo
  throughput: 0.1       # OK

# Líneas 136-141: Pesos de risk_metrics
risk_metrics:
  gini_weight: 0.1      # Muy bajo vs cvar_alpha: 0.95
  cvar_alpha: 0.95      # Esto es parámetro, no peso
```

#### ✅ Recomendación:
```yaml
environment:
  reward_weights:
    queue_length: 0.4   # Positivo, se negará en _calculate_reward
    avg_speed: 0.3
    wait_time: 0.2
    throughput: 0.1

risk_metrics:
  gini_weight: 0.15     # Peso real para Gini
  cvar_weight: 0.15     # Peso real para CVaR
  cvar_alpha: 0.95      # Parámetro de CVaR (cola 5%)
```

### 4. Tests Unitarios

#### ✅ Tests Passing (79/94):
- `test_env_34d.py`: 12/12 ✓ (Dimensionalidad, CPU-only, recompensas)
- `test_reward_math.py`: 24/24 ✓ (Gini, CVaR, propiedades matemáticas)
- `test_smoke.py`: 13/13 ✓ (Imports, estructura, config)
- `test_vine_samples.py`: 30/30 ✓ (Cópulas, escenarios de estrés)

#### ❌ Tests Falling (15/94):
- `test_sumo_env.py`: 15 fallando por APIs desactualizadas

---

## 📊 MÉTRICAS DE CALIDAD DEL CÓDIGO

| Métrica | Valor | Estado |
|---------|-------|--------|
| Tests Passing | 79/94 (84%) | ⚠️ Mejorable |
| Coverage Estimado | ~65% | ⚠️ Bajo |
| Documentación | Excelente | ✅ |
| Type Hints | Parcial | ⚠️ |
| Logging | Completo | ✅ |
| Error Handling | Adecuado | ✅ |

---

## 🔧 RECOMENDACIONES PRIORIZADAS

### Alta Prioridad (Crítico)

1. **Fix `test_sumo_env.py`**:
   - Cambiar `env.n_lanes` → `env._n_lanes` o agregar property pública
   - Actualizar referencia `SumoRLEnv` → `TSCEnv`
   - Ajustar signatures de métodos en tests

2. **Corregir doble Monitor wrapping**:
   ```python
   # Opción A: Remover Monitor de make_env
   def make_env(...) -> Callable[[], TSCEnv]:  # Sin Monitor
       def _thunk() -> TSCEnv:
           return TSCEnv(**env_config)
       return _thunk
   
   # Opción B: No usar VecMonitor si ya hay Monitor
   vec_env = VecEnvClass(env_factories)  # Sin VecMonitor
   ```

3. **Normalizar pesos de recompensa en YAML**:
   - Usar solo valores positivos
   - Asegurar que sumen 1.0

### Media Prioridad (Mejora)

4. **Agregar métodos faltantes a TSCEnv**:
   - `__repr__()` para debugging
   - `_compute_pressure_scalar()` si es necesario
   - Property `n_lanes` pública

5. **Mejorar type hints**:
   - Agregar tipos a todos los parámetros y retornos
   - Usar `typing.Optional`, `typing.List`, etc.

6. **Aumentar coverage de tests**:
   - Tests para `scripts/train.py`
   - Tests para callbacks personalizados
   - Integration tests con SUMO real (si es posible)

### Baja Prioridad (Nice-to-have)

7. **Agregar pre-commit hooks**:
   - Black para formato
   - Flake8 para linting
   - Mypy para type checking

8. **CI/CD Pipeline**:
   - GitHub Actions para tests automáticos
   - Validación de configs YAML

---

## 🎯 CONCLUSIÓN

El framework está **funcionalmente operativo** como demuestra el log de entrenamiento exitoso:
```
✅ Modelo final guardado en: outputs/models/ppo_final.zip
```

Sin embargo, requiere **mantenimiento de tests** y **normalización de configuración** para garantizar calidad académica y reproducibilidad a largo plazo.

**Estado General:** ✅ **OPERATIVO** con mejoras recomendadas

---

## 📝 ARCHIVOS AUDITADOS

| Archivo | Líneas | Estado | Notas |
|---------|--------|--------|-------|
| `src/core/tsc_env.py` | 1004 | ✅ | Core sólido, faltan métodos menores |
| `scripts/train.py` | 585 | ⚠️ | Double Monitor wrapping |
| `config/default_config.yaml` | 186 | ⚠️ | Pesos inconsistentes |
| `tests/test_env_34d.py` | 270 | ✅ | 12/12 passing |
| `tests/test_reward_math.py` | 350+ | ✅ | 24/24 passing |
| `tests/test_sumo_env.py` | 315 | ❌ | 15 failing, necesita update |
| `tests/test_smoke.py` | 150+ | ✅ | 13/13 passing |
| `tests/test_vine_samples.py` | 400+ | ✅ | 30/30 passing |

---

*Generado automáticamente como parte de la auditoría del repositorio*
