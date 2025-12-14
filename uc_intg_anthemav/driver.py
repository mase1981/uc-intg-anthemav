"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging

from ucapi import EntityTypes
from ucapi_framework import BaseIntegrationDriver, create_entity_id

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice
from uc_intg_anthemav.media_player import AnthemMediaPlayer

_LOG = logging.getLogger(__name__)


class AnthemDriver(BaseIntegrationDriver):
    """Anthem A/V integration driver."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        """Initialize the Anthem driver."""
        super().__init__(
            loop=loop,
            device_class=AnthemDevice,
            entity_classes=[AnthemMediaPlayer]
        )
    
    def create_entities(
        self, 
        config: AnthemDeviceConfig, 
        device: AnthemDevice
    ) -> list:
        """Create media player entities for each zone."""
        entities = []
        
        for zone_config in config.zones:
            if not zone_config.enabled:
                continue
            
            entity_id = create_entity_id(
                EntityTypes.MEDIA_PLAYER,
                config.identifier,
                f"zone{zone_config.zone_number}"
            )
            
            entity = AnthemMediaPlayer(
                entity_id=entity_id,
                device=device,
                device_config=config,
                zone_config=zone_config
            )
            
            entities.append(entity)
            _LOG.info(f"Created entity: {entity_id} for {config.name} Zone {zone_config.zone_number}")
        
        return entities
    
    def sub_device_from_entity_id(self, entity_id: str) -> str | None:
        """Extract zone identifier from entity ID."""
        parts = entity_id.split(".")
        if len(parts) == 3:
            return parts[2]
        return None