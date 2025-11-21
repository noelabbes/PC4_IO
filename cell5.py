import data
import json
import pandas as pd
import os

def run():
    # Celda 5 (nueva): Cargar datos reales desde CSVs y params.json

    # Usar directorio del script para rutas relativas
    base_dir = os.path.dirname(__file__)
    path_sites = os.path.join(base_dir, "construction_sites.csv")
    path_trucks = os.path.join(base_dir, "trucks.csv")
    path_units = os.path.join(base_dir, "units.csv")
    path_params = os.path.join(base_dir, "params.json")

    # Verificar que los archivos existan
    for path, name in [(path_sites, "construction_sites.csv"), (path_trucks, "trucks.csv"), (path_units, "units.csv"), (path_params, "parameters.json")]:
        if not os.path.exists(path):
            print(f"Error: {name} not found in {base_dir}")
            return

    # Cargar CSVs en DataFrames
    df_sites = pd.read_csv(path_sites)
    df_trucks = pd.read_csv(path_trucks)
    df_units = pd.read_csv(path_units)

    # Cargar parámetros globales
    with open(path_params, "r") as f:
        params = json.load(f)

    print("✅ Datos cargados correctamente:\n")
    print("Sitios:", df_sites.shape)
    print("Camiones:", df_trucks.shape)
    print("Unidades:", df_units.shape)
    print("\nParámetros globales:")
    print(json.dumps(params, indent=2))

    # Store in shared data
    data.shared['df_sites'] = df_sites
    data.shared['df_trucks'] = df_trucks
    data.shared['df_units'] = df_units
    data.shared['params'] = params