"""
Anthem Sensor Entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi.sensor import Attributes, DeviceClasses, Options, States
from ucapi_framework import SensorEntity

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemSensor(SensorEntity):
    """Generic sensor entity for Anthem device values."""

    def __init__(self, entity_id, name, device, sensor_key, unit=None):
        attrs = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VALUE: "",
        }
        options = {}
        if unit:
            options = {Options.CUSTOM_UNIT: unit}

        super().__init__(
            entity_id,
            name,
            [],
            attrs,
            device_class=DeviceClasses.CUSTOM,
            options=options,
        )
        self._device = device
        self._sensor_key = sensor_key
        self.subscribe_to_device(device)

    async def sync_state(self):
        if self._device.get_zone_state(1).power is None:
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        value = self._device.get_sensor_value(self._sensor_key)
        self.update({
            Attributes.STATE: States.ON,
            Attributes.VALUE: value or "Unknown",
        })


def create_sensors(config: AnthemDeviceConfig, device: AnthemDevice) -> list:
    """Create all sensor entities for Zone 1."""
    device_id = config.identifier
    sensor_defs = [
        ("volume", f"{config.name} Volume", "dB"),
        ("audio_format", f"{config.name} Audio Format", None),
        ("audio_channels", f"{config.name} Audio Channels", None),
        ("video_resolution", f"{config.name} Video Resolution", None),
        ("listening_mode", f"{config.name} Listening Mode", None),
        ("sample_rate", f"{config.name} Sample Rate", None),
        ("model", f"{config.name} Model", None),
    ]
    sensors = []
    for key, name, unit in sensor_defs:
        entity_id = f"sensor.{device_id}.{key}"
        sensors.append(AnthemSensor(entity_id, name, device, key, unit))
    return sensors
