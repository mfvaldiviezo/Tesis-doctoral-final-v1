import re

FILE_PATH = "src/core/tsc_env.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Detectar inicio de _compute_delay
    if 'def _compute_delay(self' in line:
        # Saltar hasta encontrar el siguiente 'def' o fin de la función (indentación correcta)
        new_lines.append(line) # Mantener signature
        # Buscar el cuerpo y reemplazarlo
        # Estrategia simple: insertar nuevo cuerpo y saltar el viejo
        indent = '        ' # Asumiendo indentación estándar de 8 espacios
        
        # Nuevo cuerpo
        body = [
            '        """Delay agregado robusto."""\n',
            '        if wait_times is None or len(wait_times) == 0:\n',
            '            return 0.0\n',
            '        wt = np.array(wait_times)\n',
            '        wt = wt[wt >= 0]\n',
            '        return float(np.sum(wt)) if len(wt) > 0 else 0.0\n',
            '\n'
        ]
        new_lines.extend(body)
        
        # Saltar líneas antiguas hasta el siguiente def o clase
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.strip().startswith('def ') and not next_line.strip().startswith('def _'): # Siguiente método público? No, cualquier def
                 # Cuidado con métodos privados siguientes
                 if next_line.startswith('    def '): # Mismo nivel de indentación de clase
                    break
            i += 1
        continue # Continuar bucle principal sin añadir la línea actual procesada

    # Detectar inicio de _calculate_gini
    elif 'def _calculate_gini(self' in line:
        new_lines.append(line)
        body = [
            '        """Gini robusto."""\n',
            '        if wait_times is None or len(wait_times) == 0:\n',
            '            return 0.0\n',
            '        wt = np.array(wait_times)\n',
            '        wt = wt[wt >= 0]\n',
            '        n = len(wt)\n',
            '        if n <= 1: return 0.0\n',
            '        mean_wait = np.mean(wt)\n',
            '        if mean_wait == 0: return 0.0\n',
            '        sorted_wt = np.sort(wt)\n',
            '        index = np.arange(1, n + 1)\n',
            '        num = 2 * np.sum(index * sorted_wt)\n',
            '        den = n * np.sum(sorted_wt)\n',
            '        if den == 0: return 0.0\n',
            '        gini = (num / den) - (n + 1) / n\n',
            '        return float(np.clip(gini, 0.0, 1.0))\n',
            '\n'
        ]
        new_lines.extend(body)
        
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.startswith('    def '): 
                break
            i += 1
        continue

    else:
        new_lines.append(line)
        i += 1

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Funciones de métricas parcheadas correctamente.")
