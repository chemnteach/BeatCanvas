"""
Auto-Caption Tool for LoRA Training Datasets

Generates .txt caption files for each image in a dataset folder
using Florence-2 (4GB VRAM) or Joy-Caption (8-10GB VRAM).

Usage:
    python tools/auto_caption.py datasets/tiki-bar-interior/
    python tools/auto_caption.py datasets/beach-sunset/ --trigger "beach_sunset"
    python tools/auto_caption.py datasets/artist-john/ --trigger "ohwx" --model joy-caption
    python tools/auto_caption.py datasets/my-lora/ --overwrite

Each image gets a matching .txt file:
    img_001.jpg → img_001.txt ("a photo of ohwx, tropical tiki bar with bamboo...")

Requires: transformers, torch, Pillow
Florence-2 needs ~4GB VRAM. Joy-Caption needs ~8-10GB.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def find_images(dataset_dir: Path) -> List[Path]:
    """Find all images in a dataset directory."""
    images = []
    for f in sorted(dataset_dir.iterdir()):
        if f.suffix.lower() in IMAGE_EXTENSIONS and not f.name.startswith("_"):
            images.append(f)
    return images


def needs_caption(image_path: Path, overwrite: bool = False) -> bool:
    """Check if an image needs captioning."""
    caption_path = image_path.with_suffix(".txt")
    if overwrite:
        return True
    return not caption_path.exists()


def caption_with_florence2(
    images: List[Path],
    trigger_word: str = "",
    prefix: str = "",
) -> List[Tuple[Path, str]]:
    """
    Caption images using Microsoft Florence-2.
    ~4GB VRAM, ~0.5s per image. Good general-purpose captions.
    """
    import torch
    from transformers import AutoProcessor, AutoModelForCausalLM
    from PIL import Image

    model_id = "microsoft/Florence-2-large"
    print(f"Loading Florence-2 from {model_id}...")

    # Use float16 on GPU, float32 on CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        trust_remote_code=True,
        attn_implementation="eager"  # Fix for transformers 4.57+ compatibility
    ).to(device)

    print(f"Florence-2 loaded on {device} ({dtype})")
    results = []

    for i, img_path in enumerate(images):
        print(f"  [{i+1}/{len(images)}] {img_path.name}...", end=" ", flush=True)
        start = time.time()

        try:
            image = Image.open(img_path).convert("RGB")
            inputs = processor(
                text="<MORE_DETAILED_CAPTION>",
                images=image,
                return_tensors="pt",
            ).to(device, dtype)

            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=256,
                do_sample=False,
            )
            caption = processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]

            # Clean up the caption
            caption = caption.strip()
            # Remove the task prefix if Florence includes it
            if caption.startswith("<MORE_DETAILED_CAPTION>"):
                caption = caption[len("<MORE_DETAILED_CAPTION>"):].strip()

            # Add trigger word and prefix
            parts = []
            if trigger_word:
                parts.append(f"a photo of {trigger_word}")
            if prefix:
                parts.append(prefix)
            parts.append(caption)
            full_caption = ", ".join(parts)

            elapsed = time.time() - start
            print(f"({elapsed:.1f}s) {full_caption[:80]}...")
            results.append((img_path, full_caption))

        except Exception as e:
            print(f"ERROR: {e}")
            # Write a basic caption so training doesn't skip this image
            fallback = f"a photo of {trigger_word}" if trigger_word else "a photograph"
            results.append((img_path, fallback))

    # Cleanup
    del model, processor
    if torch.cuda.is_available():
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    return results


def caption_with_joy(
    images: List[Path],
    trigger_word: str = "",
    prefix: str = "",
) -> List[Tuple[Path, str]]:
    """
    Caption images using Joy-Caption Alpha Two.
    ~8-10GB VRAM, slower but better for LoRA training specifically.
    Understands what details matter for identity preservation.
    """
    # Joy-Caption requires more setup - check availability
    try:
        import torch
        from transformers import AutoProcessor, LlavaForConditionalGeneration
        from PIL import Image
    except ImportError:
        print("ERROR: Joy-Caption requires additional dependencies.")
        print("Install: pip install transformers torch pillow")
        sys.exit(1)

    model_id = "fancyfeast/llama-joycaption-alpha-two-hf-llava"
    print(f"Loading Joy-Caption from {model_id}...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    processor = AutoProcessor.from_pretrained(model_id)
    model = LlavaForConditionalGeneration.from_pretrained(
        model_id, torch_dtype=dtype
    ).to(device)

    print(f"Joy-Caption loaded on {device}")
    results = []

    # Joy-Caption prompt optimized for LoRA training
    caption_prompt = (
        "Write a detailed caption for this image suitable for AI image generation training. "
        "Describe the subject's appearance, clothing, pose, expression, setting, lighting, "
        "and art style in a single paragraph. Be specific about visual details."
    )

    for i, img_path in enumerate(images):
        print(f"  [{i+1}/{len(images)}] {img_path.name}...", end=" ", flush=True)
        start = time.time()

        try:
            image = Image.open(img_path).convert("RGB")

            convo = [
                {"role": "system", "content": "You are a helpful image captioner."},
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": caption_prompt},
                    ],
                },
            ]
            convo_string = processor.apply_chat_template(
                convo, tokenize=False, add_generation_prompt=True
            )
            inputs = processor(
                text=[convo_string], images=[image], return_tensors="pt"
            ).to(device)
            inputs["pixel_values"] = inputs["pixel_values"].to(dtype)

            generated_ids = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.6,
            )
            # Trim input tokens from output
            generated_ids = generated_ids[:, inputs["input_ids"].shape[1]:]
            caption = processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0].strip()

            # Add trigger word
            parts = []
            if trigger_word:
                parts.append(f"a photo of {trigger_word}")
            if prefix:
                parts.append(prefix)
            parts.append(caption)
            full_caption = ", ".join(parts)

            elapsed = time.time() - start
            print(f"({elapsed:.1f}s) {full_caption[:80]}...")
            results.append((img_path, full_caption))

        except Exception as e:
            print(f"ERROR: {e}")
            fallback = f"a photo of {trigger_word}" if trigger_word else "a photograph"
            results.append((img_path, fallback))

    del model, processor
    if torch.cuda.is_available():
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    return results


def save_captions(results: List[Tuple[Path, str]]) -> int:
    """Save caption text files alongside images."""
    saved = 0
    for img_path, caption in results:
        caption_path = img_path.with_suffix(".txt")
        caption_path.write_text(caption, encoding="utf-8")
        saved += 1
    return saved


def main():
    parser = argparse.ArgumentParser(
        description="Auto-caption images for LoRA training datasets"
    )
    parser.add_argument(
        "dataset_dir", help="Path to dataset directory containing images"
    )
    parser.add_argument(
        "--trigger",
        type=str,
        default="",
        help="Trigger word to prepend (e.g., 'ohwx' for character, 'beach_sunset' for style)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Additional prefix after trigger word (e.g., 'tropical beach scene')",
    )
    parser.add_argument(
        "--model",
        choices=["florence2", "joy-caption"],
        default="florence2",
        help="Captioning model (default: florence2, ~4GB VRAM)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing caption files",
    )

    args = parser.parse_args()
    dataset_dir = Path(args.dataset_dir)

    if not dataset_dir.exists():
        print(f"ERROR: Directory not found: {dataset_dir}")
        sys.exit(1)

    # Find images needing captions
    all_images = find_images(dataset_dir)
    images_to_caption = [
        img for img in all_images if needs_caption(img, args.overwrite)
    ]

    print(f"Dataset: {dataset_dir}")
    print(f"Total images: {len(all_images)}")
    print(f"Need captioning: {len(images_to_caption)}")
    if args.trigger:
        print(f"Trigger word: {args.trigger}")
    print(f"Model: {args.model}")
    print()

    if not images_to_caption:
        print("All images already captioned. Use --overwrite to redo.")
        return

    # Run captioning
    if args.model == "florence2":
        results = caption_with_florence2(
            images_to_caption,
            trigger_word=args.trigger,
            prefix=args.prefix,
        )
    else:
        results = caption_with_joy(
            images_to_caption,
            trigger_word=args.trigger,
            prefix=args.prefix,
        )

    # Save
    saved = save_captions(results)
    print()
    print(f"Done! Saved {saved} caption files.")
    print(f"Dataset ready for training: {dataset_dir}")


if __name__ == "__main__":
    main()
