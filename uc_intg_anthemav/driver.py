"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi import Entity, EntityTypes, media_player, remote, sensor, select
from ucapi_framework import BaseIntegrationDriver

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice
from uc_intg_anthemav.media_player import AnthemMediaPlayer
from uc_intg_anthemav.remote import AnthemRemote
from uc_intg_anthemav.sensor import (
    AnthemVolumeSensor,
    AnthemAudioFormatSensor,
    AnthemAudioChannelsSensor,
    AnthemVideoResolutionSensor,
    AnthemListeningModeSensor,
    AnthemSampleRateSensor,
    AnthemModelSensor,
)
from uc_intg_anthemav.select import AnthemListeningModeSelect

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
        """Create media player, remote, and sensor entities for each zone."""
        entities = []

        for zone_config in device_config.zones:
            if not zone_config.enabled:
                continue

            # Create media player entity
            media_player_entity = AnthemMediaPlayer(device_config, device, zone_config)
            entities.append(media_player_entity)
            _LOG.info(
                "Created media player: %s for %s Zone %d",
                media_player_entity.id,
                device_config.name,
                zone_config.zone_number,
            )

            # Create remote entity
            remote_entity = AnthemRemote(device_config, device, zone_config)
            entities.append(remote_entity)
            _LOG.info(
                "Created remote: %s for %s Zone %d audio controls",
                remote_entity.id,
                device_config.name,
                zone_config.zone_number,
            )

            # Create sensor entities (only for Zone 1 to avoid clutter)
            if zone_config.zone_number == 1:
                # Volume sensor (shows actual dB value)
                volume_sensor = AnthemVolumeSensor(device_config, device, zone_config)
                entities.append(volume_sensor)
                _LOG.info("Created sensor: %s for volume monitoring", volume_sensor.id)

                # Audio format sensor
                audio_format_sensor = AnthemAudioFormatSensor(device_config, device, zone_config)
                entities.append(audio_format_sensor)
                _LOG.info("Created sensor: %s for audio format", audio_format_sensor.id)

                # Audio channels sensor
                audio_channels_sensor = AnthemAudioChannelsSensor(device_config, device, zone_config)
                entities.append(audio_channels_sensor)
                _LOG.info("Created sensor: %s for audio channels", audio_channels_sensor.id)

                # Video resolution sensor
                video_resolution_sensor = AnthemVideoResolutionSensor(device_config, device, zone_config)
                entities.append(video_resolution_sensor)
                _LOG.info("Created sensor: %s for video resolution", video_resolution_sensor.id)

                # Listening mode sensor
                listening_mode_sensor = AnthemListeningModeSensor(device_config, device, zone_config)
                entities.append(listening_mode_sensor)
                _LOG.info("Created sensor: %s for listening mode", listening_mode_sensor.id)

                # Sample rate sensor
                sample_rate_sensor = AnthemSampleRateSensor(device_config, device, zone_config)
                entities.append(sample_rate_sensor)
                _LOG.info("Created sensor: %s for sample rate", sample_rate_sensor.id)

                # Model sensor (device-level, not zone-specific)
                model_sensor = AnthemModelSensor(device_config, device)
                entities.append(model_sensor)
                _LOG.info("Created sensor: %s for model info", model_sensor.id)

            # Create select entity for listening mode (per zone)
            listening_mode_select = AnthemListeningModeSelect(device_config, device, zone_config)
            entities.append(listening_mode_select)
            _LOG.info(
                "Created select: %s for Zone %d listening mode",
                listening_mode_select.id,
                zone_config.zone_number,
            )

        return entities

    def device_from_entity_id(self, entity_id: str) -> str | None:
        """Extract device identifier, handling underscore-suffixed sensor/select IDs."""
        if not entity_id or "." not in entity_id:
            return None

        parts = entity_id.split(".")
        if len(parts) >= 3:
            return parts[1]

        candidate = parts[1]
        if candidate in self._device_instances:
            return candidate

        for device_id in self._device_instances:
            if candidate.startswith(device_id + "_"):
                return device_id

        return candidate

    def _zone_from_entity_id(self, entity_id: str) -> int:
        """Extract zone number from entity ID."""
        parts = entity_id.split(".")
        if len(parts) == 3 and parts[2].startswith("zone"):
            try:
                zone_part = parts[2].split("_")[0]
                return int(zone_part.replace("zone", ""))
            except ValueError:
                pass
        return 1

    async def refresh_entity_state(self, entity_id: str) -> None:
        """Refresh entity state from current device data and query for updates."""
        _LOG.info("[%s] Refreshing entity state", entity_id)

        device_id = self.device_from_entity_id(entity_id)
        if not device_id:
            _LOG.warning("[%s] Could not extract device_id", entity_id)
            return

        device = self._device_instances.get(device_id)
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

        zone_num = self._zone_from_entity_id(entity_id)
        zone_state = device.get_zone_state(zone_num)
        state_str = "ON" if zone_state.power else "OFF"
        vol_db = zone_state.volume_db if zone_state.volume_db is not None else -90
        volume_pct = max(0, min(100, int(((vol_db + 90) / 90) * 100)))

        if configured_entity.entity_type == EntityTypes.MEDIA_PLAYER:
            source_list = device.get_input_list()
            attrs = {
                media_player.Attributes.STATE: media_player.States.ON if zone_state.power else media_player.States.OFF,
                media_player.Attributes.VOLUME: volume_pct,
                media_player.Attributes.MUTED: bool(zone_state.muted),
            }
            if source_list:
                attrs[media_player.Attributes.SOURCE_LIST] = source_list
            if zone_state.input_name != "Unknown":
                attrs[media_player.Attributes.SOURCE] = zone_state.input_name
            self.api.configured_entities.update_attributes(entity_id, attrs)

        elif configured_entity.entity_type == EntityTypes.REMOTE:
            self.api.configured_entities.update_attributes(
                entity_id,
                {remote.Attributes.STATE: remote.States.ON if zone_state.power else remote.States.OFF},
            )

        elif configured_entity.entity_type == EntityTypes.SENSOR:
            sensor_attrs = {sensor.Attributes.STATE: sensor.States.ON}
            if "_volume" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = str(zone_state.volume_db if zone_state.volume_db is not None else -90)
            elif "_audio_format" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = zone_state.audio_format
            elif "_audio_channels" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = zone_state.audio_channels
            elif "_video_resolution" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = zone_state.video_resolution
            elif "_listening_mode" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = zone_state.listening_mode
            elif "_sample_rate" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = zone_state.sample_rate
            elif "_model" in entity_id:
                sensor_attrs[sensor.Attributes.VALUE] = device._model or "Unknown"
            self.api.configured_entities.update_attributes(entity_id, sensor_attrs)

        elif configured_entity.entity_type == EntityTypes.SELECT:
            self.api.configured_entities.update_attributes(
                entity_id,
                {
                    select.Attributes.STATE: select.States.ON,
                    select.Attributes.CURRENT_OPTION: zone_state.listening_mode,
                },
            )

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
                entity_ids.append(f"select.{device_id}_listening_mode")
                # Add sensor entity IDs (only for Zone 1)
                entity_ids.append(f"sensor.{device_id}_volume")
                entity_ids.append(f"sensor.{device_id}_audio_format")
                entity_ids.append(f"sensor.{device_id}_audio_channels")
                entity_ids.append(f"sensor.{device_id}_video_resolution")
                entity_ids.append(f"sensor.{device_id}_listening_mode")
                entity_ids.append(f"sensor.{device_id}_sample_rate")
                entity_ids.append(f"sensor.{device_id}_model")
            else:
                entity_ids.append(f"media_player.{device_id}.zone{zone.zone_number}")
                entity_ids.append(f"remote.{device_id}.zone{zone.zone_number}")
                entity_ids.append(f"select.{device_id}.zone{zone.zone_number}_listening_mode")

        return entity_ids
