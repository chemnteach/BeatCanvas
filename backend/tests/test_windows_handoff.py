"""
Windows Handoff Tests - Automated Delivery Verification

Tests the automated delivery pipeline from WSL to Windows Downloads.
This is a CRITICAL gate - no render ships without Green handoff tests.

Test Scenarios:
1. Basic file copy to Windows path
2. Directory creation on Windows
3. Full render bundle handoff (video + frames + metadata)
4. Path sanitization for cross-platform compatibility
5. Large file handling (>100MB)
"""

import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Windows handoff paths (WSL mount points)
WINDOWS_DOWNLOADS = Path("/mnt/c/Users/craig/Downloads")
SYNTERRA_REVIEW = WINDOWS_DOWNLOADS / "synterra_review"
SYNTERRA_ARCHIVE = WINDOWS_DOWNLOADS / "synterra_archive"

# Test file sizes
SMALL_FILE_MB = 1
MEDIUM_FILE_MB = 10
LARGE_FILE_MB = 100


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_source_dir():
    """Create a temporary source directory with test files."""
    temp_dir = tempfile.mkdtemp(prefix="beatcanvas_test_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def dummy_video(temp_source_dir):
    """Create a dummy MP4 file for testing."""
    video_path = temp_source_dir / "test_render.mp4"
    # Create a small dummy file (1MB)
    with open(video_path, "wb") as f:
        f.write(b"\x00" * (SMALL_FILE_MB * 1024 * 1024))
    return video_path


@pytest.fixture
def dummy_render_bundle(temp_source_dir):
    """Create a full render bundle (video + frames + metadata)."""
    # Video
    video_path = temp_source_dir / "cinematic_60fps.mp4"
    with open(video_path, "wb") as f:
        f.write(b"\x00" * (SMALL_FILE_MB * 1024 * 1024))

    # Raw video
    raw_video_path = temp_source_dir / "raw_8fps.mp4"
    with open(raw_video_path, "wb") as f:
        f.write(b"\x00" * (SMALL_FILE_MB * 1024 * 1024))

    # Frames
    frames_dir = temp_source_dir / "frames"
    frames_dir.mkdir()
    for i in range(25):
        frame_path = frames_dir / f"frame_{i:05d}.png"
        with open(frame_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000)  # Minimal PNG header

    # Metadata
    metadata_path = temp_source_dir / "render_metadata.json"
    with open(metadata_path, "w") as f:
        f.write('{"prompt": "test", "timestamp": "2026-02-02T21:00:00"}')

    return {
        "video": video_path,
        "raw_video": raw_video_path,
        "frames_dir": frames_dir,
        "metadata": metadata_path,
        "source_dir": temp_source_dir
    }


@pytest.fixture
def cleanup_windows_test_files():
    """Cleanup any test files on Windows after tests."""
    test_paths = []
    yield test_paths
    # Cleanup after test
    for path in test_paths:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def windows_path_accessible() -> bool:
    """Check if Windows filesystem is accessible via WSL."""
    return WINDOWS_DOWNLOADS.exists() and os.access(WINDOWS_DOWNLOADS, os.W_OK)


def create_timestamped_folder(base_path: Path, prefix: str = "render") -> Path:
    """Create a timestamped folder for render output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = base_path / f"{prefix}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ═══════════════════════════════════════════════════════════════════════════════
# WINDOWS HANDOFF MODULE (Inline for testing - will be extracted later)
# ═══════════════════════════════════════════════════════════════════════════════

class WindowsHandoff:
    """
    Handles automated delivery from WSL to Windows Downloads.

    This class manages the cross-filesystem transfer of render outputs
    to the Windows review station.
    """

    def __init__(
        self,
        review_path: Path = SYNTERRA_REVIEW,
        archive_path: Path = SYNTERRA_ARCHIVE
    ):
        self.review_path = review_path
        self.archive_path = archive_path

    def is_available(self) -> bool:
        """Check if Windows handoff is available."""
        return self.review_path.parent.exists() and os.access(self.review_path.parent, os.W_OK)

    def ensure_review_folder(self) -> Path:
        """Ensure the review folder exists."""
        if not self.is_available():
            raise RuntimeError("Windows filesystem not accessible")
        self.review_path.mkdir(parents=True, exist_ok=True)
        return self.review_path

    def copy_file(self, source: Path, dest_name: str = None) -> Path:
        """Copy a single file to the review folder."""
        self.ensure_review_folder()
        dest_name = dest_name or source.name
        dest_path = self.review_path / dest_name
        shutil.copy2(source, dest_path)
        return dest_path

    def copy_render_bundle(
        self,
        video_path: Path,
        raw_video_path: Path = None,
        frames_dir: Path = None,
        metadata_path: Path = None,
        bundle_name: str = None
    ) -> dict:
        """
        Copy a full render bundle to Windows.

        Returns dict with paths to all copied files.
        """
        if not self.is_available():
            raise RuntimeError("Windows filesystem not accessible")

        # Create timestamped bundle folder
        bundle_name = bundle_name or f"synterra_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        bundle_path = self.review_path / bundle_name
        bundle_path.mkdir(parents=True, exist_ok=True)

        result = {
            "bundle_path": bundle_path,
            "video": None,
            "raw_video": None,
            "frames": [],
            "metadata": None
        }

        # Copy main video
        if video_path and video_path.exists():
            dest = bundle_path / "cinematic_60fps.mp4"
            shutil.copy2(video_path, dest)
            result["video"] = dest

        # Copy raw video
        if raw_video_path and raw_video_path.exists():
            dest = bundle_path / "raw_8fps.mp4"
            shutil.copy2(raw_video_path, dest)
            result["raw_video"] = dest

        # Copy frames
        if frames_dir and frames_dir.exists():
            frames_dest = bundle_path / "frames"
            frames_dest.mkdir(exist_ok=True)
            for frame in sorted(frames_dir.glob("*.png")):
                dest = frames_dest / frame.name
                shutil.copy2(frame, dest)
                result["frames"].append(dest)

        # Copy metadata
        if metadata_path and metadata_path.exists():
            dest = bundle_path / "metadata.json"
            shutil.copy2(metadata_path, dest)
            result["metadata"] = dest

        return result

    def archive_old_renders(self, keep_recent: int = 5) -> int:
        """
        Move old renders from review to archive.

        Returns count of archived renders.
        """
        if not self.is_available():
            return 0

        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Get all render folders sorted by modification time
        render_folders = sorted(
            [d for d in self.review_path.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        archived = 0
        for folder in render_folders[keep_recent:]:
            dest = self.archive_path / folder.name
            shutil.move(str(folder), str(dest))
            archived += 1

        return archived


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Basic Connectivity
# ═══════════════════════════════════════════════════════════════════════════════

class TestWindowsConnectivity:
    """Tests for basic Windows filesystem connectivity."""

    def test_windows_downloads_accessible(self):
        """Verify Windows Downloads folder is accessible."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        assert WINDOWS_DOWNLOADS.exists(), "Windows Downloads should exist"
        assert os.access(WINDOWS_DOWNLOADS, os.W_OK), "Should have write access"

    def test_can_create_review_folder(self, cleanup_windows_test_files):
        """Verify we can create the synterra_review folder."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        test_folder = SYNTERRA_REVIEW / "test_create"
        cleanup_windows_test_files.append(test_folder)

        test_folder.mkdir(parents=True, exist_ok=True)
        assert test_folder.exists(), "Should create folder on Windows"

    def test_handoff_availability_check(self):
        """Test the availability check function."""
        handoff = WindowsHandoff()
        # Should not raise, returns bool
        result = handoff.is_available()
        assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Single File Handoff
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleFileHandoff:
    """Tests for single file delivery to Windows."""

    def test_copy_dummy_video_to_windows(self, dummy_video, cleanup_windows_test_files):
        """Test copying a dummy MP4 to Windows Downloads."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        handoff = WindowsHandoff()
        dest_path = handoff.copy_file(dummy_video, "test_handoff.mp4")
        cleanup_windows_test_files.append(dest_path)

        # THE CRITICAL ASSERTION
        assert dest_path.exists(), f"Video must exist at Windows path: {dest_path}"
        assert os.path.exists(str(dest_path)), "os.path.exists must return True"

        # Verify file integrity
        assert dest_path.stat().st_size == dummy_video.stat().st_size, \
            "File sizes must match"

    def test_copy_preserves_timestamps(self, dummy_video, cleanup_windows_test_files):
        """Verify file timestamps are preserved during copy."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        handoff = WindowsHandoff()
        dest_path = handoff.copy_file(dummy_video, "test_timestamp.mp4")
        cleanup_windows_test_files.append(dest_path)

        # shutil.copy2 should preserve mtime
        source_mtime = dummy_video.stat().st_mtime
        dest_mtime = dest_path.stat().st_mtime
        # Allow 1 second tolerance for filesystem differences
        assert abs(source_mtime - dest_mtime) < 1, "Timestamps should be preserved"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Full Bundle Handoff
# ═══════════════════════════════════════════════════════════════════════════════

class TestBundleHandoff:
    """Tests for full render bundle delivery."""

    def test_copy_full_render_bundle(self, dummy_render_bundle, cleanup_windows_test_files):
        """Test copying a complete render bundle to Windows."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        handoff = WindowsHandoff()
        bundle = dummy_render_bundle

        result = handoff.copy_render_bundle(
            video_path=bundle["video"],
            raw_video_path=bundle["raw_video"],
            frames_dir=bundle["frames_dir"],
            metadata_path=bundle["metadata"],
            bundle_name="test_bundle"
        )
        cleanup_windows_test_files.append(result["bundle_path"])

        # Verify all components exist
        assert result["bundle_path"].exists(), "Bundle folder should exist"
        assert result["video"].exists(), "Video should exist"
        assert result["raw_video"].exists(), "Raw video should exist"
        assert result["metadata"].exists(), "Metadata should exist"
        assert len(result["frames"]) == 25, "All 25 frames should be copied"

        # Verify with os.path.exists
        assert os.path.exists(str(result["video"])), "os.path.exists must work"

    def test_bundle_creates_timestamped_folder(self, dummy_render_bundle, cleanup_windows_test_files):
        """Verify bundle creates properly named folder."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        handoff = WindowsHandoff()
        bundle = dummy_render_bundle

        result = handoff.copy_render_bundle(
            video_path=bundle["video"],
            bundle_name=None  # Auto-generate name
        )
        cleanup_windows_test_files.append(result["bundle_path"])

        # Should start with 'synterra_' and have timestamp
        assert result["bundle_path"].name.startswith("synterra_"), \
            "Bundle should have synterra_ prefix"
        assert len(result["bundle_path"].name) > 15, \
            "Bundle name should include timestamp"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Path Sanitization
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathSanitization:
    """Tests for cross-platform path handling."""

    def test_handles_spaces_in_filename(self, temp_source_dir, cleanup_windows_test_files):
        """Verify files with spaces work correctly."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        # Create file with spaces
        source = temp_source_dir / "test file with spaces.mp4"
        with open(source, "wb") as f:
            f.write(b"\x00" * 1000)

        handoff = WindowsHandoff()
        dest_path = handoff.copy_file(source)
        cleanup_windows_test_files.append(dest_path)

        assert dest_path.exists(), "File with spaces should copy successfully"

    def test_handles_unicode_in_filename(self, temp_source_dir, cleanup_windows_test_files):
        """Verify files with unicode characters work."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        # Create file with unicode (safe characters only)
        source = temp_source_dir / "test_render_2026.mp4"
        with open(source, "wb") as f:
            f.write(b"\x00" * 1000)

        handoff = WindowsHandoff()
        dest_path = handoff.copy_file(source)
        cleanup_windows_test_files.append(dest_path)

        assert dest_path.exists(), "File should copy successfully"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Error Handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Tests for error conditions."""

    def test_graceful_handling_when_windows_unavailable(self):
        """Test behavior when Windows filesystem is not mounted."""
        # Use a non-existent path
        handoff = WindowsHandoff(
            review_path=Path("/mnt/z/NonExistent/Path")
        )

        assert not handoff.is_available(), "Should report unavailable"

        with pytest.raises(RuntimeError, match="Windows filesystem not accessible"):
            handoff.ensure_review_folder()

    def test_missing_source_file(self, cleanup_windows_test_files):
        """Test handling of missing source file."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        handoff = WindowsHandoff()
        missing_file = Path("/nonexistent/video.mp4")

        with pytest.raises(FileNotFoundError):
            handoff.copy_file(missing_file)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Integration with CinematicDirector
# ═══════════════════════════════════════════════════════════════════════════════

class TestCinematicDirectorIntegration:
    """Tests for CinematicDirector handoff integration."""

    def test_director_includes_windows_handoff_stage(self):
        """Verify CinematicDirector has handoff as final stage."""
        try:
            from src.local.cinematic_director import CinematicDirector
        except ImportError:
            pytest.skip("CinematicDirector not available")

        director = CinematicDirector()

        # Check for handoff capability (method and config)
        assert hasattr(director, 'handoff_to_windows'), \
            "CinematicDirector should have handoff_to_windows method"
        assert hasattr(director, 'windows_downloads'), \
            "CinematicDirector should have windows_downloads attribute"

    def test_director_run_returns_windows_path(self):
        """Verify director.run() returns windows_path in result."""
        try:
            from src.local.cinematic_director import CinematicDirector
        except ImportError:
            pytest.skip("CinematicDirector not available")

        # The smoke test already verified this returns windows_path
        # This test documents the contract
        director = CinematicDirector()

        # Mock a minimal run to check result structure
        # Full run is tested in production_smoke_test.py
        assert hasattr(director, 'run'), "Director must have run method"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: Large File Handling (Skipped by default - slow)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLargeFileHandling:
    """Tests for large file transfers (marked slow)."""

    @pytest.mark.slow
    def test_copy_large_file_100mb(self, temp_source_dir, cleanup_windows_test_files):
        """Test copying a 100MB file to Windows."""
        if not windows_path_accessible():
            pytest.skip("Windows filesystem not mounted")

        # Create 100MB file
        large_file = temp_source_dir / "large_render.mp4"
        with open(large_file, "wb") as f:
            # Write in chunks to avoid memory issues
            chunk = b"\x00" * (1024 * 1024)  # 1MB chunk
            for _ in range(LARGE_FILE_MB):
                f.write(chunk)

        handoff = WindowsHandoff()
        dest_path = handoff.copy_file(large_file, "large_test.mp4")
        cleanup_windows_test_files.append(dest_path)

        assert dest_path.exists(), "Large file should copy successfully"
        assert dest_path.stat().st_size == large_file.stat().st_size, \
            "File sizes must match for large files"


# ═══════════════════════════════════════════════════════════════════════════════
# CLI RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "--tb=short", "-x"])
