"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi import Entity, EntityTypes, media_player
from ucapi_framework import BaseIntegrationDriver

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice
from uc_intg_anthemav.media_player import AnthemMediaPlayer
from uc_intg_anthemav.remote import AnthemRemote

_LOG = logging.getLogger(__name__)


class AnthemDriver(BaseIntegrationDriver[AnthemDevice, AnthemDeviceConfig]):
    """Anthem A/V integration driver."""

    def __init__(self):
        super().__init__(
            device_class=AnthemDevice,
            entity_classes=[],
        )

    def create_entities(
        self, device_config: AnthemDeviceConfig, device: AnthemDevice
    ) -> list[Entity]:
        """Create both media player and remote entities for each zone."""
        entities = []

        for zone_config in device_config.zones:
            if not zone_config.enabled:
                continue

            media_player_entity = AnthemMediaPlayer(device_config, device, zone_config)
            entities.append(media_player_entity)
            _LOG.info(
                "Created media player: %s for %s Zone %d",
                media_player_entity.id,
                device_config.name,
                zone_config.zone_number,
            )

            remote_entity = AnthemRemote(device_config, device, zone_config)
            entities.append(remote_entity)
            _LOG.info(
                "Created remote: %s for %s Zone %d audio controls",
                remote_entity.id,
                device_config.name,
                zone_config.zone_number,
            )

        return entities

    async def refresh_entity_state(self, entity_id: str) -> None:
        """
        Refresh entity state by querying device and updating SOURCE_LIST.
        """
        _LOG.info("[%s] Refreshing entity state", entity_id)

        device_id = self.device_from_entity_id(entity_id)
        if not device_id:
            _LOG.warning("[%s] Could not extract device_id", entity_id)
            return

        device = self._configured_devices.get(device_id)
        if not device:
            _LOG.warning("[%s] Device %s not found", entity_id, device_id)
            return

        configured_entity = self.api.configured_entities.get(entity_id)
        if not configured_entity:
            _LOG.debug("[%s] Entity not configured yet", entity_id)
            return

        if not device.is_connected:
            _LOG.debug("[%s] Device not connected, marking unavailable", entity_id)
            await super().refresh_entity_state(entity_id)
            return

        if configured_entity.entity_type == EntityTypes.MEDIA_PLAYER:
            source_list = device.get_input_list()
            if source_list:
                self.api.configured_entities.update_attributes(
                    entity_id, {media_player.Attributes.SOURCE_LIST: source_list}
                )
                _LOG.info(
                    "[%s] Updated SOURCE_LIST with %d sources", entity_id, len(source_list)
                )

        parts = entity_id.split(".")
        if len(parts) == 2:
            zone_num = 1
        elif len(parts) == 3 and parts[2].startswith("zone"):
            try:
                zone_num = int(parts[2].replace("zone", ""))
            except ValueError:
                _LOG.error("[%s] Invalid zone format: %s", entity_id, parts[2])
                return
        else:
            zone_num = 1

        _LOG.info("[%s] Querying device status for Zone %d", entity_id, zone_num)
        await device.query_status(zone_num)

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
