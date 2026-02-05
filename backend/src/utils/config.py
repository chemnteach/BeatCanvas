import yaml
import os
from pathlib import Path

# specific logic to find the file relative to this script
# Structure: backend/src/utils/config.py -> go up 2 levels to backend -> then down to config/settings.yaml
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

# Load immediately so it's available as a constant
SETTINGS = load_config()
