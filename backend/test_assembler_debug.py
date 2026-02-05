"""Debug script to trace video assembly step by step"""
import os
import sys
from pathlib import Path

# Change to backend directory
os.chdir(Path(__file__).parent)

from src.video.assembler import VideoAssembler
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import numpy as np

def test_basic_image_clip():
    """Test 1: Can we create a basic ImageClip?"""
    print("\n=== Test 1: Basic ImageClip ===")

    image_dir = Path("data/generated_images")
    images = sorted([f for f in image_dir.glob("*.png") if f.stat().st_size > 0],
                    key=lambda x: x.stat().st_mtime, reverse=True)

    if not images:
        print("ERROR: No images found")
        return False

    img_path = str(images[0])
    print(f"Using image: {img_path}")
    print(f"Image size: {images[0].stat().st_size} bytes")

    try:
        clip = ImageClip(img_path, duration=2.0)
        print(f"Clip created: size={clip.size}, duration={clip.duration}")

        # Check frame format
        frame = clip.get_frame(0)
        print(f"Frame dtype: {frame.dtype}, shape: {frame.shape}, min={frame.min()}, max={frame.max()}")

        clip.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cinematic_processing():
    """Test 2: Does cinematic processing work?"""
    print("\n=== Test 2: Cinematic Processing ===")

    image_dir = Path("data/generated_images")
    images = sorted([f for f in image_dir.glob("*.png") if f.stat().st_size > 0],
                    key=lambda x: x.stat().st_mtime, reverse=True)

    img_path = str(images[0])

    try:
        clip = ImageClip(img_path, duration=2.0)
        clip = clip.resized((1792, 1024))

        # Check frame format before processing
        frame_before = clip.get_frame(0)
        print(f"BEFORE cinematic - dtype: {frame_before.dtype}, min={frame_before.min():.3f}, max={frame_before.max():.3f}")

        # Apply cinematic processing
        assembler = VideoAssembler()
        processed = assembler._apply_cinematic_processing(clip, {'mood': 'neutral'})

        # Check frame format after processing
        frame_after = processed.get_frame(0)
        print(f"AFTER cinematic - dtype: {frame_after.dtype}, min={frame_after.min():.3f}, max={frame_after.max():.3f}")

        # Verify output range
        if frame_after.max() > 1.0:
            print("WARNING: Frame values exceed 1.0 - MoviePy expects 0-1 for float!")

        processed.close()
        clip.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_concatenate_with_cinematic():
    """Test 3: Can we concatenate clips after cinematic processing?"""
    print("\n=== Test 3: Concatenate with Cinematic ===")

    image_dir = Path("data/generated_images")
    images = sorted([f for f in image_dir.glob("*.png") if f.stat().st_size > 0],
                    key=lambda x: x.stat().st_mtime, reverse=True)[:3]

    assembler = VideoAssembler()
    clips = []

    try:
        for i, img_path in enumerate(images):
            clip = ImageClip(str(img_path), duration=2.0)
            clip = clip.resized((1792, 1024))
            clip = assembler._apply_cinematic_processing(clip, {'mood': 'neutral'})
            clips.append(clip)
            print(f"Clip {i+1} created")

        print("Concatenating clips...")
        final = concatenate_videoclips(clips, method="compose")
        print(f"Final video: duration={final.duration}, size={final.size}")

        # Try to get a frame from middle
        test_frame = final.get_frame(3.0)
        print(f"Frame at 3s: dtype={test_frame.dtype}, min={test_frame.min():.3f}, max={test_frame.max():.3f}")

        final.close()
        for c in clips:
            c.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_write_video():
    """Test 4: Can we write a short test video?"""
    print("\n=== Test 4: Write Video ===")

    image_dir = Path("data/generated_images")
    images = sorted([f for f in image_dir.glob("*.png") if f.stat().st_size > 0],
                    key=lambda x: x.stat().st_mtime, reverse=True)[:3]

    # Find audio
    audio_files = list(Path("data/uploads").glob("*.wav")) + list(Path("data/uploads").glob("*.mp3"))
    if not audio_files:
        print("ERROR: No audio files found")
        return False

    audio_path = str(audio_files[0])
    print(f"Using audio: {audio_path}")

    assembler = VideoAssembler()
    clips = []

    try:
        for i, img_path in enumerate(images):
            clip = ImageClip(str(img_path), duration=2.0)
            clip = clip.resized((1792, 1024))
            clip = assembler._apply_cinematic_processing(clip, {'mood': 'neutral'})
            clips.append(clip)

        final_video = concatenate_videoclips(clips, method="compose")

        # Load audio and trim to video length
        audio = AudioFileClip(audio_path)
        audio = audio.subclipped(0, final_video.duration)

        final_video = final_video.with_audio(audio)

        output_path = "output/debug_cinematic_test.mp4"
        print(f"Writing to {output_path}...")

        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            logger=None  # Suppress progress bar
        )

        # Check file size
        size = Path(output_path).stat().st_size
        print(f"Output size: {size} bytes ({size/1024/1024:.2f} MB)")

        if size < 100000:  # Less than 100KB
            print("WARNING: Output file suspiciously small!")

        final_video.close()
        audio.close()
        for c in clips:
            c.close()

        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("VIDEO ASSEMBLER DEBUG")
    print("=" * 60)

    results = []
    results.append(("Basic ImageClip", test_basic_image_clip()))
    results.append(("Cinematic Processing", test_cinematic_processing()))
    results.append(("Concatenate + Cinematic", test_concatenate_with_cinematic()))
    results.append(("Write Video", test_write_video()))

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
