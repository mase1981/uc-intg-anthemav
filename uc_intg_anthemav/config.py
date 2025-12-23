"""
Anthem A/V Receiver configuration with dataclasses.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass, field
from ucapi_framework import BaseConfigManager


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
    """Configuration for an Anthem A/V receiver."""
    
    identifier: str
    name: str
    host: str
    model: str = "MRX"
    port: int = 14999
    zones: list[ZoneConfig] = field(default_factory=lambda: [ZoneConfig(1)])


class AnthemConfigManager(BaseConfigManager[AnthemDeviceConfig]):
    """Configuration manager for Anthem devices with JSON persistence."""
    pass