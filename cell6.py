import data
import math
from collections import defaultdict
import pandas as pd

def run():
    # Nueva Celda 6: generar batches robustos a partir de df_sites y df_trucks
    df_sites = data.shared['df_sites']
    df_trucks = data.shared['df_trucks']
    params = data.shared['params']

    # Asegúrate de tener df_sites y df_trucks cargados
    df_sites["demand_m3"] = pd.to_numeric(df_sites["demand_m3"], errors="coerce").fillna(0)
    site_map = {str(s["site_id"]).strip(): s.to_dict() for _, s in df_sites.iterrows()}

    df_trucks["capacity_m3"] = pd.to_numeric(df_trucks["capacity_m3"], errors="coerce").fillna(0)
    if "min_load_m3" not in df_trucks.columns:
        df_trucks["min_load_m3"] = 0
    else:
        df_trucks["min_load_m3"] = pd.to_numeric(df_trucks["min_load_m3"], errors="coerce").fillna(0)

    max_truck_cap = df_trucks["capacity_m3"].max()
    min_truck_minload = df_trucks["min_load_m3"].min() if len(df_trucks)>0 else 0

    print("Max truck capacity:", max_truck_cap)
    print("Min truck min-load:", min_truck_minload)

    batches = []
    for _, s in df_sites.iterrows():
        site_id = s["site_id"]
        rem = float(s["demand_m3"])
        if rem <= 0:
            continue
        n_full = int(rem // max_truck_cap)
        chunks = [max_truck_cap] * n_full
        last = rem - n_full * max_truck_cap
        if last > 0:
            if last < min_truck_minload and len(chunks) > 0:
                if chunks[-1] + last <= max_truck_cap:
                    chunks[-1] = chunks[-1] + last
                    last = 0
            if last > 0:
                chunks.append(last)
        for idx, vol in enumerate(chunks, start=1):
            batches.append({
                "site_id": site_id,
                "batch_id": f"{site_id}_b{idx}",
                "volume": round(float(vol), 6)
            })

    small_batches = [b for b in batches if b["volume"] < min_truck_minload]
    if small_batches:
        print("WARNING: Found small batches below the minimum truck min-load. Review these if unexpected:")
        for b in small_batches:
            print(b)

    df_batches = pd.DataFrame(batches)
    print("Batches generated:", df_batches.shape[0])

    # Paso Previo: Mergear small batches
    min_truck_minload = df_trucks["min_load_m3"].min() if "min_load_m3" in df_trucks.columns else 0
    small = df_batches[df_batches["volume"] < min_truck_minload].copy()
    print("Small batches to merge:", small.shape[0])
    if not small.empty:
        merged = []
        dfb = df_batches.copy()
        dfb["batch_idx"] = dfb["batch_id"].str.extract(r"_b(\d+)$").astype(float).fillna(0).astype(int)
        dfb = dfb.sort_values(["site_id","batch_idx"]).reset_index(drop=True)

        to_drop = []
        for _, sb in small.iterrows():
            site = sb["site_id"]
            bidx = int(sb["batch_id"].split("_b")[-1])
            prev_mask = (dfb["site_id"]==site) & (dfb["batch_idx"] == (bidx-1))
            if prev_mask.any():
                prev_idx = dfb[prev_mask].index[0]
                dfb.at[prev_idx, "volume"] = float(dfb.at[prev_idx, "volume"]) + float(sb["volume"])
                to_drop.append(sb["batch_id"])
                merged.append((sb["batch_id"], dfb.at[prev_idx, "batch_id"], sb["volume"]))
            else:
                next_mask = (dfb["site_id"]==site) & (dfb["batch_idx"] == (bidx+1))
                if next_mask.any():
                    next_idx = dfb[next_mask].index[0]
                    dfb.at[next_idx, "volume"] = float(dfb.at[next_idx, "volume"]) + float(sb["volume"])
                    to_drop.append(sb["batch_id"])
                    merged.append((sb["batch_id"], dfb.at[next_idx, "batch_id"], sb["volume"]))
                else:
                    print("No neighbor to merge for", sb["batch_id"], "site", site)

        if to_drop:
            dfb = dfb[~dfb["batch_id"].isin(to_drop)].copy()
        dfb = dfb.drop(columns=["batch_idx"])
        df_batches = dfb.reset_index(drop=True)
        print("Merged small batches (source -> target -> vol):")
        for m in merged:
            print(m)
    else:
        print("No small batches found; no merge required.")

    # Paso previo 2: Eliminar batches que superan la capacidad máxima
    max_cap = df_trucks["capacity_m3"].max()
    too_big = df_batches[df_batches["volume"] > max_cap]
    print("Removing oversized batches:", too_big["batch_id"].tolist())
    df_batches = df_batches[df_batches["volume"] <= max_cap].copy()
    df_batches.reset_index(drop=True, inplace=True)

    data.shared['df_batches'] = df_batches
    data.shared['site_map'] = site_map  # Also store site_map for later use