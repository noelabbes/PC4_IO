import json
import os

def load_params(params_path="input/params.json"):
    if not os.path.exists(params_path):
        # Fallback to default or error
        print(f"Warning: {params_path} not found.")
        return {}
    with open(params_path, 'r') as f:
        return json.load(f)
