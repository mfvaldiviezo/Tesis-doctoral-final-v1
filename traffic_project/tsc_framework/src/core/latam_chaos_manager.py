import logging
import traci
import math

logger = logging.getLogger(__name__)

class LatamChaosManager:
    """
    Gestor dinámico de comportamientos LATAM vía TraCI.
    Se invoca en cada simulationStep para aplicar lógica reactiva.
    """
    def __init__(self, tls_id="B1", probabilidad_caos=0.3):
        self.tls_id = tls_id
        self.probabilidad_caos = probabilidad_caos
        self.police_affected_vehicles = {}
        self.assigned_vehicles = set()
        self.latam_types = {}
        
    def step(self):
        try:
            import random
            # 1. Recuperar todos los vehículos y peatones en este step
            veh_ids = traci.vehicle.getIDList()
            ped_ids = traci.person.getIDList()
            
            # Pre-calcular posiciones si hay peatones para evitar dobles bucles costosos
            ped_positions = []
            if ped_ids:
                for p_id in ped_ids:
                    try:
                        pos = traci.person.getPosition(p_id)
                        ped_positions.append((p_id, pos))
                    except traci.exceptions.TraCIException:
                        pass

            for v_id in veh_ids:
                # 0. Asignación Dinámica de Tipos LATAM (al aparecer)
                if v_id not in self.assigned_vehicles:
                    self.assigned_vehicles.add(v_id)
                    if random.random() < self.probabilidad_caos:
                        try:
                            # 50% imprudente, 50% micro_imprudent
                            new_type = "micro_imprudent" if random.random() < 0.5 else "imprudent"
                            self.latam_types[v_id] = new_type
                            # Imprudentes aceleran más, ignoran distancia de seguridad y son agresivos
                            traci.vehicle.setTau(v_id, 0.5) # Muy pegados
                            traci.vehicle.setSpeedFactor(v_id, random.uniform(1.2, 1.8)) # Exceso de velocidad
                            traci.vehicle.setImperfection(v_id, 0.9) # Conductores distraídos/erráticos
                            traci.vehicle.setColor(v_id, (255, 0, 0)) # Rojo para visualizar el caos en la GUI
                        except traci.exceptions.TraCIException:
                            pass
                
                v_type = self.latam_types.get(v_id, "")
                if not v_type:
                    try:
                        v_type = traci.vehicle.getTypeID(v_id)
                    except traci.exceptions.TraCIException:
                        v_type = ""
                
                
                # A. MICROS: Paradas oportunistas si hay peatones cerca
                if "micro_imprudent" in v_type and ped_positions:
                    v_pos = traci.vehicle.getPosition(v_id)
                    # Buscar si hay un peatón a menos de 5 metros
                    for p_id, p_pos in ped_positions:
                        dist = math.hypot(v_pos[0] - p_pos[0], v_pos[1] - p_pos[1])
                        if dist < 5.0:
                            # Frenado repentino fingiendo recoger pasajero (speed 0 por un par de steps)
                            traci.vehicle.setSpeed(v_id, 0.0)
                            # Parar una vez es suficiente, romper
                            break
                            
                # B. GRIDLOCK EGOÍSTA Y BLOQUEO DE INTERSECCIÓN
                if "imprudent" in v_type:
                    try:
                        edge = traci.vehicle.getRoadID(v_id)
                        # 1. Si está DENTRO de un cruce (internal edge) hay un 5% de probabilidad 
                        # por segundo de que se quede "trabado" (bloqueando el flujo transversal)
                        if edge.startswith(":") and random.random() < 0.05:
                            traci.vehicle.setSpeed(v_id, 0.0)
                            traci.vehicle.setColor(v_id, (255, 165, 0)) # Naranja: Bloqueando cruce

                        # 2. Si se acerca a cualquier semáforo (no solo B1)
                        tls_links = traci.vehicle.getNextTLS(v_id)
                        if tls_links:
                            tls_id, tls_link_idx, dist, state = tls_links[0]
                            # Si está a menos de 20m y la luz está amarilla o roja, acelera para "ganarle" al semáforo
                            if state.lower() in ['y', 'r'] and dist < 20.0:
                                traci.vehicle.setSpeedFactor(v_id, 2.0)
                    except traci.exceptions.TraCIException:
                        pass

            # C. EFECTO ARRASTRE PEATONAL
            # Si un peatón está cruzando (en la calle) subir la velocidad de los demás
            crossing_peds = []
            for p_id, p_pos in ped_positions:
                edge = traci.person.getRoadID(p_id)
                # Si el edge no contiene vereda ni es un paso de cebra normal (es la calle)
                if not edge.startswith(":") and not "footway" in edge:
                    crossing_peds.append((p_id, p_pos))
                    
            if crossing_peds:
                for p_id, p_pos in ped_positions:
                    # Si no está ya cruzando agresivamente
                    for cross_id, cross_pos in crossing_peds:
                        if p_id != cross_id:
                            dist = math.hypot(p_pos[0] - cross_pos[0], p_pos[1] - cross_pos[1])
                            if dist < 10.0:
                                # Efecto arrastre: correr a 2x
                                try:
                                    traci.person.setSpeed(p_id, 2.5) # Corriendo
                                except traci.exceptions.TraCIException:
                                    pass

            # D. PRESENCIA POLICIAL
            # Revisar los detectores police_
            loop_ids = traci.inductionloop.getIDList()
            police_loops = [l for l in loop_ids if "police_" in l]
            for loop in police_loops:
                veh_data = traci.inductionloop.getVehicleData(loop)
                for v in veh_data:
                    v_id = v[0]
                    if v_id not in self.police_affected_vehicles:
                        # Guardar estado original no es estrictamente necesario, 
                        # solo le clavamos parámetros prudentes
                        try:
                            traci.vehicle.setTau(v_id, 1.5)
                            traci.vehicle.setSpeedFactor(v_id, 0.9)
                            traci.vehicle.setColor(v_id, (0, 0, 255)) # Se pone azul de "buen comportamiento"
                            self.police_affected_vehicles[v_id] = True
                        except traci.exceptions.TraCIException:
                            pass
                            
        except traci.exceptions.FatalTraCIError:
            pass
        except Exception as e:
            logger.error(f"Error en Chaos Manager: {e}")
