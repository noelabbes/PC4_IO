
from src import context as data
import json
import pandas as pd
import os

def run():
    # Load real data from CSVs and params.json
    
    # Define paths relative to the project root (assuming execution from root)
    # Or relative to this file: ../../input/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # project root
    input_dir = os.path.join(base_dir, "input")
    
    path_sites = os.path.join(input_dir, "construction_sites.csv")
    path_trucks = os.path.join(input_dir, "trucks.csv")
    path_units = os.path.join(input_dir, "units.csv")
    path_params = os.path.join(input_dir, "params.json")

    # Verify files exist
    for path, name in [(path_sites, "construction_sites.csv"), (path_trucks, "trucks.csv"), (path_units, "units.csv"), (path_params, "parameters.json")]:
        if not os.path.exists(path):
            print(f"Error: {name} not found in {input_dir}")
            return

    # Load CSVs into DataFrames
    df_sites = pd.read_csv(path_sites)
    df_trucks = pd.read_csv(path_trucks)
    df_units = pd.read_csv(path_units)

    # Load global parameters
    with open(path_params, "r") as f:
        params = json.load(f)

    print("[OK] Data loaded successfully:\n")
    print("Sites:", df_sites.shape)
    print("Trucks:", df_trucks.shape)
    print("Units:", df_units.shape)
    print("\nGlobal Parameters:")
    print(json.dumps(params, indent=2))

    # Store in shared data
    data.shared['df_sites'] = df_sites
    data.shared['df_trucks'] = df_trucks
    data.shared['df_units'] = df_units
    data.shared['params'] = params
