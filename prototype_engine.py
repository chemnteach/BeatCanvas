"""
Rapid prototype for local AI video generation.

Pipeline: Text → Flux.1-schnell (image) → LTX-Video (video) → MP4
Optimized for 16GB VRAM NVIDIA GPUs.

Usage:
    python prototype_engine.py

Output:
    test_render.mp4 (768x512, 5 seconds, 24fps)
"""

import gc
import torch
from PIL import Image


def clear_memory():
    """Release GPU memory between model loads."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def generate_image(prompt: str, seed: int = 42) -> Image.Image:
    """
    Generate an image using Flux.1-schnell.

    Args:
        prompt: Text description of the image to generate
        seed: Random seed for reproducibility

    Returns:
        PIL Image (1024x576)
    """
    from diffusers import FluxPipeline

    print("[IMAGE] Loading Flux.1-schnell...")
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16
    )
    pipe.enable_model_cpu_offload()

    print("[IMAGE] Generating image...")
    result = pipe(
        prompt=prompt,
        height=576,
        width=1024,
        num_inference_steps=4,
        guidance_scale=0.0,  # Must be 0 for schnell
        max_sequence_length=256,
        generator=torch.Generator("cpu").manual_seed(seed)
    )
    image = result.images[0]

    # Save intermediate image for inspection
    image.save("test_image.png")
    print("[IMAGE] Saved intermediate image to test_image.png")

    # Unload Flux before loading LTX
    del pipe
    clear_memory()
    print("[IMAGE] Flux unloaded, memory cleared")

    return image


def generate_video(image: Image.Image, motion_prompt: str, output_path: str = "test_render.mp4") -> str:
    """
    Animate an image using LTX-Video.

    Args:
        image: PIL Image to animate
        motion_prompt: Description of desired motion/animation
        output_path: Where to save the output video

    Returns:
        Path to the saved video file
    """
    from diffusers import LTXImageToVideoPipeline
    from diffusers.utils import export_to_video

    print("[VIDEO] Loading LTX-Video...")
    pipe = LTXImageToVideoPipeline.from_pretrained(
        "Lightricks/LTX-Video",
        torch_dtype=torch.bfloat16
    )
    pipe.to("cuda")
    pipe.vae.enable_tiling()  # Memory optimization

    # Resize image to LTX native resolution
    image_resized = image.resize((768, 512), Image.Resampling.LANCZOS)

    print("[VIDEO] Generating video (this may take a few minutes)...")
    result = pipe(
        image=image_resized,
        prompt=motion_prompt,
        negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, static, frozen",
        width=768,
        height=512,
        num_frames=121,  # 5 seconds at 24fps (must be 8n+1)
        num_inference_steps=50,
    )
    video_frames = result.frames[0]

    export_to_video(video_frames, output_path, fps=24)
    print(f"[VIDEO] Saved video to {output_path}")

    # Cleanup
    del pipe
    clear_memory()

    return output_path


def main():
    """
    Main entry point. Modify the prompts below to test different generations.
    """
    # ========== MODIFY THESE PROMPTS ==========

    image_prompt = (
        "A cinematic wide shot of a serene Japanese garden at golden hour, "
        "with a traditional wooden bridge over a koi pond, cherry blossom trees "
        "in full bloom, soft pink petals floating in the air, warm sunset light "
        "casting long shadows, photorealistic, 8k, masterpiece"
    )

    motion_prompt = (
        "Camera slowly pans right across the tranquil garden scene, "
        "cherry blossom petals gently drift downward through the warm light, "
        "subtle ripples form on the pond surface, leaves sway gently in a soft breeze, "
        "cinematic smooth motion"
    )

    seed = 42  # Change for different variations

    # ==========================================

    print("=" * 60)
    print("PROTOTYPE ENGINE - Local AI Video Generation")
    print("=" * 60)
    print(f"Image prompt: {image_prompt[:80]}...")
    print(f"Motion prompt: {motion_prompt[:80]}...")
    print("=" * 60)

    # Check CUDA availability
    if not torch.cuda.is_available():
        print("[ERROR] CUDA not available. This script requires an NVIDIA GPU.")
        return

    device_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"[GPU] {device_name} ({vram_gb:.1f} GB VRAM)")
    print()

    # Step 1: Generate image
    image = generate_image(image_prompt, seed=seed)

    # Step 2: Animate image to video
    output_path = generate_video(image, motion_prompt)

    print()
    print("=" * 60)
    print(f"[DONE] Video saved to: {output_path}")
    print(f"[DONE] Intermediate image saved to: test_image.png")
    print("=" * 60)


if __name__ == "__main__":
    main()
