"""
Anthem A/V Receiver configuration with discovered capabilities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass, field
from ucapi_framework import BaseConfigManager


@dataclass
class ZoneConfig:
<<<<<<< HEAD
    """Configuration for a single receiver zone."""
    
=======
    """Configuration for a single zone."""

>>>>>>> main
    zone_number: int
    enabled: bool = True
    name: str | None = None

    def __post_init__(self):
        """Set default name if not provided."""
        if self.name is None:
            self.name = f"Zone {self.zone_number}"


@dataclass
class AnthemDeviceConfig:
<<<<<<< HEAD
=======
    """Configuration for an Anthem A/V receiver/processor."""

>>>>>>> main
    identifier: str
    name: str
    host: str
    model: str = "AVM"
    port: int = 14999
    zones: list[ZoneConfig] = field(default_factory=lambda: [ZoneConfig(1)])
<<<<<<< HEAD
    
    # CRITICAL: Store discovered inputs from setup flow
    # This is populated during query_device() BEFORE entities are created
    discovered_inputs: list[str] = field(default_factory=list)
    discovered_model: str = "Unknown"


class AnthemConfigManager(BaseConfigManager[AnthemDeviceConfig]):
    """Configuration manager for Anthem devices with JSON persistence."""
    pass
=======

    def __post_init__(self):
        """Ensure zones is a list of ZoneConfig objects."""
        if self.zones and isinstance(self.zones[0], dict):
            self.zones = [
                ZoneConfig(**z) if isinstance(z, dict) else z for z in self.zones
            ]
>>>>>>> main
