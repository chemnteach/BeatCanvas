import sys
import os
import argparse
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from local.image_generator import LocalImageGenerator
from local.video_generator import LocalVideoGenerator

class BeatCanvasPipeline:
    def __init__(self):
        self.image_gen = LocalImageGenerator()
        self.video_gen = LocalVideoGenerator()

    # UPDATED: Added 'checkpoint' parameter with default 'base'
    def run_full_mode(self, prompt, lora_names=None, checkpoint="base"):
        print("\n🚀 STARTING PIPELINE")
        print(f"   • Engine: {checkpoint}")
        print(f"   • Prompt: {prompt}")
        
        # 1. Generate Image (Passing checkpoint down)
        image = self.image_gen.generate(prompt, lora_names, checkpoint)
        
        timestamp = int(time.time())
        image_path = f"output/image_{timestamp}.png"
        image.save(image_path)
        print(f"✅ Image Saved: {image_path}")

        # 2. Generate Video
        frames = self.video_gen.generate_video(image_path)
        video_path = f"output/video_{timestamp}.mp4"
        self.video_gen.save_video(frames, video_path)
        print(f"✅ Video Saved: {video_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["image", "video", "full"], required=True)
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--lora", type=str, default="none")
    parser.add_argument("--checkpoint", type=str, default="base", help="Checkpoints: base, photoreal") # Added CLI support
    args = parser.parse_args()

    pipeline = BeatCanvasPipeline()

    if args.mode == "full":
        pipeline.run_full_mode(args.prompt, args.lora, args.checkpoint)

if __name__ == "__main__":
    main()
