# cell8_repair_v4.py -- Heurística Robusta Final (Cleaned for Hard Constraints)
from src import context as data
import pulp
from copy import deepcopy
from collections import defaultdict
import shutil
import math

def run():
    print("\n=== CELDA 8 (Repair v4 - Cleaned): Inicio ===")

    try:
        X = data.shared['X']
        Y = data.shared['Y']
        T_tard_vars = data.shared['T_tard']
        V_used_vars = data.shared['V_used']
        prob = data.shared['prob']
        # Recuperamos solo las variables que realmente existen en el modelo
        slacks_map = {v.name: v for v in prob.variables() if "Slack" in v.name}
    except Exception as e:
        print(f"Error recuperando variables: {e}")
        return

    units_list = data.shared['units_list']
    batches_list = data.shared['batches_list']
    trucks_list = data.shared['trucks_list']
    site_map = data.shared['site_map']
    params = data.shared['params']

    print(f"Variables recuperadas: {len(batches_list)} lotes.")

    U = len(units_list)
    V_count = len(trucks_list)
    B = len(batches_list)
    
    proc_by_ui = {ui: int(units_list[ui].get("process_time_min", 0)) for ui in range(U)}
    wash = params.get("wash_time", 0)
    wait = params.get("wait_before_departure", 0)
    unload_time = params.get("unload_time", 20) 
    max_tardiness = params.get("max_tardiness_allowed", 120) 
    max_time_lag = 60 
    T1 = params.get("T1", 420)
    T2 = params.get("T2", 1020)
    
    X_by_b = defaultdict(list)
    for (b,u,t) in X.keys(): X_by_b[b].append((u,t))
    for b in X_by_b: X_by_b[b].sort(key=lambda x: x[1])

    Y_by_b = defaultdict(list)
    for (b,v,t) in Y.keys(): Y_by_b[b].append((v,t))
    for b in Y_by_b: Y_by_b[b].sort(key=lambda x: x[1])

    batch_info = {}
    for b_idx, b_data in enumerate(batches_list):
        site_id = str(b_data["site_id"]).strip().lower()
        site_data = site_map.get(site_id, {})
        
        # Parser HH:MM
        raw_end = site_data.get("tw_end_h", T2/60)
        tw_end = T2
        s_val = str(raw_end).strip()
        if ":" in s_val:
            try:
                hh, mm = s_val.split(":")
                tw_end = int(hh) * 60 + int(mm)
            except: pass
        else:
            try:
                f_val = float(s_val)
                tw_end = int(f_val * 60) if f_val <= 24.0 else int(f_val)
            except: pass
        
        ctype = str(site_data.get("concrete_type", "p6")).strip().lower()
        st_map = {"p1":108, "p2":108, "p3":114, "p4":114, "p5":114, "p6":90, "p7":108, "p8":126}
        
        batch_info[b_idx] = {
            "site_id": site_id,
            "travel": float(site_data.get("travel_time_min", 0)),
            "tw_end": tw_end,
            "setting_time": st_map.get(ctype, 90)
        }

    batches_order = sorted(list(range(B)), key=lambda b: batch_info[b]["tw_end"])

    unit_next_free = {ui: T1 for ui in range(U)}
    site_last_unload = defaultdict(int) 
    truck_busy_until = {v: T1 for v in range(V_count)} 
    
    chosen_X = {}
    chosen_Y = {}

    print("Construyendo solución factible (Heurística)...")

    for b in batches_order:
        # A. Producción
        best_x = None
        candidates_x = X_by_b.get(b, [])
        if not candidates_x: continue 

        for (ui, t) in candidates_x:
            if t >= unit_next_free[ui]:
                best_x = (b, ui, t)
                break
        if not best_x: 
             (panic_u, panic_t) = candidates_x[-1]
             best_x = (b, panic_u, panic_t)
        
        (bx, ux, tx) = best_x
        prod_finish = tx + proc_by_ui[ux]
        
        # B. Transporte
        info = batch_info[b]
        travel = info["travel"]
        prev_finish = site_last_unload[info["site_id"]]
        
        # Restricciones lógicas para la heurística:
        min_dep_seq = prev_finish - travel 
        min_dep_prod = prod_finish + wash + wait
        min_dep = max(min_dep_prod, min_dep_seq)
        
        candidates_y = Y_by_b.get(b, [])
        best_y = None
        
        for (v, t) in candidates_y:
            if t >= min_dep:
                if t - wash >= truck_busy_until[v]:
                    best_y = (b, v, t)
                    break
        
        # Fallback si no encontramos hueco perfecto
        if not best_y and candidates_y:
            for (v, t) in candidates_y:
                if t >= min_dep_prod: 
                      best_y = (b, v, t)
                      break
        if not best_y and candidates_y:
             (panic_v, panic_t) = candidates_y[-1]
             best_y = (b, panic_v, panic_t)

        if best_y:
            chosen_X[b] = best_x
            chosen_Y[b] = best_y
            
            unit_next_free[ux] = max(unit_next_free[ux], prod_finish)
            (_, vy, ty) = best_y
            trip_end = ty + travel + unload_time + travel
            truck_busy_until[vy] = max(truck_busy_until[vy], trip_end)
            this_unload_finish = ty + travel + unload_time
            site_last_unload[info["site_id"]] = max(site_last_unload[info["site_id"]], this_unload_finish)

    print(f"Heurística completada. Lotes asignados: {len(chosen_X)}/{B}")

    # 4. Inyectar Solución
    print("Inyectando Warm Start (Solo variables activas)...")

    for (b, u, t), var in X.items():
        var.setInitialValue(1.0 if chosen_X.get(b) == (b, u, t) else 0.0)
        
    used_trucks_indices = set()
    for (b, v, t), var in Y.items():
        val = 1.0 if chosen_Y.get(b) == (b, v, t) else 0.0
        var.setInitialValue(val)
        if val > 0.5: used_trucks_indices.add(v)

    for v, var in V_used_vars.items():
        var.setInitialValue(1.0 if v in used_trucks_indices else 0.0)

    # Calculamos Slacks solo para lo que sigue siendo Soft
    batches_by_site = defaultdict(list)
    for b in range(B):
        if b in chosen_Y:
            site_id = batch_info[b]["site_id"]
            batches_by_site[site_id].append(b)
    
    for b in range(B):
        if b not in chosen_Y: continue
        
        (_, _, ty) = chosen_Y[b]
        (_, _, tx) = chosen_X[b]
        info = batch_info[b]
        
        arrival = ty + info["travel"]
        arrival_finish = arrival + unload_time
        (_, ux, _) = chosen_X[b]
        prod_finish = tx + proc_by_ui[ux]

        tard = max(0, arrival - info["tw_end"])
        if b in T_tard_vars: T_tard_vars[b].setInitialValue(tard)
        
        # Slack Max Tardiness (Soft)
        violation_tard = tard - max_tardiness
        slack_tard = max(0, violation_tard + 10)
        s_name_tard = f"Slack_MaxTard_b{b}"
        if s_name_tard in slacks_map: slacks_map[s_name_tard].setInitialValue(slack_tard)

        # Slack Setting Time (Soft)
        violation = (arrival_finish - prod_finish) - info["setting_time"]
        slack_val = max(0, violation + 10) 
        s_name = f"Slack_Setting_b{b}"
        if s_name in slacks_map: slacks_map[s_name].setInitialValue(slack_val)
        
        # Slack Sync: ELIMINADO (Ahora es Hard Constraint)
        # Si la heurística violó esto, HiGHS descartará el warm start, pero no crashea.

    # Slacks Secuencia
    for site, b_list in batches_by_site.items():
        b_list.sort()
        for i in range(len(b_list) - 1):
            b_curr = b_list[i]
            b_next = b_list[i+1]
            
            (_, _, ty_c) = chosen_Y[b_curr]
            finish_curr = ty_c + batch_info[b_curr]["travel"] + unload_time
            (_, _, ty_n) = chosen_Y[b_next]
            start_next = ty_n + batch_info[b_next]["travel"]
            
            # Slack Seq: ELIMINADO (Ahora es Hard Constraint)
            
            # Slack Lag (Juntas frías) - Sigue siendo Soft
            gap = start_next - finish_curr
            violation_lag = gap - max_time_lag
            s_lag = max(0, violation_lag + 10)
            s_name_lag = f"Slack_Lag_{site}_{i}"
            if s_name_lag in slacks_map: slacks_map[s_name_lag].setInitialValue(s_lag)

    print("=== CELDA 8: Fin (Solución limpia inyectada) ===\n")