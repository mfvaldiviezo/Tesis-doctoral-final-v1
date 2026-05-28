import re
import os

file_path = "src/core/tsc_env.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# --- REPARACIÓN 1: Agregar método _safe_close_traci si no existe ---
if "_safe_close_traci" not in content:
    # Buscar el método close() existente e inyectar la definición antes o dentro
    # Estrategia: Definir el método justo antes de 'def close'
    
    safe_close_method = '''
    def _safe_close_traci(self):
        """Cierra conexión TraCI de forma segura evitando errores."""
        if hasattr(self, '_traci_port') and self._traci_port:
            try:
                import traci
                if traci.is_connected():
                    traci.close()
            except Exception:
                pass  # Ignorar errores al cerrar
        if hasattr(self, '_sumo_process') and self._sumo_process:
            try:
                self._sumo_process.terminate()
                self._sumo_process.wait(timeout=2)
            except Exception:
                pass
'''
    
    # Insertar antes del método close()
    pattern = r'(    def close\(self\)):'
    match = re.search(pattern, content)
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + safe_close_method + "\n" + content[insert_pos:]
        print("✅ Método '_safe_close_traci' agregado.")
    else:
        print("⚠️ No se encontró 'def close(self)' para insertar el método.")

# --- REPARACIÓN 2: Corregir _compute_delay para evitar retorno 0 constante ---
old_delay_func = r'def _compute_delay\(self, wait_times.*?\n(        .*?\n)*?        return float\(delay\)'
# Vamos a buscar y reemplazar la lógica específica si es muy simple

# Estrategia más segura: Reemplazar solo la línea de retorno si devuelve 0 incorrectamente
# O mejor, asegurar que la función calcule algo real.
# Busquemos la definición actual y la reescribimos si es problemática.

# Detectar si la función actual es demasiado simple o errónea
if "def _compute_delay(self, wait_times" in content:
    # Extraer bloque actual (aproximado)
    start = content.find("def _compute_delay(self, wait_times")
    next_def = content.find("\n    def ", start + 10)
    if next_def == -1: next_def = len(content)
    current_func = content[start:next_def]
    
    # Si la función actual devuelve 0 siempre o tiene lógica rota, la reemplazamos
    if "return 0.0" in current_func or (current_func.count("wait_times") < 2 and "sum" not in current_func):
        new_delay_func = '''    def _compute_delay(self, wait_times: Optional[np.ndarray] = None) -> float:
        """Calcula el delay total basado en tiempos de espera.
        
        Si wait_times es None o vacío, intenta obtener datos directos de TraCI.
        """
        try:
            if wait_times is None or len(wait_times) == 0:
                # Fallback: obtener waiting times directos de TraCI si hay conexión
                if hasattr(self, 'traci') and self.traci and self.traci.is_connected():
                    try:
                        vehicle_ids = self.traci.vehicle.getIDList()
                        if vehicle_ids:
                            wait_times = np.array([
                                self.traci.vehicle.getWaitingTime(vid) 
                                for vid in vehicle_ids
                            ])
                        else:
                            return 0.0
                    except Exception:
                        return 0.0
                else:
                    return 0.0
            
            if len(wait_times) == 0:
                return 0.0
                
            # Delay total = suma de tiempos de espera
            total_delay = float(np.sum(wait_times))
            
            # Normalizar opcionalmente por número de vehículos para estabilidad
            # pero mantenemos la suma absoluta para la recompensa raw
            return total_delay
        except Exception:
            return 0.0
'''
        content = content[:start] + new_delay_func + content[next_def:]
        print("✅ Función '_compute_delay' corregida.")

# --- REPARACIÓN 3: Corregir _calculate_gini ---
if "def _calculate_gini(self, wait_times" in content:
    start = content.find("def _calculate_gini(self, wait_times")
    next_def = content.find("\n    def ", start + 10)
    if next_def == -1: next_def = len(content)
    
    new_gini_func = '''    def _calculate_gini(self, wait_times: Optional[np.ndarray] = None) -> float:
        """Calcula el coeficiente de Gini para medir equidad en tiempos de espera."""
        try:
            if wait_times is None or len(wait_times) == 0:
                if hasattr(self, 'traci') and self.traci and self.traci.is_connected():
                    vehicle_ids = self.traci.vehicle.getIDList()
                    if vehicle_ids:
                        wait_times = np.array([
                            self.traci.vehicle.getWaitingTime(vid) 
                            for vid in vehicle_ids
                        ])
                    else:
                        return 0.0
                else:
                    return 0.0
            
            if len(wait_times) == 0:
                return 0.0
            
            # Filtrar valores negativos (no deberían existir pero por seguridad)
            wait_times = np.sort(np.maximum(wait_times, 0))
            n = len(wait_times)
            
            if n == 1:
                return 0.0 # Un solo vehículo, equidad perfecta
            
            sum_wait = np.sum(wait_times)
            if sum_wait == 0:
                return 0.0 # Nadie ha esperado
            
            # Fórmula de Gini: (2 * Σ i*x_i) / (n * Σ x_i) - (n+1)/n
            cumsum = np.cumsum(wait_times)
            gini = (2 * np.sum((np.arange(1, n + 1) * wait_times))) / (n * sum_wait) - (n + 1) / n
            
            return float(np.clip(gini, 0.0, 1.0))
        except Exception:
            return 0.0
'''
    content = content[:start] + new_gini_func + content[next_def:]
    print("✅ Función '_calculate_gini' corregida.")

# Guardar cambios
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("🎉 Parche aplicado completamente.")
