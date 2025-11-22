# cell9_report.py -- Diagnóstico de Solución
from src import context as data
import pulp
import pandas as pd

def run():
    print("\n=== CELDA 9: REPORTE DE DIAGNÓSTICO ===")
    
    # Recuperar variables
    try:
        prob = data.shared['prob']
        X = data.shared['X']
        Y = data.shared['Y']
        batches = data.shared['batches_list']
        slacks_map = {v.name: v for v in prob.variables() if "Slack" in v.name}
    except:
        print("No hay solución cargada en memoria.")
        return

    # Verificar estado del solver
    print(f"Estado del Solver: {pulp.LpStatus[prob.status]}")
    print(f"Función Objetivo Final: {pulp.value(prob.objective):,.2f}")

    # 1. Análisis de Slacks (¿Por qué cuesta 20 Millones?)
    print("\n--- [ALERT] DESGLOSE DE VIOLACIONES (SLACKS) ---")
    total_slack_min = 0
    
    active_slacks = []
    for name, var in slacks_map.items():
        val = var.varValue
        if val and val > 0.1: # Filtrar ruido numérico
            total_slack_min += val
            active_slacks.append((name, val))
    
    active_slacks.sort(key=lambda x: x[1], reverse=True)
    
    if not active_slacks:
        print("[OK] ¡CERO VIOLACIONES! La solución es perfecta en calidad.")
    else:
        print(f"Total minutos de violación: {total_slack_min:.1f} min")
        print("Top 10 peores violaciones:")
        for name, val in active_slacks[:10]:
            print(f"  [FAIL] {name}: {val:.1f} min")

    # 2. Análisis de Transporte
    print("\n--- [TRUCK] RESUMEN LOGÍSTICO ---")
    trips = []
    for (b, v, t), var in Y.items():
        if var.varValue and var.varValue > 0.5:
            trips.append((b, v, t))
    
    trips.sort(key=lambda x: x[2]) # Ordenar por tiempo
    print(f"Total Viajes Asignados: {len(trips)} / {len(batches)}")
    
    # Mostrar primeros 5 viajes
    for (b, v, t) in trips[:5]:
        site = batches[b]['site_id']
        print(f"  - Lote {b} -> Camión {v} sale a las {t} min hacia {site}")

    print("\n=== FIN REPORTE ===")