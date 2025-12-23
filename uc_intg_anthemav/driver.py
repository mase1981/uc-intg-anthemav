"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging

from ucapi import EntityTypes
from ucapi_framework import BaseIntegrationDriver, create_entity_id

from .config import AnthemConfigManager, AnthemDeviceConfig
from .device import AnthemDevice
from .media_player import AnthemMediaPlayer
from .setup_flow import AnthemSetupFlow

_LOG = logging.getLogger(__name__)


class AnthemDriver(BaseIntegrationDriver[AnthemDevice, AnthemDeviceConfig]):
    """Anthem A/V integration driver."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__(
            device_class=AnthemDevice,
            entity_classes=[],  # We'll create entities manually for multi-zone
            loop=loop,
            driver_id="anthemav"
        )
        # Store entity references for subscription handler
        self._entities: dict[str, AnthemMediaPlayer] = {}
    
    def create_entities(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice
    ) -> list[AnthemMediaPlayer]:
        """
        Create media player entities for each zone.
        
        For multi-zone receivers, creates one entity per zone.
        """
        entities = []
        
        for zone_config in device_config.zones:
            if not zone_config.enabled:
                continue
            
            entity = AnthemMediaPlayer(device_config, device, zone_config)
            entities.append(entity)
            
            # Store entity reference for subscription handler
            self._entities[entity.id] = entity
            
            _LOG.info("Created entity: %s for %s Zone %d",
                     entity.id, device_config.name, zone_config.zone_number)
        
        return entities
    
    async def on_subscribe_entities(self, entity_ids: list[str]) -> None:
        """
        Handle entity subscription requests.
        
        Called when Remote subscribes to entities. This triggers initial
        status queries to populate entity state.
        """
        _LOG.info("=== SUBSCRIPTION HANDLER TRIGGERED ===")
        _LOG.info("Subscribed entity IDs: %s", entity_ids)
        
        # Log available entities for debugging
        available_ids = list(self._entities.keys())
        _LOG.info("Available entities: %s", available_ids)
        
        # Trigger initial status query for each subscribed entity
        for entity_id in entity_ids:
            entity = self._entities.get(entity_id)
            if entity:
                _LOG.info("[%s] Triggering initial status query", entity_id)
                await entity.push_update()
            else:
                _LOG.warning("[%s] Entity not found in driver registry", entity_id)
    
    def device_from_entity_id(self, entity_id: str) -> str | None:
        """
        Extract device ID from entity ID.
        
        Entity ID format:
        - Zone 1: media_player.anthem_192_168_1_100_14999
        - Zone 2+: media_player.anthem_192_168_1_100_14999.zone2
        """
        if not entity_id:
            return None
        
        if "." not in entity_id:
            return None
        
        parts = entity_id.split(".")
        
        if len(parts) == 2:
            # Simple format: media_player.device_id
            return parts[1]
        elif len(parts) == 3:
            # With sub-device: media_player.device_id.zone2
            return parts[1]
        
        return None
    
    def get_entity_ids_for_device(self, device_id: str) -> list[str]:
        """
        Get all entity IDs for a device.
        
        Returns entity IDs for all configured zones.
        """
        device_config = self.get_device_config(device_id)
        if not device_config:
            return []
        
        entity_ids = []
        for zone in device_config.zones:
            if not zone.enabled:
                continue
            
            if zone.zone_number == 1:
                entity_ids.append(f"media_player.{device_id}")
            else:
                entity_ids.append(f"media_player.{device_id}.zone{zone.zone_number}")
        
        return entity_ids