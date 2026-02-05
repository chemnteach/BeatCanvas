"""
Environment loader that sources from global Claude .env first, then local .env
This ensures API keys are available from the centralized ~/.claude/.env
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_global_env():
    """
    Load environment variables from global Claude .env and local .env
    Priority: local .env overrides global ~/.claude/.env
    """
    # Load global .env first (lower priority)
    global_env = Path.home() / ".claude" / ".env"
    if global_env.exists():
        load_dotenv(dotenv_path=global_env, override=False)
        print(f"[ENV] Loaded global config from {global_env}")
    else:
        print("[ENV] No global config found at ~/.claude/.env")

    # Load local .env (higher priority - overrides global)
    local_env = Path(".env")
    if local_env.exists():
        load_dotenv(dotenv_path=local_env, override=True)
        print(f"[ENV] Loaded local config from {local_env}")
    else:
        print("[ENV] No local .env file found")

    # Validate critical API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "your_openai_api_key_here":
        print("[WARNING] OpenAI API key not configured")
        return False
    else:
        print("[ENV] OpenAI API key loaded successfully")
        return True


def get_api_key(service: str) -> str:
    """
    Get API key for a specific service

    Args:
        service: API service name (openai, novelai, replicate, etc.)

    Returns:
        API key string or empty string if not found
    """
    key_mapping = {
        'openai': 'OPENAI_API_KEY',
        'novelai': 'NOVELAI_API_KEY',
        'replicate': 'REPLICATE_API_TOKEN',
        'midjourney': 'MIDJOURNEY_API_KEY',
        # Google/Gemini keys for Nano Banana image generation
        'google': 'GOOGLE_AI_API_KEY',
        'gemini': 'GOOGLE_AI_API_KEY',
        'google_ai': 'GOOGLE_AI_API_KEY',
        'nano_banana': 'GOOGLE_AI_API_KEY',
    }

    env_var = key_mapping.get(service.lower())
    if not env_var:
        print(f"[ERROR] Unknown service: {service}")
        return ""

    key = os.getenv(env_var, "")
    if key and key != f"your_{service.lower()}_api_key_here":
        return key
    else:
        print(f"[WARNING] {service} API key not configured")
        return ""


def get_path(name: str, default: Path = None) -> Path:
    """
    Get a path from environment variables.

    Machine-specific paths should be in .env, not in code.

    Args:
        name: Path name (e.g., 'svd_output' -> SVD_OUTPUT_DIR)
        default: Fallback path if env var not set

    Returns:
        Path object
    """
    path_mapping = {
        'svd_output': 'SVD_OUTPUT_DIR',
        'models': 'MODELS_DIR',
        'loras': 'LORAS_DIR',
        'windows_downloads': 'WINDOWS_DOWNLOADS',
        'rife_engine': 'RIFE_ENGINE_PATH',
    }

    env_var = path_mapping.get(name.lower())
    if not env_var:
        if default:
            return default
        raise ValueError(f"Unknown path name: {name}")

    path_str = os.getenv(env_var)
    if path_str:
        return Path(path_str)
    elif default:
        return default
    else:
        raise ValueError(f"{env_var} not set and no default provided")


# Auto-load when module is imported
if __name__ != "__main__":
    load_global_env()