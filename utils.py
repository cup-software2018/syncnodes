import sys
import yaml

def load_inventory(file_path: str) -> list:
    """Load node inventory from a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('nodes', [])
    except FileNotFoundError:
        print(f"[Error] Inventory file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"[Error] YAML parsing error: {e}", file=sys.stderr)
        sys.exit(1)
