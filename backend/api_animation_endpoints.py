"""
Animation Workflow API Endpoints

Add these endpoints to main.py to enable animation video generation in the UI.

These endpoints provide:
- Animation style listing
- Character LoRA management
- Animation video generation workflow
- Project config management
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
import yaml

# Create router
animation_router = APIRouter(prefix="/api/animation", tags=["animation"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AnimationStyleInfo(BaseModel):
    """Information about an animation style"""
    name: str
    description: str
    best_for: str
    prompt_suffix: str


class AnimationProjectRequest(BaseModel):
    """Request to generate animated music video"""
    task_id: str
    audio_path: str
    animation_style: str
    protagonist_lora: Optional[str] = None
    supporting_loras: Optional[List[str]] = None
    scene_loras: Optional[List[str]] = None
    style_lora: Optional[str] = None
    quality_tier: str = "professional"
    use_stock_footage: bool = False
    stock_footage_queries: Optional[List[str]] = None
    fps: int = 24
    width: int = 1024
    height: int = 1024


class SaveProjectConfigRequest(BaseModel):
    """Save animation project configuration"""
    project_name: str
    config: Dict


# ============================================================================
# Endpoints
# ============================================================================

@animation_router.get("/styles")
async def list_animation_styles():
    """
    List all available animation styles with descriptions.

    Returns 16 animation styles categorized by genre.
    """
    from src.animation.rotoscope_generator import ANIMATION_STYLES

    styles = []
    for name, config in ANIMATION_STYLES.items():
        styles.append({
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "description": config["prompt_suffix"],
            "best_for": config.get("best_for", "Various genres"),
            "guidance_scale": config["guidance_scale"],
            "conditioning_scale": config["controlnet_conditioning_scale"]
        })

    return {
        "total_styles": len(styles),
        "styles": styles,
        "categories": {
            "tropical": ["watercolor", "cel_shaded", "impressionist", "pop_art"],
            "rock": ["comic_book", "graffiti", "pencil_sketch", "neon"],
            "electronic": ["synthwave", "neon", "pixel_art"],
            "jazz_classical": ["art_deco", "oil_painting", "impressionist"],
            "world_indie": ["ukiyo_e", "ghibli", "paper_cutout"],
            "pop": ["cartoon", "pop_art", "cel_shaded"]
        }
    }


@animation_router.get("/loras")
async def list_character_loras():
    """
    List all trained character LoRAs available for animation.

    Returns character, scene, and style LoRAs from registry.
    """
    lora_registry_path = Path("backend/config/loras.yaml")

    if not lora_registry_path.exists():
        return {
            "character_loras": [],
            "scene_loras": [],
            "style_loras": [],
            "message": "No LoRA registry found"
        }

    with open(lora_registry_path, 'r') as f:
        registry = yaml.safe_load(f)

    character_loras = []
    scene_loras = []
    style_loras = []

    for name, config in registry.items():
        if not config.get('enabled', False):
            continue

        lora_info = {
            "name": name,
            "display_name": name.replace("-", " ").replace("_", " ").title(),
            "type": config.get("type", "unknown"),
            "description": config.get("description", ""),
            "file": config.get("file", ""),
            "trigger": config.get("triggers", [None])[0] if config.get("triggers") else None,
            "default_weight": config.get("default_weight", 0.7)
        }

        lora_type = config.get("type", "")
        if lora_type == "character":
            character_loras.append(lora_info)
        elif lora_type == "scene":
            scene_loras.append(lora_info)
        elif lora_type == "style":
            style_loras.append(lora_info)

    return {
        "character_loras": character_loras,
        "scene_loras": scene_loras,
        "style_loras": style_loras,
        "total": len(character_loras) + len(scene_loras) + len(style_loras)
    }


@animation_router.post("/generate")
async def generate_animation_video(request: AnimationProjectRequest):
    """
    Generate animated music video using character LoRAs and animation style.

    This is the main endpoint for creating animation videos.
    Runs the full pipeline: audio → character scenes → rotoscope → final video.
    """
    try:
        from src.animation.animation_workflow import AnimationWorkflow, AnimationProjectConfig
        import asyncio

        # Create project config from request
        config = AnimationProjectConfig(
            project_name=f"project_{request.task_id[:8]}",
            audio_path=request.audio_path,
            animation_style=request.animation_style,
            quality_tier=request.quality_tier,
            protagonist_lora=request.protagonist_lora,
            supporting_loras=request.supporting_loras,
            scene_loras=request.scene_loras,
            style_lora=request.style_lora,
            use_stock_footage=request.use_stock_footage,
            stock_footage_queries=request.stock_footage_queries,
            fps=request.fps,
            width=request.width,
            height=request.height
        )

        # Run workflow in background
        workflow = AnimationWorkflow()

        # Start workflow asynchronously
        asyncio.create_task(run_animation_workflow(request.task_id, workflow, config))

        return {
            "task_id": request.task_id,
            "status": "started",
            "animation_style": request.animation_style,
            "message": "Animation video generation started"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start animation: {str(e)}")


async def run_animation_workflow(task_id: str, workflow, config):
    """Background task for animation workflow"""
    # Import active_tasks from main
    from main import active_tasks

    try:
        # Create task entry if not exists
        if task_id not in active_tasks:
            active_tasks[task_id] = {
                "id": task_id,
                "status": "animating",
                "progress": "Starting animation workflow...",
            }

        task = active_tasks[task_id]
        task["status"] = "animating"
        task["progress"] = "Running animation workflow..."

        # Run workflow
        result = await workflow.run_workflow(config)

        if result.success:
            task["status"] = "complete"
            task["progress"] = "Animation complete!"
            task["video_url"] = f"/api/download/{task_id}_animation"
            task["output_path"] = result.output_video_path
        else:
            task["status"] = "error"
            task["progress"] = f"Animation failed: {result.error}"

    except Exception as e:
        task = active_tasks.get(task_id, {})
        task["status"] = "error"
        task["progress"] = f"Animation error: {str(e)}"
        import traceback
        traceback.print_exc()


@animation_router.post("/upload-character-lora")
async def upload_character_lora(
    name: str,
    lora_file: UploadFile = File(...),
    trigger: str = "ohwx",
    description: str = ""
):
    """
    Upload a trained character LoRA for use in animations.

    Saves to output/loras/ and updates registry.
    """
    try:
        # Save LoRA file
        lora_dir = Path("output/loras") / name
        lora_dir.mkdir(parents=True, exist_ok=True)

        lora_path = lora_dir / f"{name}.safetensors"

        with open(lora_path, "wb") as f:
            content = await lora_file.read()
            f.write(content)

        # Update registry
        registry_path = Path("backend/config/loras.yaml")

        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry = yaml.safe_load(f) or {}
        else:
            registry = {}

        # Add to registry
        registry[name] = {
            "description": description or f"Custom character: {name}",
            "type": "character",
            "triggers": [trigger],
            "file": f"{name}/{name}.safetensors",
            "default_weight": 0.8,
            "enabled": True,
            "source": "custom"
        }

        with open(registry_path, 'w') as f:
            yaml.dump(registry, f, default_flow_style=False)

        return {
            "name": name,
            "path": str(lora_path),
            "trigger": trigger,
            "status": "uploaded",
            "message": f"Character LoRA '{name}' uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@animation_router.get("/projects")
async def list_animation_projects():
    """List all saved animation project configs"""
    projects_dir = Path("config/animation_projects")

    if not projects_dir.exists():
        return {"projects": []}

    projects = []
    for config_file in projects_dir.glob("*.yaml"):
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                projects.append({
                    "name": config_file.stem,
                    "config": config
                })
        except:
            continue

    return {"projects": projects, "total": len(projects)}


@animation_router.post("/save-project")
async def save_project_config(request: SaveProjectConfigRequest):
    """Save animation project configuration for reuse"""
    try:
        projects_dir = Path("config/animation_projects")
        projects_dir.mkdir(parents=True, exist_ok=True)

        config_path = projects_dir / f"{request.project_name}.yaml"

        with open(config_path, 'w') as f:
            yaml.dump(request.config, f, default_flow_style=False)

        return {
            "project_name": request.project_name,
            "config_path": str(config_path),
            "status": "saved",
            "message": f"Project '{request.project_name}' saved successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")


# Export router for inclusion in main.py
__all__ = ['animation_router']
