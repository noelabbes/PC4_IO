# cell12_gantt.py
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import pandas as pd
import numpy as np
import data

def minutes_to_hhmm(minutes):
    """Convierte minutos absolutos (ej. 480) a formato hora (08:00)."""
    h = int(minutes / 60)
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"

def get_site_color(site_id, color_map):
    """Asigna un color consistente a cada sitio."""
    if site_id not in color_map:
        # Generar un color único de la paleta tab20
        idx = len(color_map) % 20
        color_map[site_id] = plt.cm.tab20(idx)
    return color_map[site_id]

def run():
    print("=== CELDA 12: GENERANDO DIAGRAMA DE GANTT (Carga, Espera, Lavado, Viaje, Descarga) ===")
    
    # 1. Recuperar datos del contexto compartido
    if 'X' not in data.shared or 'Y' not in data.shared:
        print("Error: No se encontraron soluciones (X, Y) en data.shared")
        return

    X_vars = data.shared['X'] # Producción
    Y_vars = data.shared['Y'] # Transporte
    batches = data.shared['batches_list']
    units = data.shared['units_list']
    trucks = data.shared['trucks_list']
    site_map = data.shared['site_map']
    params = data.shared['params']

    # Parámetros globales
    wash_time = params.get("wash_time", 10)
    unload_time = params.get("unload_time", 30)
    T1 = params.get("T1", 420)
    T2 = params.get("T2", 1020)

    # 2. Procesar la solución para graficar
    schedule_units = [] 
    schedule_trucks = [] 
    
    color_map = {} 

    # A) Procesar Producción (X)
    # Necesitamos saber cuándo empieza y termina la producción de cada lote
    # para dibujar la "Carga" en el camión.
    batch_prod_info = {} # {batch_id: {'start': t, 'end': t+proc, 'duration': proc}}
    
    for (b_idx, u_idx, t), var in X_vars.items():
        if var.varValue and var.varValue > 0.5:
            proc_time = float(units[u_idx]["process_time_min"])
            site_id = str(batches[b_idx]["site_id"]).strip().lower()
            
            schedule_units.append({
                "unit": u_idx,
                "start": t,
                "duration": proc_time,
                "site": site_id,
                "batch": b_idx
            })
            batch_prod_info[b_idx] = {
                'start': t,
                'end': t + proc_time,
                'duration': proc_time
            }

    # B) Procesar Transporte (Y)
    active_trucks = set()
    for (b_idx, v_idx, t), var in Y_vars.items():
        if var.varValue and var.varValue > 0.5:
            site_id = str(batches[b_idx]["site_id"]).strip().lower()
            site_data = site_map.get(site_id, {})
            travel_time = float(site_data.get("travel_time_min", 0))
            tw_end_h = site_data.get("tw_end_h", 17.0)
            
            try:
                if isinstance(tw_end_h, str) and ":" in tw_end_h:
                    hh, mm = map(int, tw_end_h.split(":"))
                    tw_end_min = hh * 60 + mm
                else:
                    tw_end_min = int(float(tw_end_h) * 60)
            except:
                tw_end_min = T2

            # Obtener datos de producción para este lote
            prod_data = batch_prod_info.get(b_idx, {'start': T1, 'end': T1, 'duration': 0})
            
            schedule_trucks.append({
                "truck": v_idx,
                "depart": t,
                "travel": travel_time,
                "site": site_id,
                "batch": b_idx,
                "prod_start": prod_data['start'],   # Inicio Carga
                "prod_end": prod_data['end'],       # Fin Carga
                "tw_end": tw_end_min
            })
            active_trucks.add(v_idx)

    # Filtrar y ordenar camiones usados
    sorted_truck_indices = sorted(list(active_trucks))
    truck_y_map = {v_idx: i for i, v_idx in enumerate(sorted_truck_indices)}

    # 3. Configuración del Gráfico
    fig, (ax_units, ax_trucks) = plt.subplots(2, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [1, 3]})
    
    # --- GRÁFICO SUPERIOR: UNIDADES ---
    ax_units.set_title(f"Plan de Producción (Unidades) - Solución Óptima ({len(schedule_units)} lotes)")
    y_ticks_units = []
    y_labels_units = []

    for u_idx in range(len(units)):
        y_pos = u_idx
        y_ticks_units.append(y_pos)
        y_labels_units.append(f"Unit {u_idx+1}")
        ax_units.axhspan(y_pos - 0.4, y_pos + 0.4, color='lightgray', alpha=0.1)

    for task in schedule_units:
        color = get_site_color(task["site"], color_map)
        rect = mpatches.Rectangle((task["start"], task["unit"] - 0.3), task["duration"], 0.6, 
                                  color=color, ec='black', alpha=0.8)
        ax_units.add_patch(rect)
        ax_units.text(task["start"] + task["duration"]/2, task["unit"], f"b{task['batch']}", 
                      ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    ax_units.set_yticks(y_ticks_units)
    ax_units.set_yticklabels(y_labels_units)
    ax_units.grid(True, axis='x', linestyle='--', alpha=0.5)

    # --- GRÁFICO INFERIOR: CAMIONES ---
    ax_trucks.set_title(f"Logística de Distribución ({len(schedule_trucks)} viajes en {len(active_trucks)} camiones)")
    y_ticks_trucks = []
    y_labels_trucks = []

    for v_idx in sorted_truck_indices:
        y_pos = truck_y_map[v_idx]
        y_ticks_trucks.append(y_pos)
        cap = trucks[v_idx]['capacity_m3']
        y_labels_trucks.append(f"T{v_idx} ({cap}m3)")
        ax_trucks.axhspan(y_pos - 0.4, y_pos + 0.4, color='whitesmoke', alpha=0.3)

    for trip in schedule_trucks:
        y_pos = truck_y_map[trip["truck"]]
        color = get_site_color(trip["site"], color_map)
        
        # --- CRONOLOGÍA DEL VIAJE ---
        # 1. Carga (Loading): Coincide con la producción
        t_load_start = trip["prod_start"]
        t_load_end = trip["prod_end"]
        
        # 2. Lavado (Washing): Justo antes de salir
        t_depart = trip["depart"]
        t_wash_start = t_depart - wash_time
        t_wash_end = t_depart
        
        # 3. Espera (Waiting): Entre Fin de Carga e Inicio de Lavado
        # Si wash empieza después de que termina la carga, hay espera.
        t_wait_start = t_load_end
        t_wait_end = t_wash_start
        
        # 4. Viaje Ida
        t_arrive_site = t_depart + trip["travel"]
        
        # 5. Descarga
        t_finish_unload = t_arrive_site + unload_time
        
        # 6. Retorno
        t_return_plant = t_finish_unload + trip["travel"]

        # --- DIBUJO ---
        
        # A. LOADING (Carga) - Borde punteado rojo o color suave
        # Representa que el camión está debajo de la tolva
        ax_trucks.add_patch(mpatches.Rectangle((t_load_start, y_pos - 0.25), t_load_end - t_load_start, 0.5, 
                                               facecolor='none', hatch='..', edgecolor='red', linewidth=0.5, alpha=0.5))
        
        # B. WAITING (Espera) - Línea punteada
        if t_wait_end > t_wait_start:
            ax_trucks.plot([t_wait_start, t_wait_end], [y_pos, y_pos], 
                           linestyle=':', color='gray', linewidth=2)

        # C. WASHING (Lavado) - Gris rayado
        ax_trucks.add_patch(mpatches.Rectangle((t_wash_start, y_pos - 0.2), wash_time, 0.4, 
                                               color='lightgray', hatch='///', ec='black'))

        # D. TRAVEL TO (Ida) - Color del Sitio
        ax_trucks.add_patch(mpatches.Rectangle((t_depart, y_pos - 0.3), trip["travel"], 0.6, 
                                               color=color, ec='black'))

        # E. UNLOAD (Descarga) - Negro sólido
        ax_trucks.add_patch(mpatches.Rectangle((t_arrive_site, y_pos - 0.3), unload_time, 0.6, 
                                               color='black', alpha=0.7, ec='black'))

        # F. TRAVEL BACK (Retorno) - Transparente
        ax_trucks.add_patch(mpatches.Rectangle((t_finish_unload, y_pos - 0.3), trip["travel"], 0.6, 
                                               color=color, alpha=0.3, ec='black', linestyle='--'))

        # G. TARDINESS (Tardanza) - Alerta Amarilla
        if t_finish_unload > trip["tw_end"]:
            start_delay = max(trip["tw_end"], t_arrive_site)
            duration_delay = t_finish_unload - start_delay
            if duration_delay > 0:
                delay_min = int(t_finish_unload - trip["tw_end"])
                # Rectángulo amarillo sobre la parte final de la descarga
                ax_trucks.add_patch(mpatches.Rectangle((start_delay, y_pos - 0.35), duration_delay, 0.7, 
                                                       color='yellow', alpha=0.8, ec='red', linewidth=2))
                # Etiqueta de minutos
                ax_trucks.text(t_finish_unload, y_pos + 0.45, f"!{delay_min}m", 
                               color='red', fontsize=7, ha='center', fontweight='bold')

        # Etiqueta "To Site" en el viaje de ida
        ax_trucks.text(t_depart + trip["travel"]/2, y_pos, f"To {trip['site']}", 
                       ha='center', va='center', color='white', fontsize=6, fontweight='bold')

    # Configuración final de ejes
    ax_trucks.set_yticks(y_ticks_trucks)
    ax_trucks.set_yticklabels(y_labels_trucks)
    x_ticks = np.arange(T1, T2 + 60, 60)
    x_labels = [minutes_to_hhmm(t) for t in x_ticks]
    ax_trucks.set_xticks(x_ticks)
    ax_trucks.set_xticklabels(x_labels, rotation=0)
    ax_trucks.set_xlabel("Hora del día")
    ax_trucks.grid(True, axis='x', linestyle='--', alpha=0.5)

    # Leyenda
    legend_patches = [mpatches.Patch(color=c, label=s) for s, c in color_map.items()]
    legend_patches.append(mpatches.Patch(facecolor='none', hatch='..', edgecolor='red', label='Loading (Plant)'))
    legend_patches.append(mpatches.Patch(facecolor='lightgray', hatch='///', label='Washing'))
    legend_patches.append(mpatches.Patch(color='black', alpha=0.7, label='Unloading (Site)'))
    legend_patches.append(mpatches.Patch(color='white', ec='black', alpha=0.3, linestyle='--', label='Return Trip'))
    legend_patches.append(mpatches.Patch(color='yellow', ec='red', label='Tardiness'))
    
    fig.legend(handles=legend_patches, loc='upper center', bbox_to_anchor=(0.5, 0.06), ncol=6, fontsize='small')

    plt.tight_layout(rect=[0, 0.07, 1, 1])
    filename = "gantt_optimal_schedule_full.png"
    plt.savefig(filename, dpi=150)
    print(f"Diagrama de Gantt detallado guardado en: {filename}")
    plt.close()

if __name__ == "__main__":
    pass