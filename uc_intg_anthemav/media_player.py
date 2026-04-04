"""
Anthem Media Player entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.media_player import Attributes, Commands, DeviceClasses, Features, MediaPlayer, States, Options
from ucapi_framework import MediaPlayerEntity

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemMediaPlayer(MediaPlayerEntity):
    """Media player entity for Anthem A/V receiver zone."""

    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice, zone_config: ZoneConfig):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

        if zone_config.zone_number == 1:
            entity_id = f"media_player.{device_config.identifier}"
            entity_name = device_config.name
        else:
            entity_id = f"media_player.{device_config.identifier}.zone{zone_config.zone_number}"
            entity_name = f"{device_config.name} {zone_config.name}"

        features = [
            Features.ON_OFF,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.SELECT_SOURCE,
        ]

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: [],
        }

        options = {
            Options.SIMPLE_COMMANDS: [
                Commands.ON,
                Commands.OFF,
                Commands.VOLUME_UP,
                Commands.VOLUME_DOWN,
                Commands.MUTE_TOGGLE,
            ]
        }

        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            device_class=DeviceClasses.RECEIVER,
            cmd_handler=self._handle_command,
            options=options,
        )

        self.subscribe_to_device(device)

    async def sync_state(self):
        if not self._device.is_connected:
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return

        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        vol_db = zone_state.volume_db if zone_state.volume_db is not None else -90
        volume_pct = max(0, min(100, int(((vol_db + 90) / 90) * 100)))

        attrs = {
            Attributes.STATE: States.ON if zone_state.power else States.OFF,
            Attributes.VOLUME: volume_pct,
            Attributes.MUTED: bool(zone_state.muted),
        }
        source_list = self._device.get_input_list()
        if source_list:
            attrs[Attributes.SOURCE_LIST] = source_list
        if zone_state.input_name != "Unknown":
            attrs[Attributes.SOURCE] = zone_state.input_name
        self.update(attrs)

    async def _handle_command(
        self,
        entity: MediaPlayer,
        cmd_id: str,
        params: dict[str, Any] | None,
    ) -> StatusCodes:
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            zone = self._zone_config.zone_number

            if cmd_id == Commands.ON:
                success = await self._device.power_on(zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.OFF:
                success = await self._device.power_off(zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.VOLUME:
                if params and "volume" in params:
                    volume_pct = float(params["volume"])
                    volume_db = int((volume_pct * 90 / 100) - 90)
                    success = await self._device.set_volume(volume_db, zone)
                    return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                return StatusCodes.BAD_REQUEST

            elif cmd_id == Commands.VOLUME_UP:
                success = await self._device.volume_up(zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.VOLUME_DOWN:
                success = await self._device.volume_down(zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.MUTE_TOGGLE:
                success = await self._device.mute_toggle(zone)
                if success:
                    asyncio.create_task(self._device.query_volume(zone))
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.MUTE:
                success = await self._device.set_mute(True, zone)
                if success:
                    asyncio.create_task(self._device.query_volume(zone))
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.UNMUTE:
                success = await self._device.set_mute(False, zone)
                if success:
                    asyncio.create_task(self._device.query_volume(zone))
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.SELECT_SOURCE:
                if params and "source" in params:
                    source_name = params["source"]
                    input_num = self._device.get_input_number_by_name(source_name)
                    if input_num is not None:
                        success = await self._device.select_input(input_num, zone)
                        return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                    return StatusCodes.BAD_REQUEST
                return StatusCodes.BAD_REQUEST

            else:
                _LOG.debug("[%s] Unsupported command: %s", self.id, cmd_id)
                return StatusCodes.OK

        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    @property
    def zone_number(self) -> int:
        return self._zone_config.zone_number
