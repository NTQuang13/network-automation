import csv, yaml

def load_inventory(path):
    if path.endswith((".yaml", ".yml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        defaults = data.get("defaults", {})
        return [{**defaults, **d} for d in data["devices"]]
    with open(path, newline="") as f:
        return list(csv.DictReader(f))