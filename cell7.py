# cell7.py -- Replica Paper Compacta v7 (Optimized: Reduced M + Hard Phys Constraints)
import data
import pulp
import math
import pandas as pd
from collections import defaultdict
import shutil

def run():
    print("=== CELDA 7: CONSTRUCCIÓN MODELO (OPTIMIZADO: HARD PHYS + LOW M) ===")
    
    params = data.shared['params']
    batches = data.shared['df_batches'].to_dict("records")
    trucks = data.shared['df_trucks'].to_dict("records")
    units = data.shared['df_units'].to_dict("records")
    sites_df = data.shared['df_sites']
    sites_map = {str(row['site_id']).strip().lower(): row for row in sites_df.to_dict("records")}

    T1, T2 = params["T1"], params["T2"]
    delta = params.get("delta_min", 10)
    time_points = list(range(T1, T2 + 1, delta))
    
    wash = params.get("wash_time", 10)
    unload = params.get("unload_time", 30)
    wait = params.get("wait_before_departure", 0)
    max_tardiness = params.get("max_tardiness_allowed", 120)
    setting_time_limit = params.get("setting_time", 90)
    max_lag = 60 

    def get_minutes(val):
        if val is None or pd.isna(val): return T1
        s_val = str(val).strip()
        if ":" in s_val:
            try:
                hh, mm = s_val.split(":")
                return int(hh) * 60 + int(mm)
            except: pass
        try:
            f_val = float(s_val)
            return int(f_val * 60) if f_val <= 24.0 else int(f_val)
        except: return T1

    prob = pulp.LpProblem("RMC_Robust_Optimization", pulp.LpMinimize)
    
    X, Y, T_tard, V_used = {}, {}, {}, {}
    
    # --- OPTIMIZACIÓN: Solo mantenemos Slacks para calidad/tardanza, no para física ---
    Slacks_Setting = {}     # Calidad (Fraguado) - Se mantiene Soft
    Slacks_Lag = {}         # Calidad (Junta fría) - Se mantiene Soft
    Slacks_MaxTard = {}     # Límite Tardanza - Se mantiene Soft
    # Slacks_Sync y Slacks_Seq eliminados (ahora son restricciones duras)
    
    X_sums = defaultdict(list)
    Y_sums = defaultdict(list)
    Y_by_v = defaultdict(list)

    print(f"Generando variables para {len(batches)} lotes...")

    for b_idx, batch in enumerate(batches):
        site_id = str(batch["site_id"]).strip().lower()
        site_data = sites_map.get(site_id, {})
        vol = float(batch.get("volume", 0))
        
        tw_start = get_minutes(site_data.get("tw_start_h"))
        tw_end = get_minutes(site_data.get("tw_end_h"))
        travel = float(site_data.get("travel_time_min", 0))
        
        T_tard[b_idx] = pulp.LpVariable(f"T_tard_b{b_idx}", lowBound=0) 
        
        Slacks_Setting[b_idx] = pulp.LpVariable(f"Slack_Setting_b{b_idx}", lowBound=0)
        Slacks_MaxTard[b_idx] = pulp.LpVariable(f"Slack_MaxTard_b{b_idx}", lowBound=0)

        latest_prod = T2 
        earliest_dep, latest_dep = T1, T2
        
        # X Vars (Producción)
        for u_idx, unit in enumerate(units):
            proc = float(unit.get("process_time_min", 0))
            for t in time_points:
                if t + proc <= latest_prod:
                    var = pulp.LpVariable(f"X_b{b_idx}_u{u_idx}_t{t}", cat="Binary")
                    X[(b_idx, u_idx, t)] = var
                    X_sums[b_idx].append((var, t, proc))

        # Y Vars (Transporte)
        count_y = 0
        for v_idx, truck in enumerate(trucks):
            cap = float(truck.get("capacity_m3", 0))
            if cap >= vol:
                for t in time_points:
                    if earliest_dep <= t <= latest_dep:
                        var = pulp.LpVariable(f"Y_b{b_idx}_v{v_idx}_t{t}", cat="Binary")
                        Y[(b_idx, v_idx, t)] = var
                        Y_sums[b_idx].append((var, t, v_idx))
                        Y_by_v[v_idx].append(var)
                        count_y += 1
        
        if count_y == 0: # Safety Net
             v_max = max(range(len(trucks)), key=lambda i: float(trucks[i]["capacity_m3"]))
             var = pulp.LpVariable(f"Y_b{b_idx}_v{v_max}_t{T1}", cat="Binary")
             Y[(b_idx, v_max, T1)] = var
             Y_sums[b_idx].append((var, T1, v_max))
             Y_by_v[v_max].append(var)

    for v_idx in range(len(trucks)):
        V_used[v_idx] = pulp.LpVariable(f"V_used_v{v_idx}", cat="Binary")

    print("Agregando restricciones (Hard Constraints aplicadas)...")
    
    for b in range(len(batches)):
        prob += pulp.lpSum([x[0] for x in X_sums[b]]) == 1, f"One_Prod_b{b}"
        prob += pulp.lpSum([y[0] for y in Y_sums[b]]) == 1, f"One_Trip_b{b}"

        finish_prod = pulp.lpSum([(t + proc) * xvar for (xvar, t, proc) in X_sums[b]])
        depart_truck = pulp.lpSum([t * yvar for (yvar, t, _) in Y_sums[b]])
        
        # --- Eq 7: Sincronización Carga ---
        prob += finish_prod + wash + wait <= depart_truck, f"Eq7_Sync_b{b}"
        
        # --- Eq 8: Vida útil (Setting Time)
        site_id = str(batches[b]["site_id"]).strip().lower()
        travel = float(sites_map.get(site_id, {}).get("travel_time_min", 0))
        arrival_finish = depart_truck + travel + unload
        prob += arrival_finish - finish_prod <= setting_time_limit + Slacks_Setting[b], f"Eq8_ShelfLife_b{b}"

        # Tardanza Def
        tw_end = get_minutes(sites_map.get(site_id, {}).get("tw_end_h"))
        prob += T_tard[b] >= (depart_truck + travel + unload) - tw_end, f"Def_Tard_b{b}"
        
        # Límite Tardanza
        prob += T_tard[b] <= max_tardiness + Slacks_MaxTard[b], f"Limit_Tard_b{b}"

    # Capacidad Unidades
    unit_occupancy = defaultdict(list)
    for (b, u, t), var in X.items():
        proc = float(units[u]["process_time_min"])
        for k in range(int(math.ceil(proc / delta))):
            if t + k*delta <= T2: unit_occupancy[(u, t + k*delta)].append(var)
    for k, vlist in unit_occupancy.items(): prob += pulp.lpSum(vlist) <= 1, f"Cap_Unit_{k}"

    # Capacidad Camiones
    truck_occupancy = defaultdict(list)
    for (b, v, t), var in Y.items():
        site_id = str(batches[b]["site_id"]).strip().lower()
        travel = float(sites_map.get(site_id, {}).get("travel_time_min", 0))
        trip_len = travel + unload + travel
        for k in range(-int(math.ceil(wash/delta)), int(math.ceil(trip_len/delta))):
            if T1 <= t + k*delta <= T2: truck_occupancy[(v, t + k*delta)].append(var)
    for k, vlist in truck_occupancy.items(): prob += pulp.lpSum(vlist) <= 1, f"Cap_Truck_{k}"

    # Secuencia
    batches_by_site = defaultdict(list)
    for i, b in enumerate(batches): batches_by_site[str(b["site_id"]).strip().lower()].append(i)
    
    for site, b_indices in batches_by_site.items():
        for i in range(len(b_indices) - 1):
            b_curr, b_next = b_indices[i], b_indices[i+1]
            travel = float(sites_map.get(site, {}).get("travel_time_min", 0))
            
            dep_curr = pulp.lpSum([t * y for (y, t, _) in Y_sums[b_curr]])
            dep_next = pulp.lpSum([t * y for (y, t, _) in Y_sums[b_next]])
            
            finish_curr = dep_curr + travel + unload
            start_next = dep_next + travel
            
            s_name_lag = f"Slack_Lag_{site}_{i}"
            Slacks_Lag[(site, i)] = pulp.LpVariable(s_name_lag, lowBound=0)
            
            # --- Eq 13 (HARD): Secuencia Lógica ---
            # Eliminado Slack: El siguiente no puede empezar antes que el actual termine.
            prob += start_next >= finish_curr, f"Eq13_Seq_{site}_{i}"
            
            # Eq 14 (SOFT): Lag Máximo (Juntas frías)
            prob += start_next - finish_curr <= max_lag + Slacks_Lag[(site, i)], f"Eq14_Lag_{site}_{i}"

    alpha = params.get("alpha", 1.0)
    beta = params.get("beta", 1.0)
    
    # === OPCIÓN A: AJUSTE DE PENALIZACIÓN ===
    # Reducido de 1,000,000 a 10,000 para estabilidad numérica en el solver.
    PENALTY = 1000  
    
    transp_cost = 0
    for (b, v, t), var in Y.items():
        site_id = str(batches[b]["site_id"]).strip().lower()
        dist = float(sites_map.get(site_id, {}).get("dist_km", 0))
        cost = float(trucks[v].get("var_cost_per_km", 0))
        transp_cost += var * (2 * dist * cost)

    fixed_costs = pulp.lpSum([V_used[v] * float(trucks[v].get("fixed_cost", 0)) for v in range(len(trucks))])

    # Suma de Slacks restantes (Solo Setting, Lag y MaxTard)
    slack_cost = PENALTY * (
        pulp.lpSum(Slacks_Setting.values()) + 
        pulp.lpSum(Slacks_Lag.values()) +
        pulp.lpSum(Slacks_MaxTard.values())
    )
    
    prob += alpha * (transp_cost + fixed_costs) + beta * pulp.lpSum(T_tard.values()) + slack_cost

    data.shared['prob'] = prob
    data.shared['X'] = X
    data.shared['Y'] = Y
    data.shared['T_tard'] = T_tard
    data.shared['V_used'] = V_used
    data.shared['units_list'] = units
    data.shared['batches_list'] = batches
    data.shared['trucks_list'] = trucks
    data.shared['site_map'] = sites_map
    data.shared["time_points"] = time_points
    
    print("Modelo Optimizado Guardado (M=10k, HardSync, HardSeq).")