"""
Anthem Sensor Entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi.sensor import Attributes, DeviceClasses, Sensor, States

from .config import AnthemDeviceConfig, ZoneConfig
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemVolumeSensor(Sensor):
    """Sensor for displaying volume in dB (since media player only shows percentage)."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_volume"
            entity_name = f"{device_config.name} Volume"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_volume"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Volume"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
            Attributes.UNIT: "dB",
        }

        options = {"CUSTOM_UNIT": "dB"}

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
            options=options,
        )

        _LOG.info("[%s] Volume sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for volume sensor."""
        # Check if update is for our zone's media player
        expected_media_player_id = (
            f"media_player.{self._device_config.identifier}"
            if self._zone_config.zone_number == 1
            else f"media_player.{self._device_config.identifier}.zone{self._zone_config.zone_number}"
        )

        if entity_id == expected_media_player_id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "volume_db" in zone_state:
                volume_db = zone_state["volume_db"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = str(volume_db)
                _LOG.debug("[%s] Volume updated to %d dB", self.id, volume_db)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "volume_db" in zone_state:
            volume_db = zone_state["volume_db"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = str(volume_db)
            _LOG.debug("[%s] Volume updated to %d dB", self.id, volume_db)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number


class AnthemAudioFormatSensor(Sensor):
    """Sensor for displaying current audio input format."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_audio_format"
            entity_name = f"{device_config.name} Audio Format"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_audio_format"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Audio Format"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
        }

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        _LOG.info("[%s] Audio format sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for audio format sensor."""
        if entity_id == self.id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "audio_format" in zone_state:
                audio_format = zone_state["audio_format"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = audio_format
                _LOG.debug("[%s] Audio format updated to %s", self.id, audio_format)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "audio_format" in zone_state:
            audio_format = zone_state["audio_format"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = audio_format
            _LOG.debug("[%s] Audio format updated to %s", self.id, audio_format)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number


class AnthemAudioChannelsSensor(Sensor):
    """Sensor for displaying current audio channel configuration."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_audio_channels"
            entity_name = f"{device_config.name} Audio Channels"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_audio_channels"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Audio Channels"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
        }

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        _LOG.info("[%s] Audio channels sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for audio channels sensor."""
        if entity_id == self.id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "audio_channels" in zone_state:
                audio_channels = zone_state["audio_channels"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = audio_channels
                _LOG.debug("[%s] Audio channels updated to %s", self.id, audio_channels)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "audio_channels" in zone_state:
            audio_channels = zone_state["audio_channels"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = audio_channels
            _LOG.debug("[%s] Audio channels updated to %s", self.id, audio_channels)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number


class AnthemVideoResolutionSensor(Sensor):
    """Sensor for displaying current video resolution."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_video_resolution"
            entity_name = f"{device_config.name} Video Resolution"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_video_resolution"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Video Resolution"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
        }

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        _LOG.info("[%s] Video resolution sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for video resolution sensor."""
        if entity_id == self.id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "video_resolution" in zone_state:
                video_resolution = zone_state["video_resolution"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = video_resolution
                _LOG.debug("[%s] Video resolution updated to %s", self.id, video_resolution)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "video_resolution" in zone_state:
            video_resolution = zone_state["video_resolution"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = video_resolution
            _LOG.debug("[%s] Video resolution updated to %s", self.id, video_resolution)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number


class AnthemListeningModeSensor(Sensor):
    """Sensor for displaying current listening/audio processing mode."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_listening_mode"
            entity_name = f"{device_config.name} Listening Mode"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_listening_mode"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Listening Mode"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
        }

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        _LOG.info("[%s] Listening mode sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for listening mode sensor."""
        if entity_id == self.id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "listening_mode" in zone_state:
                listening_mode = zone_state["listening_mode"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = listening_mode
                _LOG.debug("[%s] Listening mode updated to %s", self.id, listening_mode)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "listening_mode" in zone_state:
            listening_mode = zone_state["listening_mode"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = listening_mode
            _LOG.debug("[%s] Listening mode updated to %s", self.id, listening_mode)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number


class AnthemSampleRateSensor(Sensor):
    """Sensor for displaying current audio sample rate and bit depth."""

    def __init__(
        self,
        device_config: AnthemDeviceConfig,
        device: AnthemDevice,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"sensor.{device_config.identifier}_sample_rate"
            entity_name = f"{device_config.name} Sample Rate"
        else:
            entity_id = f"sensor.{device_config.identifier}.zone{zone_config.zone_number}_sample_rate"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Sample Rate"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "Unknown",
        }

        super().__init__(
            entity_id,
            entity_name,
            [],
            attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        _LOG.info("[%s] Sample rate sensor initialized for Zone %d", entity_id, zone_config.zone_number)

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for sample rate sensor."""
        if entity_id == self.id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            if "sample_rate" in zone_state:
                sample_rate = zone_state["sample_rate"]
                self.attributes[Attributes.STATE] = States.ON
                self.attributes[Attributes.VALUE] = sample_rate
                _LOG.debug("[%s] Sample rate updated to %s", self.id, sample_rate)

    def update_from_device(self) -> None:
        """Update sensor value from device state (called after data received)."""
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if "sample_rate" in zone_state:
            sample_rate = zone_state["sample_rate"]
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.VALUE] = sample_rate
            _LOG.debug("[%s] Sample rate updated to %s", self.id, sample_rate)

    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number
