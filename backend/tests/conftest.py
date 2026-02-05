"""
Pytest configuration and shared fixtures for BeatCanvas tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Add backend to Python path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set working directory to backend for config resolution
os.chdir(BACKEND_DIR)


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "cuda: marks tests that require CUDA (skip without GPU)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def backend_dir():
    """Return backend directory path."""
    return BACKEND_DIR


@pytest.fixture(scope="session")
def config_dir(backend_dir):
    """Return config directory path."""
    return backend_dir / "config"


@pytest.fixture(scope="session")
def models_dir():
    """Return models directory path."""
    return Path("/home/craig/AI_Workspace/synterra/beatcanvas/backend/models")


@pytest.fixture
def cuda_available():
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
