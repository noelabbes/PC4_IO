# cell9_reconstruct.py : Reconstrucción de solución entera para time-indexed
import data
import pandas as pd

def run():

    print("\n========== CELDA 9: RECONSTRUCCIÓN DE SOLUCIÓN ==========\n")

    # Recuperar estructuras
    X          = data.shared["X"]         # X[b,u,s]
    Y          = data.shared["Y"]         # Y[b,v,t]
    T_tard     = data.shared["T_tard"]
    V_used     = data.shared["V_used"]
    batches    = data.shared["batches_list"]
    trucks     = data.shared["trucks_list"]
    units      = data.shared["units_list"]
    site_map   = data.shared["site_map"]
    params     = data.shared["params"]

    print("Variables cargadas desde data.shared.")

    # ------------------------------------------------------------
    # EXTRAER SOLUCIÓN ENTERA
    # ------------------------------------------------------------
    print("Extrayendo solución entera actual del solver...")

    X_sol = {}
    for key, var in X.items():
        if var.varValue is not None and var.varValue > 0.5:
            X_sol[key] = 1

    Y_sol = {}
    for key, var in Y.items():
        if var.varValue is not None and var.varValue > 0.5:
            Y_sol[key] = 1

    print("X_sol:", len(X_sol), "Y_sol:", len(Y_sol))


    # ------------------------------------------------------------
    # RECONSTRUCCIÓN DE PRODUCCIÓN POR UNIDAD
    # ------------------------------------------------------------
    print("\n--- Reconstruyendo producción por unidad ---")

    # Mapeo correcto: índice de unidad → tiempo de proceso
    unit_proc_time = {
        idx: u["process_time_min"]
        for idx, u in enumerate(units)
    }

    rows_prod = []

    for (b, u, s) in X_sol:
        batch = batches[b]
        start_time = s
        proc_time = unit_proc_time[u]  # FIX: ya no usa unit_id string
        finish_time = start_time + proc_time

        rows_prod.append({
            "batch": b,
            "unit": u,
            "site_id": batch["site_id"],
            "start_min": start_time,
            "finish_min": finish_time,
            "volume_m3": batch["volume"]
        })

    df_prod = pd.DataFrame(rows_prod)
    print(df_prod.head())

    data.shared["df_prod"] = df_prod



    # ------------------------------------------------------------
    # RECONSTRUCCIÓN DE ASIGNACIÓN DE CAMIONES
    # ------------------------------------------------------------
    print("\n--- Reconstruyendo asignación de camiones ---")

    rows_trucks = []

    for (b, v, t) in Y_sol:
        batch = batches[b]
        truck = trucks[v]
        rows_trucks.append({
            "batch": b,
            "truck": truck["truck_id"],
            "site_id": batch["site_id"],
            "depart_time_min": t,
            "volume_m3": batch["volume"],
            "travel_time_min": site_map[batch["site_id"]]["travel_time_min"]
        })

    df_trucks = pd.DataFrame(rows_trucks)
    print(df_trucks.head())

    data.shared["df_trucks"] = df_trucks


    # ------------------------------------------------------------
    # RETRASOS
    # ------------------------------------------------------------
    print("\n--- Calculando tardiness report ---")

    tardiness_rows = []

    for b, var in T_tard.items():
        val = var.varValue if var.varValue is not None else 0
        batch = batches[b]
        tardiness_rows.append({
            "batch": b,
            "site_id": batch["site_id"],
            "tardiness_min": val
        })

    df_tard = pd.DataFrame(tardiness_rows)
    print(df_tard.head())

    data.shared["df_tard"] = df_tard


    # ------------------------------------------------------------
    # COST SUMMARY
    # ------------------------------------------------------------
    print("\n--- Calculando resumen de costos ---")

    alpha = params["alpha"]
    beta  = params["beta"]

    total_truck_cost = 0
    for (b, v, t) in Y_sol:
        batch = batches[b]
        truck = trucks[v]
        dist = site_map[batch["site_id"]]["dist_km"]

        total_truck_cost += truck["fixed_cost"] + truck["var_cost_per_km"] * dist

    total_tardiness = df_tard["tardiness_min"].sum()
    total_cost = total_truck_cost + alpha * total_truck_cost + beta * total_tardiness

    summary = {
        "truck_cost": total_truck_cost,
        "tardiness_cost": beta * total_tardiness,
        "total_cost": total_cost
    }

    print(summary)
    data.shared["summary"] = summary

    print("\n========== FIN CELDA 9 ==========\n")
