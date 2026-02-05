"""
Optics Catalog - Load and validate cinematography presets from YAML.

Provides OpticsCatalog class for accessing cameras, film stocks, lighting,
motion presets, and aDetailer configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, List
import yaml


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PresetEntry:
    """Single preset entry (camera, film stock, etc.)."""

    name: str
    prompt_tokens: str
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "PresetEntry":
        """Create from YAML dict."""
        return cls(
            name=name,
            prompt_tokens=data.get("prompt_tokens", ""),
            description=data.get("description", ""),
        )


@dataclass
class ADetailerConfig:
    """aDetailer post-processing configuration."""

    enabled: bool = True
    model: str = ""
    confidence: float = 0.3
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ADetailerConfig":
        """Create from YAML dict."""
        return cls(
            enabled=data.get("enabled", True),
            model=data.get("model", ""),
            confidence=data.get("confidence", 0.3),
            description=data.get("description", ""),
        )


@dataclass
class QualityToken:
    """Quality token configuration."""

    prompt_tokens: str
    mandatory: bool = False
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityToken":
        """Create from YAML dict."""
        return cls(
            prompt_tokens=data.get("prompt_tokens", ""),
            mandatory=data.get("mandatory", False),
            description=data.get("description", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# OPTICS CATALOG
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class OpticsCatalog:
    """
    Catalog of cinematography optics presets.

    Loads from YAML file and provides typed access to:
    - Cameras
    - Film stocks
    - Lighting setups
    - Motion styles
    - Quality tokens
    - aDetailer configs
    - Negative prompts
    """

    cameras: Dict[str, PresetEntry] = field(default_factory=dict)
    film_stocks: Dict[str, PresetEntry] = field(default_factory=dict)
    lighting: Dict[str, PresetEntry] = field(default_factory=dict)
    motion: Dict[str, PresetEntry] = field(default_factory=dict)
    quality_tokens: Dict[str, QualityToken] = field(default_factory=dict)
    adetailer: Dict[str, ADetailerConfig] = field(default_factory=dict)
    negative_prompts: Dict[str, str] = field(default_factory=dict)
    version: str = "1.0"

    @classmethod
    def empty(cls) -> "OpticsCatalog":
        """
        Create empty catalog for unit testing.

        Returns catalog with no presets loaded - useful for tests
        that don't need actual YAML data.
        """
        return cls()

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "OpticsCatalog":
        """
        Load catalog from YAML file.

        Args:
            yaml_path: Path to optics_presets.yaml

        Returns:
            Populated OpticsCatalog

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Optics presets not found: {yaml_path}")

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpticsCatalog":
        """
        Create catalog from dict (for testing with inline data).

        Args:
            data: Dict matching YAML structure

        Returns:
            Populated OpticsCatalog
        """
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "OpticsCatalog":
        """Internal: Parse dict into catalog."""
        catalog = cls()
        catalog.version = data.get("version", "1.0")

        # Parse cameras
        for name, entry in data.get("cameras", {}).items():
            catalog.cameras[name] = PresetEntry.from_dict(name, entry)

        # Parse film stocks
        for name, entry in data.get("film_stocks", {}).items():
            catalog.film_stocks[name] = PresetEntry.from_dict(name, entry)

        # Parse lighting
        for name, entry in data.get("lighting", {}).items():
            catalog.lighting[name] = PresetEntry.from_dict(name, entry)

        # Parse motion
        for name, entry in data.get("motion", {}).items():
            catalog.motion[name] = PresetEntry.from_dict(name, entry)

        # Parse quality tokens
        for name, entry in data.get("quality_tokens", {}).items():
            catalog.quality_tokens[name] = QualityToken.from_dict(entry)

        # Parse aDetailer
        for name, entry in data.get("adetailer", {}).items():
            catalog.adetailer[name] = ADetailerConfig.from_dict(entry)

        # Parse negative prompts
        for name, entry in data.get("negative_prompts", {}).items():
            catalog.negative_prompts[name] = entry.get("prompt_tokens", "")

        return catalog

    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS - Return prompt tokens or empty string
    # ═══════════════════════════════════════════════════════════════════════════

    def get_camera_tokens(self, name: str) -> str:
        """Get camera prompt tokens by name, empty string if not found."""
        entry = self.cameras.get(name)
        return entry.prompt_tokens if entry else ""

    def get_film_tokens(self, name: str) -> str:
        """Get film stock prompt tokens by name, empty string if not found."""
        entry = self.film_stocks.get(name)
        return entry.prompt_tokens if entry else ""

    def get_lighting_tokens(self, name: str) -> str:
        """Get lighting prompt tokens by name, empty string if not found."""
        entry = self.lighting.get(name)
        return entry.prompt_tokens if entry else ""

    def get_motion_tokens(self, name: str) -> str:
        """Get motion prompt tokens by name, empty string if not found."""
        entry = self.motion.get(name)
        return entry.prompt_tokens if entry else ""

    def get_mandatory_quality_tokens(self) -> str:
        """Get all mandatory quality tokens combined."""
        mandatory = [
            qt.prompt_tokens
            for qt in self.quality_tokens.values()
            if qt.mandatory and qt.prompt_tokens
        ]
        return ", ".join(mandatory) if mandatory else ""

    def get_negative_prompt(self, category: str) -> str:
        """Get negative prompt by category (photorealism, anatomy, quality)."""
        return self.negative_prompts.get(category, "")

    def get_all_negative_prompts(self) -> str:
        """Get all negative prompts combined."""
        return ", ".join(
            prompt for prompt in self.negative_prompts.values() if prompt
        )

    def get_adetailer_config(self, name: str) -> Optional[ADetailerConfig]:
        """Get aDetailer config by name."""
        return self.adetailer.get(name)

    # ═══════════════════════════════════════════════════════════════════════════
    # LISTING - Available presets
    # ═══════════════════════════════════════════════════════════════════════════

    def list_cameras(self) -> List[str]:
        """List all camera names."""
        return list(self.cameras.keys())

    def list_film_stocks(self) -> List[str]:
        """List all film stock names."""
        return list(self.film_stocks.keys())

    def list_lighting(self) -> List[str]:
        """List all lighting names."""
        return list(self.lighting.keys())

    def list_motion(self) -> List[str]:
        """List all motion names."""
        return list(self.motion.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT CATALOG LOADER
# ═══════════════════════════════════════════════════════════════════════════════

# Default path relative to this module
_DEFAULT_PRESETS_PATH = (
    Path(__file__).parent.parent.parent / "library" / "optics_presets.yaml"
)


def load_default_catalog() -> OpticsCatalog:
    """
    Load the default optics catalog from library/optics_presets.yaml.

    Returns:
        OpticsCatalog with all presets loaded

    Raises:
        FileNotFoundError: If default YAML doesn't exist
    """
    return OpticsCatalog.from_yaml(_DEFAULT_PRESETS_PATH)
