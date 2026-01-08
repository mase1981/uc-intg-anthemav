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