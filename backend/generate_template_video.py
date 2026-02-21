"""
Template-based video generation - uses proven working prompts.
Skip LLM storyboard, use known-good prompt templates.
"""
from src.cinematography import AnimateDiffGenerator
from src.video.assembler import VideoAssembler
from pathlib import Path
import cv2

# Proven prompt templates (from our successful tests)
PROMPT_TEMPLATES = {
    "beach_family": [
        "close-up of happy children smiling at beach, bright daylight, front-lit faces, visible facial features, colorful swimsuits, playing in sand, photorealistic",
        "diverse family walking on sunny beach, bright daylight, well-lit faces, smiling, holding hands, colorful clothing, blue sky, photorealistic",
        "parents playing with children at beach, bright sunlight, front-lit happy faces, building sandcastles together, vibrant colors, photorealistic",
        "family laughing together on sunny beach, close-up of smiling faces, colorful beach clothes, golden hour lighting, front-lit, photorealistic",
        "children running on beach with family, bright daylight, joyful expressions, well-lit faces, colorful swimwear, clear blue water, photorealistic",
        "family picnic on beach blanket, bright daylight, smiling faces looking at camera, colorful food and drinks, front-lit, photorealistic",
        "group photo of diverse family at beach, bright sunlight, everyone smiling at camera, colorful beach attire, well-lit faces, photorealistic",
        "kids splashing in shallow water, bright daylight, laughing faces, parents watching nearby, colorful swimsuits, front-lit, photorealistic"
    ],
    "urban_phones": [
        "people walking in city looking at phones, bright daylight, isolated individuals, blue-gray tones, disconnected atmosphere, front-lit faces, photorealistic",
        "crowd of people staring at phones, urban setting, bright daylight, separate individuals not interacting, modern dystopia, photorealistic",
        "person alone on phone in busy street, bright daylight, disconnected from surroundings, blue tones, front-lit face, photorealistic",
        "multiple people on phones not talking, urban plaza, bright daylight, isolated despite proximity, cool color grading, photorealistic",
        "commuters all looking at phones, bright daylight, no eye contact, disconnected crowd, urban environment, front-lit, photorealistic",
        "young people sitting separately on phones, bright daylight, no interaction, blue-gray atmosphere, front-lit faces, photorealistic",
        "street scene everyone on devices, bright daylight, isolated individuals, modern disconnection, cool tones, front-lit, photorealistic",
        "people walking past each other on phones, bright daylight, no acknowledgment, urban isolation, blue tones, front-lit faces, photorealistic"
    ],
    "beach_party": [
        "people dancing at beach party, bright bonfire light, joyful expressions, colorful clothes, guitars visible, celebration atmosphere, photorealistic",
        "diverse group celebrating around bonfire, bright firelight on faces, smiling people, musical instruments, warm colors, front-lit, photorealistic",
        "beach party with people singing, bright bonfire and sunset, happy faces, guitars and drums, vibrant clothing, front-lit, photorealistic",
        "friends dancing together at beach, bright bonfire, joyful expressions, colorful party clothes, instruments nearby, warm lighting, photorealistic",
        "people gathered around beach bonfire, bright flames, smiling faces, holding drinks, guitars, warm celebration atmosphere, front-lit, photorealistic",
        "group playing music at beach party, bright bonfire light, happy musicians, colorful clothes, people dancing, warm tones, photorealistic",
        "celebration at beach with bonfire, bright firelight, diverse people laughing, musical instruments, vibrant atmosphere, front-lit faces, photorealistic",
        "beach party finale around bonfire, bright flames, everyone celebrating together, instruments and dancing, warm joyful scene, photorealistic"
    ]
}

NEGATIVE_PROMPT = "silhouette, backlit, dark, shadowy, sunset backlighting, contre-jour, rim lighting, underexposed, low light, blurry, low quality, deformed"

def generate_template_video(audio_path: str, output_path: str = "template_video_test.mp4"):
    """Generate video using template prompts (24 scenes)"""
    
    print("=" * 60)
    print("TEMPLATE-BASED VIDEO GENERATION")
    print("Using proven working prompts")
    print("=" * 60)
    print()
    
    # Generate all scenes
    gen = AnimateDiffGenerator()
    gen.load()
    
    all_frames = []
    scene_num = 0
    
    # 8 beach family scenes
    print("Part 1: Beach Family Scenes (8 scenes)")
    for i, prompt in enumerate(PROMPT_TEMPLATES["beach_family"]):
        scene_num += 1
        print(f"  Scene {scene_num}/24: {prompt[:50]}...")
        
        frames = gen.generate(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            num_frames=16,
            guidance_scale=1.0,
            seed=100 + scene_num,
            width=576,
            height=1024
        )
        all_frames.extend(frames)
        print(f"    ✓ Generated {len(frames)} frames")
    
    # 8 urban phone scenes  
    print("\nPart 2: Urban Phone Scenes (8 scenes)")
    for i, prompt in enumerate(PROMPT_TEMPLATES["urban_phones"]):
        scene_num += 1
        print(f"  Scene {scene_num}/24: {prompt[:50]}...")
        
        frames = gen.generate(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            num_frames=16,
            guidance_scale=1.0,
            seed=100 + scene_num,
            width=576,
            height=1024
        )
        all_frames.extend(frames)
        print(f"    ✓ Generated {len(frames)} frames")
    
    # 8 beach party scenes
    print("\nPart 3: Beach Party Scenes (8 scenes)")
    for i, prompt in enumerate(PROMPT_TEMPLATES["beach_party"]):
        scene_num += 1
        print(f"  Scene {scene_num}/24: {prompt[:50]}...")
        
        frames = gen.generate(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            num_frames=16,
            guidance_scale=1.0,
            seed=100 + scene_num,
            width=576,
            height=1024
        )
        all_frames.extend(frames)
        print(f"    ✓ Generated {len(frames)} frames")
    
    # Save video
    print(f"\n📹 Saving video ({len(all_frames)} total frames)...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 8, (576, 1024))
    
    for frame in all_frames:
        out.write(frame)
    
    out.release()
    gen.kill()
    
    duration = len(all_frames) / 8.0
    
    print(f"\n✅ VIDEO COMPLETE!")
    print(f"   File: {output_path}")
    print(f"   Scenes: 24")
    print(f"   Frames: {len(all_frames)}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Quality: Bright, clear, people-focused")
    print()

if __name__ == "__main__":
    generate_template_video("data/uploads/rob_hill_love_and_saltwater.wav")

