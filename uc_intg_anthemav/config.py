"""
Anthem A/V Receiver configuration with discovered capabilities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass, field


@dataclass
class ZoneConfig:
    """Configuration for a single receiver zone."""

    zone_number: int
    enabled: bool = True
    name: str | None = None

    def __post_init__(self):
        """Set default name if not provided."""
        if self.name is None:
            self.name = f"Zone {self.zone_number}"


@dataclass
class AnthemDeviceConfig:
    identifier: str
    name: str
    host: str
    model: str = "AVM"
    port: int = 14999
    zones: list[ZoneConfig] = field(default_factory=lambda: [ZoneConfig(1)])

    discovered_inputs: list[str] = field(default_factory=list)
    discovered_model: str = "Unknown"

    @property
    def is_x20_series(self) -> bool:
        # TODO: Fragile substring matching — should match exact IDM? model strings.
        # Known x20 models: MRX 520, MRX 720, MRX 1120, AVM 60
        model_upper = self.discovered_model.upper()
        if "AVM 60" in model_upper or "AVM60" in model_upper:
            return True
        if "MRX" in model_upper:
            for suffix in ["520", "720", "1120"]:
                if suffix in model_upper:
                    return True
        return False

    @property
    def is_x40_series(self) -> bool:
        # TODO: Fragile substring matching — should match exact IDM? model strings.
        # Known x40 models: MRX 540, MRX 740, MRX 1140, AVM 70, AVM 90
        model_upper = self.discovered_model.upper()
        if any(s in model_upper for s in ["AVM 70", "AVM70", "AVM 90", "AVM90"]):
            return True
        if "MRX" in model_upper:
            for suffix in ["540", "740", "1140"]:
                if suffix in model_upper:
                    return True
        return False

    @property
    def series(self) -> str:
        """Return the detected series identifier, or 'unknown'."""
        if self.is_x20_series:
            return "x20"
        if self.is_x40_series:
            return "x40"
        return "unknown"
