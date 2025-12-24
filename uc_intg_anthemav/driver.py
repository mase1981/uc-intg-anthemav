"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

<<<<<<< HEAD
from ucapi import EntityTypes, media_player
from ucapi_framework import BaseIntegrationDriver
=======
from ucapi import EntityTypes
from ucapi.media_player import Attributes, States
from ucapi_framework import (
    BaseConfigManager,
    BaseIntegrationDriver,
    create_entity_id,
    get_config_path,
)
>>>>>>> main

from uc_intg_anthemav.config import AnthemConfigManager, AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice
from uc_intg_anthemav.media_player import AnthemMediaPlayer
<<<<<<< HEAD
from uc_intg_anthemav.remote import AnthemRemote
=======
from uc_intg_anthemav.setup_flow import AnthemSetupFlow
>>>>>>> main

_LOG = logging.getLogger(__name__)


<<<<<<< HEAD
class AnthemDriver(BaseIntegrationDriver[AnthemDevice, AnthemDeviceConfig]):
    """Anthem A/V integration driver."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__(
            device_class=AnthemDevice,
            entity_classes=[],
            loop=loop,
            driver_id="anthemav"
        )
    
    def create_entities(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice
    ) -> list[AnthemMediaPlayer | AnthemRemote]:
        """Create both media player and remote entities for each zone."""
        entities = []
        
        for zone_config in device_config.zones:
            if not zone_config.enabled:
                continue
            
            # Create Media Player entity
            media_player_entity = AnthemMediaPlayer(device_config, device, zone_config)
            entities.append(media_player_entity)
            _LOG.info("Created media player: %s for %s Zone %d",
                     media_player_entity.id, device_config.name, zone_config.zone_number)
            
            # Create Remote entity
            remote_entity = AnthemRemote(device_config, device, zone_config)
            entities.append(remote_entity)
            _LOG.info("Created remote: %s for %s Zone %d audio controls",
                     remote_entity.id, device_config.name, zone_config.zone_number)
        
        return entities
    
    async def refresh_entity_state(self, entity_id: str) -> None:
        """
        Refresh entity state by querying device and updating SOURCE_LIST.
        
        CRITICAL FIX: This method does THREE things:
        1. Sets STATE based on connection (via super())
        2. Copies SOURCE_LIST from device to configured entity (THE FIX!)
        3. Queries device for current volume/mute/source
        """
        _LOG.info("[%s] Refreshing entity state", entity_id)
        
        # Step 1: Call parent to set STATE
        await super().refresh_entity_state(entity_id)
        
        # Get device
        device_id = self.device_from_entity_id(entity_id)
        if not device_id:
            _LOG.warning("[%s] Could not extract device_id", entity_id)
            return
        
        device = self._configured_devices.get(device_id)
        if not device:
            _LOG.warning("[%s] Device %s not found", entity_id, device_id)
            return
        
        if not device.is_connected:
            _LOG.debug("[%s] Device not connected, skipping query", entity_id)
            return
        
        configured_entity = self.api.configured_entities.get(entity_id)
        if not configured_entity:
            _LOG.debug("[%s] Entity not configured, skipping query", entity_id)
            return
        
        # Only process media_player entities
        if configured_entity.entity_type != EntityTypes.MEDIA_PLAYER:
            _LOG.debug("[%s] Not a media player, no query needed", entity_id)
            return
        
        # Step 2: CRITICAL FIX - Copy SOURCE_LIST from device to configured entity
        # Without this, activity configuration has no source dropdown!
        source_list = device.get_input_list()
        if source_list:
            self.api.configured_entities.update_attributes(
                entity_id, 
                {media_player.Attributes.SOURCE_LIST: source_list}
            )
            _LOG.info("[%s] Updated SOURCE_LIST with %d sources", entity_id, len(source_list))
        else:
            _LOG.warning("[%s] No source list available from device", entity_id)
        
        # Step 3: Extract zone number and query device
        parts = entity_id.split(".")
        if len(parts) == 2:
            zone_num = 1  # Main zone
        elif len(parts) == 3 and parts[2].startswith("zone"):
            try:
                zone_num = int(parts[2].replace("zone", ""))
            except ValueError:
                _LOG.error("[%s] Invalid zone format: %s", entity_id, parts[2])
                return
        else:
            zone_num = 1
        
        # Query device - this triggers responses that emit UPDATE events
        _LOG.info("[%s] Querying device status for Zone %d", entity_id, zone_num)
        await device.query_status(zone_num)
    
    def device_from_entity_id(self, entity_id: str) -> str | None:
        """Extract device ID from entity ID."""
        if not entity_id or "." not in entity_id:
            return None
        
        parts = entity_id.split(".")
        
        # Format: type.device_id or type.device_id.sub
        if len(parts) >= 2:
            return parts[1]
        
        return None
    
    def get_entity_ids_for_device(self, device_id: str) -> list[str]:
        """Get all entity IDs for a device."""
        device_config = self.get_device_config(device_id)
        if not device_config:
            return []
        
        entity_ids = []
        for zone in device_config.zones:
            if not zone.enabled:
                continue
            
            if zone.zone_number == 1:
                entity_ids.append(f"media_player.{device_id}")
                entity_ids.append(f"remote.{device_id}")
            else:
                entity_ids.append(f"media_player.{device_id}.zone{zone.zone_number}")
                entity_ids.append(f"remote.{device_id}.zone{zone.zone_number}")
        
        return entity_ids
=======
class AnthemDriver(BaseIntegrationDriver):
    _device_config: AnthemDeviceConfig
    _device: AnthemDevice
    """Anthem A/V integration driver."""

    # I'm thinking about ways to avoid having to override this method. You need to create an array of entities per device
    # and I do as well in some of my integrations. It would be possible to specify a piece of config that is the list of
    # sub-devices and then have the framework create one entity per sub-device automatically. But in my situation, I need
    # to create from multiple lists. (Lights, and Covers for example). So a single list wouldn't even work. And it would
    # likely be more complex to call than just overriding this method.
    def create_entities(
        self, device_config: AnthemDeviceConfig, device: AnthemDevice
    ) -> list:
        """Create media player entities for each zone."""
        entities = []

        for zone_config in device_config.zones:
            if not zone_config.enabled:
                continue

            entity_id = create_entity_id(
                EntityTypes.MEDIA_PLAYER,
                device_config.identifier,
                f"zone{zone_config.zone_number}",
            )

            entity = AnthemMediaPlayer(
                entity_id=entity_id,
                device=device,
                device_config=device_config,
                zone_config=zone_config,
            )

            entities.append(entity)
            _LOG.info(
                f"Created entity: {entity_id} for {device_config.name} Zone {zone_config.zone_number}"
            )

        return entities

    # I'm going to update the framework to not require you to call this
    def sub_device_from_entity_id(self, entity_id: str) -> str | None:
        """Extract zone identifier from entity ID."""
        parts = entity_id.split(".")
        if len(parts) == 3:
            return parts[2]
        return None

    def on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device state updates."""
        if entity_id != self._device_config.identifier:
            return

        configured_entity = self.api.configured_entities.get(entity_id)
        zone_number = self.sub_device_from_entity_id(entity_id)

        if "zone" in update_data:
            if update_data["zone"] == zone_number:
                zone_state = update_data.get("state", {})
                self._update_attributes_from_state(zone_state, configured_entity)

        if update_data.get("inputs_discovered"):
            source_list = self._device.get_input_list()
            if configured_entity.attributes.get(Attributes.SOURCE_LIST) != source_list:
                configured_entity.attributes[Attributes.SOURCE_LIST] = source_list

    def _update_attributes_from_state(
        self, zone_state: dict[str, Any], configured_entity: AnthemMediaPlayer
    ) -> None:
        """Update entity attributes from zone state."""
        updated_attrs = {}

        if "power" in zone_state:
            new_state = States.ON if zone_state["power"] else States.OFF
            if configured_entity.attributes.get(Attributes.STATE) != new_state:
                updated_attrs[Attributes.STATE] = new_state

        if "volume" in zone_state:
            volume_db = zone_state["volume"]
            volume_pct = configured_entity._db_to_percentage(volume_db)
            if (
                abs(configured_entity.attributes.get(Attributes.VOLUME, 0) - volume_pct)
                > 0.01
            ):
                updated_attrs[Attributes.VOLUME] = volume_pct

        if "muted" in zone_state:
            if (
                configured_entity.attributes.get(Attributes.MUTED)
                != zone_state["muted"]
            ):
                updated_attrs[Attributes.MUTED] = zone_state["muted"]

        if "input_name" in zone_state:
            if (
                configured_entity.attributes.get(Attributes.SOURCE)
                != zone_state["input_name"]
            ):
                updated_attrs[Attributes.SOURCE] = zone_state["input_name"]
                if zone_state["input_name"]:
                    updated_attrs[Attributes.MEDIA_TITLE] = zone_state["input_name"]

        if "audio_format" in zone_state:
            if zone_state["audio_format"]:
                updated_attrs[Attributes.MEDIA_TYPE] = zone_state["audio_format"]

        if updated_attrs:
            configured_entity.attributes.update(updated_attrs)


# I deleted __init__ and main and moved the logic here and updated build.yml to point to this file as the driver entry point.
# This conforms to the way the official integrations are structured.
async def main():
    """Main entry point for Anthem integration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    driver = AnthemDriver(device_class=AnthemDevice, entity_classes=[AnthemMediaPlayer])

    config_manager = BaseConfigManager[AnthemDeviceConfig](
        get_config_path(driver.api.config_dir_path),
        driver.on_device_added,
        driver.on_device_removed,
        config_class=AnthemDeviceConfig,
    )

    setup_flow = AnthemSetupFlow(config_manager)

    await driver.api.init("driver.json", setup_flow)

    # Keep the driver running
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> main
