import re

file_path = "src/core/tsc_env.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_functions = '''
    def _compute_delay(self, wait_times: Optional[np.ndarray] = None) -> float:
        """Calcula el delay total basado en tiempos de espera."""
        if wait_times is None or len(wait_times) == 0:
            return 0.0
        total_delay = float(np.sum(wait_times))
        return total_delay

    def _calculate_gini(self, wait_times: Optional[np.ndarray] = None) -> float:
        """Calcula el coeficiente de Gini para los tiempos de espera."""
        if wait_times is None or len(wait_times) == 0:
            return 0.0
        
        v = np.sort(wait_times)
        n = len(v)
        if n == 0:
            return 0.0
            
        mean_wait = np.mean(v)
        if mean_wait == 0:
            return 0.0
            
        diff_sum = np.sum(np.abs(v[:, None] - v[None, :]))
        gini = diff_sum / (2.0 * n * n * mean_wait)
        
        return float(np.clip(gini, 0.0, 1.0))

    def _calculate_cvar(self, losses: np.ndarray, alpha: float = 0.95) -> float:
        """Calcula el CVaR (Conditional Value at Risk) de las pérdidas."""
        if losses is None or len(losses) == 0:
            return 0.0
        
        arr = np.array(losses)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            return 0.0
            
        q = np.quantile(arr, alpha)
        tail = arr[arr >= q]
        
        if len(tail) == 0:
            return float(q)
            
        return float(np.mean(tail))
'''

pattern = r'(\n    def _compute_delay\(self.*?)(?=\n    def _|\n\Z)'

if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_functions, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Funciones de metricas corregidas exitosamente.")
else:
    print("No se encontro la funcion _compute_delay para reemplazar.")
