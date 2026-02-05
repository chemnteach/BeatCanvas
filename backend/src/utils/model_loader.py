"""
Model path resolution utility for BeatCanvas backend.
Handles finding models in the symlinked models/ directory.
"""
from pathlib import Path


def get_model_path(model_type: str, filename: str) -> Path:
    """
    Resolve the full path to a model file.

    Args:
        model_type: Subdirectory in models/ (e.g., 'flux', 'wan', 'llm', 'pony')
        filename: Model filename (e.g., 'flux1-schnell-uncensored.gguf')

    Returns:
        Path: Full path to the model file

    Example:
        >>> get_model_path('flux', 'flux1-schnell-uncensored.gguf')
        PosixPath('/home/user/AI_Workspace/synterra/models/flux/flux1-schnell-uncensored.gguf')
    """
    # Get the src directory (where this file is located)
    src_dir = Path(__file__).resolve().parent.parent

    # Go up 3 levels: src -> backend -> beatcanvas -> synterra
    synterra_root = src_dir.parent.parent.parent

    # Construct path: synterra/models/model_type/filename
    model_path = synterra_root / "models" / model_type / filename

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found: {model_path}\n"
            f"Expected location: synterra/models/{model_type}/{filename}"
        )

    return model_path


def validate_models() -> dict:
    """
    Validate that all required models are present.

    Returns:
        dict: Status of each model type
    """
    models_to_check = {
        "flux": "flux1-schnell-uncensored.gguf",
        "wan": "Wan2.1-T2V-14B_Q4_K_M.gguf",
        "llm": "Phi-3-mini-4k-instruct.gguf",
        "pony": "ponyDiffusionV6XL.safetensors"
    }

    status = {}
    for model_type, filename in models_to_check.items():
        try:
            path = get_model_path(model_type, filename)
            status[model_type] = {"status": "OK", "path": str(path)}
        except FileNotFoundError as e:
            status[model_type] = {"status": "MISSING", "error": str(e)}

    return status


if __name__ == "__main__":
    # Quick validation test
    print("Validating model paths...")
    validation = validate_models()

    for model_type, info in validation.items():
        status_icon = "✓" if info["status"] == "OK" else "✗"
        print(f"{status_icon} {model_type}: {info['status']}")
        if info["status"] == "MISSING":
            print(f"  Error: {info['error']}")
