# cell10_checker.py  -- comprobaciones exhaustivas de factibilidad y reporte
# (Versión actualizada para incluir Eq. 8, 13, 14 y Setting Time por tipo)

from src import context as data
import pandas as pd


# ================================================================
# Utilidades robustas
# ================================================================
def safe_val(v):
    """Convierte None o valores no numéricos a 0.0."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except:
        return 0.0


def time_to_minutes(x):
    """
    Convierte:
    - '9:00'  -> 540
    - '14:30' -> 870
    - '8'     -> 480 (asume 8 horas)
    - 8.0     -> 480
    - 480     -> 480 (ya está en minutos)
    - 480.0   -> 480
    """
    if isinstance(x, (int, float)):
        return int(float(x) * 60) if float(x) < 60 else int(x)

    x = str(x).strip()

    if ":" in x:
        h, m = x.split(":")
        return int(h) * 60 + int(m)

    # Caso: valor numérico expresado como texto
    try:
        val = float(x)
        return int(val * 60) if val < 60 else int(val)
    except ValueError:
        print(f"ADVERTENCIA: No se pudo convertir a tiempo: {x}")
        return 0


# ================================================================
# CHECKER PRINCIPAL
# ================================================================
def run():
    print("\n========== CELDA 10: CHECKER DE FACTIBILIDAD ==========")

    # 1. Inicialización segura (Evita UnboundLocalError)
    X_sol = []
    Y_sol = []
    Vused_sol = {}
    Tt_sol = {}
    
    # Variables externas
    X, Y, T_tard, V_used = {}, {}, {}, {}
    units_list, batches, trucks = [], [], []
    site_map, params = {}, {}

    # 2. Recuperación de datos
    try:
        X = data.shared['X']
        Y = data.shared['Y']
        T_tard = data.shared['T_tard']
        V_used = data.shared['V_used']

        units_list = data.shared['units_list']
        batches = data.shared['batches_list']
        trucks = data.shared['trucks_list']
        site_map = data.shared['site_map']
        params = data.shared['params']

        # Extracción de valores
        X_sol = [(b, u, s) for (b, u, s), var in X.items()
                 if safe_val(getattr(var, 'varValue', None)) > 0.5]

        Y_sol = [(b, v, t) for (b, v, t), var in Y.items()
                 if safe_val(getattr(var, 'varValue', None)) > 0.5]

        Vused_sol = {v: safe_val(getattr(V_used[v], 'varValue', None)) for v in V_used}
        Tt_sol = {b: safe_val(getattr(T_tard[b], 'varValue', None)) for b in T_tard}

    except KeyError as e:
        print("ERROR: variable no encontrada en data.shared:", e)
        return
    except Exception as e:
        print(f"ERROR inesperado extrayendo solución: {e}")
        return

    # 3. Validación de existencia de solución
    if not X_sol or not Y_sol:
        print("ADVERTENCIA: El solver no devolvió solución (Infeasible o Vacía).")
        print("Saltando verificaciones detalladas.")
        return 

    print(f"X_sol = {len(X_sol)}, Y_sol = {len(Y_sol)}")

    # Precalcular tiempos
    proc_time = {ui: int(units_list[ui]["process_time_min"])
                 for ui in range(len(units_list))}

    wait = params.get("wait_before_departure", 0)
    wash = params.get("wash_time", 0)
    
    # --- CAMBIO: Cargar unload_time (necesario para C, I, J, K) ---
    unload_time = params.get("unload_time_min", 30) # 30 min por defecto [cite: 452]
    
    # ============================================================
    # B) Construir cronograma de producción
    # ============================================================
    prod = []
    for (b, u, s) in X_sol:
        finish = s + proc_time[u]
        prod.append({
            "batch": b,
            "unit": u,
            "start": s,
            "finish": finish,
            "site": batches[b]["site_id"],
            "volume": batches[b]["volume"]
        })

    if not prod:
        print("ADVERTENCIA: No hay producción planificada. Saltando validaciones de producción.")
        df_prod = pd.DataFrame(columns=["batch", "unit", "start", "finish", "site", "volume"])
    else:
        df_prod = pd.DataFrame(prod).sort_values(["unit", "start"])
    # ============================================================
    # C) Construir cronograma de camiones (MEJORADO)
    # ============================================================
    truck_sched = []
    for (b, v, t) in Y_sol:
        site = batches[b]["site_id"]

        travel = site_map[site].get("travel_time_min", None)
        if travel is None:
            print(f"ADVERTENCIA: travel_time_min faltante para sitio {site}")
            travel = 0

        travel = float(travel)
        
        # --- CAMBIO: Calcular inicio y fin de descarga ---
        arrive = t + travel
        unload_start = arrive
        unload_finish = unload_start + unload_time # [cite: 413]

        truck_sched.append({
            "batch": b,
            "truck": v,
            "depart": t,
            "arrive": arrive,
            "unload_start": unload_start, # <-- NUEVO
            "unload_finish": unload_finish, # <-- NUEVO
            "site": site,
            "volume": batches[b]["volume"]
        })

    df_tr = pd.DataFrame(truck_sched).sort_values(["truck", "depart"])

    # ============================================================
    # D) Verificación 1: Overlap en unidades
    # ============================================================
    overlap_viol = []

    for u, grp in df_prod.groupby("unit"):
        rows = grp.sort_values("start").to_dict("records")
        for i in range(len(rows) - 1):
            if rows[i]["finish"] > rows[i + 1]["start"]:
                overlap_viol.append((u, rows[i], rows[i + 1]))

    print("Overlap en unidades:", len(overlap_viol))

    # ============================================================
    # E) Verificación 2: depart >= finish + wait + wash
    # ============================================================
    depart_viol = []
    prod_by_b = {r["batch"]: r for r in prod}

    for r in truck_sched:
        b = r["batch"]
        if b not in prod_by_b:
            # Si Y_sol tiene un lote que X_sol no tiene, es una inconsistencia
            depart_viol.append((b, "No tiene producción asignada (X/Y inconsistente)"))
            continue

        fin = prod_by_b[b]["finish"]
        min_dep = fin + wait + wash

        if r["depart"] < min_dep:
            depart_viol.append((b, r["depart"], min_dep))

    print("Violaciones depart>=finish+wait+wash (Eq. 7):", len(depart_viol))

    # ============================================================
    # F) Verificación 3: Conflictos de doble uso de camión
    # ============================================================
    df_dup = df_tr.groupby(["truck", "depart"]).size().reset_index(name="count")
    df_dup = df_dup[df_dup["count"] > 1]

    print("Conflictos de doble uso del camión:", len(df_dup))

    # ============================================================
    # G) Verificación 4: Capacidad
    # ============================================================
    cap_viol = []
    for r in truck_sched:
        cap = float(trucks[r["truck"]]["capacity_m3"])
        if r["volume"] > cap + 1e-6:
            cap_viol.append((r["batch"], r["truck"], r["volume"], cap))

    print("Violaciones de capacidad:", len(cap_viol))

    # ============================================================
    # H) Verificación 5: V_used
    # ============================================================
    vused_viol = []

    for v, val in Vused_sol.items():
        used = any(1 for (b, v2, t) in Y_sol if v2 == v)
        if used and val < 0.5:
            vused_viol.append((v, val, "Usado pero no marcado"))
        if not used and val > 0.5:
            vused_viol.append((v, val, "Marcado pero no usado"))

    print("Inconsistencias V_used:", len(vused_viol))

    # ============================================================
    # I) Verificación 6: Tardiness (CORREGIDO)
    # ============================================================
    tard_viol = []

    for r in truck_sched:
        b = r["batch"]
        site = r["site"]

        # Determinar time window final
        tw_end_val = site_map[site].get("tw_end_h", params.get("T2"))
        tw_end = time_to_minutes(tw_end_val)

        # --- CAMBIO: La tardanza se mide sobre el FIN de la descarga [cite: 413] ---
        recomputed = max(0, r["unload_finish"] - tw_end)
        recorded = Tt_sol.get(b, 0)

        if abs(recomputed - recorded) > 1: # Permitir 1 min de redondeo
            tard_viol.append((b, recomputed, recorded))

    print("Tardiness inconsistencias (Eq. 18):", len(tard_viol))

    
    # --- INICIO DE SECCIONES NUEVAS ---
    
    # ============================================================
    # J) Verificación 7: Sincronización de Descarga (Eq. 13 y 14)
    # ============================================================
    max_time_lag = params.get("max_time_lag", 60) # 1 hora por defecto [cite: 453]
    unload_overlap_viol = []
    max_lag_viol = []
    
    # Agrupar por sitio y ordenar por inicio de descarga
    for site, grp in df_tr.groupby("site"):
        if len(grp) < 2:
            continue # No hay entregas consecutivas que chequear
        
        rows = grp.sort_values("unload_start").to_dict("records")
        
        for i in range(len(rows) - 1):
            curr = rows[i]
            next = rows[i+1]
            
            # Chequeo Eq. 13: La siguiente descarga no puede empezar ANTES de que la actual termine 
            if next["unload_start"] < curr["unload_finish"] - 1e-6: # Pequeña tolerancia
                unload_overlap_viol.append((site, curr["batch"], next["batch"]))
                
            # Chequeo Eq. 14: El gap no puede ser muy grande 
            gap = next["unload_start"] - curr["unload_finish"]
            if gap > max_time_lag + 1e-6: # Pequeña tolerancia
                max_lag_viol.append((site, curr["batch"], next["batch"], gap))

    print("Violaciones de solapamiento de descarga (Eq. 13):", len(unload_overlap_viol))
    print("Violaciones de max time lag (Eq. 14):", len(max_lag_viol))
    

    # --- INICIO DE SECCIÓN CORREGIDA ---
    
    # ============================================================
    # K) Verificación 8: Setting Time (Eq. 8)
    # ============================================================
    setting_time_viol = []
    
    # Mapa de Setting Time (basado en el paper, igual que cell8) 
    setting_time_map = {
        "p1": 108, "p2": 108, "p3": 114, "p4": 114,
        "p5": 114, "p6": 90,  "p7": 108, "p8": 126
    }
    
    # Unir producción y transporte
    df_prod_indexed = df_prod.set_index("batch")
    df_tr_indexed = df_tr.set_index("batch")
    
    # Usar 'inner join' porque un lote debe tener AMBAS (prod y transp)
    df_full = df_prod_indexed.join(df_tr_indexed, how='inner', lsuffix='_prod', rsuffix='_tr')
    
    if len(df_full) != len(Y_sol):
         # Nota: Esto es esperado si Y_sol es incompleto (como 45 vs 46)
         print(f"ADVERTENCIA: Discrepancia en Join. Prod: {len(df_prod)}, Tr: {len(df_tr)}, Full: {len(df_full)}")

    for b, row in df_full.iterrows():
        prod_finish = row["finish"]
        unload_finish = row["unload_finish"]
        
        # --- Lógica Corregida ---
        # Obtener el tipo de concreto para este lote
        site = row["site_prod"] # "site_prod" es el 'site' de df_prod
        ctype = site_map.get(site, {}).get("concrete_type", "p6").strip().lower()
        setting_time = setting_time_map.get(ctype, 90) # Usar el mapa 
        
        duration = unload_finish - prod_finish
        
        # Chequeo Eq. 8: Duración total no puede exceder el setting time 
        if duration > setting_time + 1e-6: # Pequeña tolerancia
            setting_time_viol.append((b, duration, setting_time))
    
    print("Violaciones de setting time (Eq. 8):", len(setting_time_viol))
    
    # --- FIN DE SECCIÓN CORREGIDA ---
    
    print("========== FIN CELDA 10 ==========\n")