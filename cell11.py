# cell11_solve_milp.py -- Versión Highs/ARM64 Compatible
import data
import pulp
import time
import shutil
import os
import cell9_report

def run():
    print("\n=== CELDA 11: INICIO SOLVE MILP COMPLETO (HIGHS 4-CORES) ===")
    start_time = time.time()

    # ---------------------------
    # 1. Recuperar el problema y las variables
    # ---------------------------
    try:
        prob = data.shared['prob']
        # Acceso para verificar integridad, aunque el solver usa 'prob' directamente
        X = data.shared['X']
        Y = data.shared['Y']
        V_used = data.shared['V_used']
        T_tard = data.shared['T_tard']
    except KeyError as e:
        print(f"Error crítico: Falta {e} en data.shared. Ejecuta cell7 y cell8 primero.")
        return

    # Usamos len() directo si es posible, o fallback seguro
    num_vars = len(X) + len(Y) + len(T_tard) + len(V_used)
    print(f"Problema MILP cargado: ~{num_vars} variables, {len(prob.constraints)} restricciones.")
    print("Warm Start (Solución Heurística) ya inyectado en las variables por Cell 8.")

    # ---------------------------
    # 2. Configurar Solver (Prioridad: Highs Multihilo)
    # ---------------------------
    solver = None
    log_path = "solver_highs.log"
    time_limit_sec = 7200 # 2 horas es suficiente para el modelo compacto

    # Estrategia de Selección de Solver Robusta
    if shutil.which("highs"):
        print("✅ Ejecutable 'highs' detectado en sistema.")
        # Highs CMD soporta threads y log path
        solver = pulp.HiGHS_CMD(
            timeLimit=time_limit_sec,
            threads=4,
            path="highs",
            options=[f"--log_file={log_path}"] # Opción nativa de Highs para log
        )
    else:
        try:
            import highspy
            print("✅ Librería Python 'highspy' detectada.")
            # La API de Highs es rápida pero a veces el log es por stdout
            solver = pulp.HiGHS(
                timeLimit=time_limit_sec,
                msg=True, # Mostrar progreso en consola
                options={
                    "threads": 4,      # Forzar hilos aquí
                    "parallel": "on",  # Refuerzo explícito
                    "presolve": "on"
                }
            )
        except ImportError:
            print("⚠️ Highs no encontrado. Usando CBC (Fallback Single-Thread).")
            solver = pulp.PULP_CBC_CMD(
                timeLimit=time_limit_sec,
                msg=True,
                logPath="solver_cbc.log"
            )

    print(f"Iniciando optimización con 4 hilos (si Highs está disponible)...")
    
    # ---------------------------
    # 3. Resolver
    # ---------------------------
    # El solver tomará los valores .setInitialValue() de las variables automáticamente
    prob.solve(solver)
    # ---------------------------
    # 4. Procesar Resultados
    # ---------------------------
    end_time = time.time()
    status = pulp.LpStatus[prob.status]
    obj_val = pulp.value(prob.objective)

    print("✅ Solver finalizado. Generando reporte de cell9_report.py inmediato...")
    cell9_report.run()
    
    print(f"\n--- SOLVER FINALIZADO ---")
    print(f"Estado Final: {status}")
    print(f"Tiempo Total: {end_time - start_time:.2f} segundos")
    print(f"Costo Objetivo: {obj_val}")

    if status != "Optimal":
        print("ADVERTENCIA: La solución puede no ser óptima (Time Limit o Infeasible).")
        
    # ---------------------------
    # 5. Extraer y Guardar Solución
    # ---------------------------
    print("Guardando solución óptima en data.shared...")

    # Helper seguro para extraer valor
    def get_val(v):
        return v.varValue if v.varValue is not None else 0.0

    new_chosen_X = {}
    for key, var in X.items():
        if get_val(var) > 0.5: # Umbral binario seguro
            new_chosen_X[key[0]] = key # Guardamos (b, u, s) indexado por b

    new_chosen_Y = {}
    used_trucks_set = set()
    for key, var in Y.items():
        if get_val(var) > 0.5:
            b_idx, v_idx, t = key
            new_chosen_Y[b_idx] = key
            used_trucks_set.add(v_idx)

    new_Tt_frac = {b: get_val(var) for b, var in T_tard.items()}
    new_V_used_frac = {v: get_val(var) for v, var in V_used.items()}

    # Sobrescribir datos compartidos para reportes
    data.shared["chosen_X"] = new_chosen_X
    data.shared["chosen_Y"] = new_chosen_Y
    data.shared["Tt_frac"] = new_Tt_frac
    data.shared["V_used_frac"] = new_V_used_frac

    print(f"Resumen Solución: {len(new_chosen_X)} lotes producidos, {len(new_chosen_Y)} lotes transportados.")
    print(f"Flota utilizada: {len(used_trucks_set)} camiones.")
    print("=== CELDA 11: FIN ===")