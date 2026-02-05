import sys
import os
import argparse

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from private.admin_runner import BeatCanvasPipeline
from skills.scene_analyzer import SceneAnalyzerSkill

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Describe your scene")
    args = parser.parse_args()

    # --- PHASE 1: THE BRAIN (Analysis) ---
    analyzer = SceneAnalyzerSkill()
    
    try:
        print(f"🎬 Director analyzing: '{args.input}'...")
        analysis = analyzer.analyze_scene(
            scene_description=args.input,
            energy_level="medium"
        )
    finally:
        analyzer.unload() 

    print("\n📋 DIRECTOR'S AUTOMATED PLAN:")
    print(f"   • Engine:     {analysis.checkpoint.upper()}")  # Visual confirmation
    print(f"   • LoRAs:      [{analysis.lora_string}]")
    print(f"   • Reasoning:  {analysis.reasoning}")
    print(f"   • Prompt:     {analysis.enhanced_prompt}")
    print("-" * 50)

    # --- PHASE 2: THE HANDS (Execution) ---
    pipeline = BeatCanvasPipeline()
    
    # CRITICAL UPDATE: Passing the 'checkpoint' argument
    pipeline.run_full_mode(
        prompt=analysis.enhanced_prompt, 
        lora_names=analysis.lora_string,
        checkpoint=analysis.checkpoint 
    )

if __name__ == "__main__":
    main()
