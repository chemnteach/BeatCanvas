import librosa
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCENE TIMING CONFIGURATION - Image-to-Video Upgrade
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Scene duration constraints (prevents machine-gun cuts and visual fatigue)
MIN_SCENE_DURATION = 2.5  # seconds - Luma needs ~3-5s to show motion
MAX_SCENE_DURATION = 8.0  # seconds - avoid visual fatigue

# Target scene counts for music video feel
DEFAULT_SCENE_COUNT = 60  # Up from 24 for music video feel
HERO_SCENE_RATIO = 0.25   # 25% of scenes get video treatment

@dataclass
class MusicSegment:
    start_time: float
    end_time: float
    tempo: float
    energy: float
    mood: str
    beat_strength: float

class MusicAnalyzer:
    def __init__(self):
        # Ensure ffmpeg is available for audio processing
        pass

    def analyze_song(self, audio_file: str) -> Dict:
        """Extract musical structure and emotional content"""
        try:
            # Load audio file
            y, sr = librosa.load(audio_file)

            # Extract basic features
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            mfcc = librosa.feature.mfcc(y=y, sr=sr)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)

            # Detect song structure (verse, chorus, bridge)
            segments = self._detect_song_structure(y, sr, beats)

            # Analyze emotional content per segment
            for segment in segments:
                segment.mood = self._analyze_mood(y, sr, segment)
                segment.tempo = tempo
                segment.beat_strength = self._calculate_beat_strength(y, sr, segment)

            # Calculate overall mood from all segments
            if segments:
                segment_moods = [seg.mood for seg in segments]
                overall_mood = max(set(segment_moods), key=segment_moods.count)  # Most common mood
            else:
                overall_mood = "neutral"

            return {
                'duration': len(y) / sr,
                'tempo': float(tempo),
                'segments': [self._segment_to_dict(seg) for seg in segments],
                'overall_energy': float(np.mean(spectral_centroids)),
                'overall_mood': overall_mood,
                'beat_times': librosa.frames_to_time(beats, sr=sr).tolist(),
                'sample_rate': int(sr),
                'audio_features': {
                    'spectral_centroid_mean': float(np.mean(spectral_centroids)),
                    'spectral_centroid_std': float(np.std(spectral_centroids)),
                    'mfcc_mean': np.mean(mfcc, axis=1).tolist(),
                    'chroma_mean': np.mean(chroma, axis=1).tolist()
                }
            }

        except Exception as e:
            raise Exception(f"Error analyzing audio: {str(e)}")

    def _detect_song_structure(self, y, sr, beats) -> List[MusicSegment]:
        """Identify verses, choruses, bridges based on audio similarity"""
        try:
            # Use librosa's segment detection
            S = librosa.feature.chroma_stft(y=y, sr=sr)
            boundaries = librosa.segment.agglomerative(S, k=min(8, len(S[0])//10))

            segments = []
            for i, boundary in enumerate(boundaries[:-1]):
                start_time = librosa.frames_to_time(boundary, sr=sr)
                end_time = librosa.frames_to_time(boundaries[i+1], sr=sr)

                # Extract energy for this segment
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                segment_y = y[start_sample:end_sample]

                if len(segment_y) > 0:
                    energy = float(np.mean(librosa.feature.rms(y=segment_y)))
                else:
                    energy = 0.0

                segments.append(MusicSegment(
                    start_time=float(start_time),
                    end_time=float(end_time),
                    tempo=0.0,  # Will be filled later
                    energy=energy,
                    mood="",  # Will be filled later
                    beat_strength=0.0
                ))

            return segments

        except Exception as e:
            # Fallback: create segments based on duration
            duration = len(y) / sr
            segment_length = min(10.0, duration / 4)  # 4 segments max
            segments = []

            for i in range(int(duration / segment_length)):
                start_time = i * segment_length
                end_time = min((i + 1) * segment_length, duration)

                segments.append(MusicSegment(
                    start_time=start_time,
                    end_time=end_time,
                    tempo=0.0,
                    energy=0.5,  # Default
                    mood="neutral",
                    beat_strength=0.5
                ))

            return segments

    def _analyze_mood(self, y, sr, segment: MusicSegment) -> str:
        """Analyze emotional content of a segment"""
        try:
            start_sample = int(segment.start_time * sr)
            end_sample = int(segment.end_time * sr)
            segment_y = y[start_sample:end_sample]

            if len(segment_y) == 0:
                return "neutral"

            # Simple mood analysis based on spectral features
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=segment_y, sr=sr))
            energy = segment.energy
            tempo_factor = 120.0 / max(segment.tempo, 1.0)  # Normalize to 120 BPM

            # Classification logic
            if energy > 0.7 and spectral_centroid > 2000:
                return "energetic"
            elif energy < 0.3:
                return "calm"
            elif spectral_centroid < 1000:
                return "dark"
            elif spectral_centroid > 3000:
                return "bright"
            else:
                return "neutral"

        except Exception:
            return "neutral"

    def _calculate_beat_strength(self, y, sr, segment: MusicSegment) -> float:
        """Calculate beat strength for a segment"""
        try:
            start_sample = int(segment.start_time * sr)
            end_sample = int(segment.end_time * sr)
            segment_y = y[start_sample:end_sample]

            if len(segment_y) == 0:
                return 0.5

            # Calculate onset strength
            onset_frames = librosa.onset.onset_detect(y=segment_y, sr=sr)
            beat_strength = len(onset_frames) / max(segment.end_time - segment.start_time, 1.0)

            # Normalize to 0-1 range
            return min(beat_strength / 10.0, 1.0)

        except Exception:
            return 0.5

    def _segment_to_dict(self, segment: MusicSegment) -> Dict:
        """Convert segment to dictionary for JSON serialization"""
        return {
            'start_time': segment.start_time,
            'end_time': segment.end_time,
            'tempo': segment.tempo,
            'energy': segment.energy,
            'mood': segment.mood,
            'beat_strength': segment.beat_strength
        }

    def get_scene_timings(self, music_data: Dict, target_scene_count: int = DEFAULT_SCENE_COUNT) -> List[Tuple[float, float]]:
        """Generate optimal scene timing based on music structure"""
        duration = music_data['duration']
        segments = music_data['segments']

        # If we have natural segments, use them as base
        if len(segments) >= target_scene_count // 2:
            # Use segments as scenes
            return [(seg['start_time'], seg['end_time']) for seg in segments]

        # Otherwise, create evenly spaced scenes with beat alignment
        beat_times = music_data['beat_times']
        scene_duration = duration / target_scene_count

        scenes = []
        for i in range(target_scene_count):
            start_time = i * scene_duration

            # Align to nearest beat
            if beat_times:
                start_beat = min(beat_times, key=lambda x: abs(x - start_time))
                start_time = start_beat

            end_time = min(start_time + scene_duration, duration)

            if end_time > start_time:
                scenes.append((start_time, end_time))

        return scenes

    def subdivide_by_beats(self, beat_times: List[float], duration: float,
                          min_dur: float = MIN_SCENE_DURATION,
                          max_dur: float = MAX_SCENE_DURATION) -> List[float]:
        """
        Create scene boundaries from beats with duration constraints.
        Returns list of boundary timestamps (scene starts).

        Args:
            beat_times: List of beat timestamps from librosa
            duration: Total song duration
            min_dur: Minimum scene duration (prevents machine-gun cuts)
            max_dur: Maximum scene duration (prevents visual fatigue)

        Returns:
            List of scene boundary timestamps
        """
        if not beat_times:
            # Fallback: evenly spaced scenes
            num_scenes = max(1, int(duration / ((min_dur + max_dur) / 2)))
            return [i * duration / num_scenes for i in range(num_scenes)]

        scene_boundaries = [0.0]

        for beat in beat_times:
            last_boundary = scene_boundaries[-1]
            time_since_last = beat - last_boundary

            # Only add boundary if we've exceeded minimum duration
            if time_since_last >= min_dur:
                scene_boundaries.append(beat)
            # Force a cut if we've exceeded maximum duration
            elif time_since_last >= max_dur:
                # Find the closest beat that's at least min_dur away
                valid_beats = [b for b in beat_times if b - last_boundary >= min_dur]
                if valid_beats:
                    scene_boundaries.append(min(valid_beats, key=lambda b: abs(b - last_boundary - max_dur/2)))

        # Handle final segment - merge if too short
        if len(scene_boundaries) > 1:
            final_duration = duration - scene_boundaries[-1]
            if final_duration < min_dur:
                scene_boundaries.pop()

        return scene_boundaries

    def align_to_nearest_beat(self, target_time: float, beat_times: List[float]) -> float:
        """Snap a time to the nearest beat for professional timing"""
        if not beat_times:
            return target_time
        return min(beat_times, key=lambda b: abs(b - target_time))

    def classify_scene_type(self, segment: Dict, position: float,
                           total_duration: float, segments: List[Dict] = None) -> str:
        """
        Classify a scene as 'hero' (gets video treatment) or 'standard' (Ken Burns).

        Hero scenes are identified by:
        - High energy moments (top 25%)
        - Climax position (last 25% of song)
        - Chorus/hook sections (if labeled)

        Args:
            segment: Music segment data with energy, mood, etc.
            position: Current position in song (seconds)
            total_duration: Total song duration
            segments: All segments (for energy percentile calculation)

        Returns:
            'hero' or 'standard'
        """
        # Calculate energy threshold (top 25% = hero)
        if segments:
            energies = [s.get('energy', 0.5) for s in segments]
            energy_threshold = np.percentile(energies, 75)
        else:
            energy_threshold = 0.7

        is_climax = position > (total_duration * 0.75)
        is_high_energy = segment.get('energy', 0.5) >= energy_threshold
        is_chorus = segment.get('label', '').lower() in ['chorus', 'hook', 'drop', 'climax']

        if is_climax or is_high_energy or is_chorus:
            return "hero"
        return "standard"

    def get_enhanced_scene_timings(self, music_data: Dict,
                                   target_scene_count: int = DEFAULT_SCENE_COUNT,
                                   hero_ratio: float = HERO_SCENE_RATIO) -> List[Dict]:
        """
        Generate scene timings with beat alignment and scene type classification.

        This is the enhanced version for the image-to-video upgrade that:
        1. Uses beat-synced boundaries with min/max duration constraints
        2. Classifies each scene as 'hero' (video) or 'standard' (Ken Burns)
        3. Returns rich scene data including timing, type, and energy

        Args:
            music_data: Full music analysis data
            target_scene_count: Target number of scenes (default 60 for music video feel)
            hero_ratio: Fraction of scenes that should be hero scenes (default 0.25)

        Returns:
            List of dicts with: start_time, end_time, scene_type, energy, mood
        """
        duration = music_data['duration']
        beat_times = music_data.get('beat_times', [])
        segments = music_data.get('segments', [])

        # Create beat-synced boundaries
        boundaries = self.subdivide_by_beats(beat_times, duration)

        # Ensure we have enough scenes (subdivide if needed)
        while len(boundaries) < target_scene_count and len(boundaries) > 1:
            new_boundaries = []
            for i, b in enumerate(boundaries[:-1]):
                new_boundaries.append(b)
                mid = (b + boundaries[i+1]) / 2
                # Only add midpoint if it respects minimum duration
                if (mid - b >= MIN_SCENE_DURATION and
                    boundaries[i+1] - mid >= MIN_SCENE_DURATION):
                    # Snap to nearest beat if possible
                    if beat_times:
                        mid = self.align_to_nearest_beat(mid, beat_times)
                    new_boundaries.append(mid)
            new_boundaries.append(boundaries[-1])
            boundaries = sorted(set(new_boundaries))

        # Build scene list with classifications
        scenes = []
        for i in range(len(boundaries)):
            start_time = boundaries[i]
            end_time = boundaries[i + 1] if i + 1 < len(boundaries) else duration

            # Skip if too short
            if end_time - start_time < MIN_SCENE_DURATION / 2:
                continue

            # Find segment data for this time
            segment = self._find_segment_for_time(segments, start_time)

            # Classify scene type
            scene_type = self.classify_scene_type(
                segment, start_time, duration, segments
            )

            scenes.append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'scene_type': scene_type,
                'energy': segment.get('energy', 0.5),
                'mood': segment.get('mood', 'neutral'),
                'beat_strength': segment.get('beat_strength', 0.5)
            })

        # Enforce hero ratio - ensure we don't exceed the limit
        hero_count = sum(1 for s in scenes if s['scene_type'] == 'hero')
        max_hero = int(len(scenes) * hero_ratio)

        if hero_count > max_hero:
            # Demote lowest-energy hero scenes to standard
            hero_scenes = [(i, s['energy']) for i, s in enumerate(scenes)
                          if s['scene_type'] == 'hero']
            hero_scenes.sort(key=lambda x: x[1])  # Sort by energy ascending
            for idx, _ in hero_scenes[:hero_count - max_hero]:
                scenes[idx]['scene_type'] = 'standard'

        return scenes

    def _find_segment_for_time(self, segments: List[Dict], target_time: float) -> Dict:
        """Find the segment containing the target time"""
        for seg in segments:
            if seg.get('start_time', 0) <= target_time <= seg.get('end_time', 0):
                return seg
        # Fallback to closest
        if segments:
            return min(segments, key=lambda s: abs(s.get('start_time', 0) - target_time))
        return {'energy': 0.5, 'mood': 'neutral', 'beat_strength': 0.5}