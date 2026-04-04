"""
Anthem Select Entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.select import Attributes, Commands, Select, States
from ucapi_framework import SelectEntity

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav import const
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


LISTENING_MODES_X40 = {
    "None": 0,
    "AnthemLogic Cinema": 1,
    "AnthemLogic Music": 2,
    "Dolby Surround": 3,
    "DTS Neural:X": 4,
    "DTS Virtual:X": 5,
    "All Channel Stereo": 6,
    "Mono": 7,
    "All Channel Mono": 8,
}

LISTENING_MODES_X20 = {
    "None": 0,
    "AnthemLogic Cinema": 1,
    "AnthemLogic Music": 2,
    "Dolby Surround": 14,
    "Neo:6 Cinema": 5,
    "Neo:6 Music": 6,
    "All Channel Stereo": 7,
    "Stereo": 15,
}


class AnthemListeningModeSelect(SelectEntity):
    """Select entity for choosing audio listening mode."""

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
            entity_id = f"select.{device_config.identifier}.listening_mode"
            entity_name = f"{device_config.name} Listening Mode"
        else:
            entity_id = f"select.{device_config.identifier}.zone{zone_config.zone_number}_listening_mode"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Listening Mode"

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.OPTIONS: [],
            Attributes.CURRENT_OPTION: "",
        }

        super().__init__(
            entity_id,
            entity_name,
            attributes,
            cmd_handler=self._handle_command,
        )

        self.subscribe_to_device(device)

    async def sync_state(self):
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if zone_state.power is None:
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        options_list = list(LISTENING_MODES_X20.keys()) if self._device.is_x20_series else list(LISTENING_MODES_X40.keys())
        current = zone_state.listening_mode
        self.update({
            Attributes.STATE: States.ON,
            Attributes.OPTIONS: options_list,
            Attributes.CURRENT_OPTION: current if current != "Unknown" else "",
        })

    def _get_alm_command(self, zone: int, mode_num: int) -> str:
        if self._device.is_x20_series:
            return f"Z{zone}ALM{mode_num:02d}"
        return f"Z{zone}ALM{mode_num}"

    def _get_mode_map(self) -> dict[str, int]:
        return LISTENING_MODES_X20 if self._device.is_x20_series else LISTENING_MODES_X40

    async def _handle_command(
        self, entity: Select, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            zone = self._zone_config.zone_number
            is_x20 = self._device.is_x20_series
            mode_map = self._get_mode_map()
            current_mode = self.attributes.get(Attributes.CURRENT_OPTION, "")
            options = self.attributes.get(Attributes.OPTIONS, [])

            if cmd_id == Commands.SELECT_OPTION:
                if not params or "option" not in params:
                    return StatusCodes.BAD_REQUEST

                option = params["option"]
                mode_num = mode_map.get(option)
                if mode_num is None:
                    mode_num = LISTENING_MODES_X40.get(option)
                if mode_num is None:
                    _LOG.warning("[%s] Mode not available: %s", self.id, option)
                    return StatusCodes.BAD_REQUEST

                success = await self._device._send_command(
                    self._get_alm_command(zone, mode_num)
                )
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.SELECT_NEXT:
                if current_mode and options:
                    try:
                        current_idx = options.index(current_mode)
                        next_idx = (current_idx + 1) % len(options)
                        next_mode = options[next_idx]
                        mode_num = mode_map.get(next_mode)
                        if mode_num is not None:
                            success = await self._device._send_command(
                                self._get_alm_command(zone, mode_num)
                            )
                            return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                    except ValueError:
                        pass
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}ALMna")
                else:
                    success = await self._device._send_command(f"Z{zone}AUP")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.SELECT_PREVIOUS:
                if current_mode and options:
                    try:
                        current_idx = options.index(current_mode)
                        prev_idx = (current_idx - 1) % len(options)
                        prev_mode = options[prev_idx]
                        mode_num = mode_map.get(prev_mode)
                        if mode_num is not None:
                            success = await self._device._send_command(
                                self._get_alm_command(zone, mode_num)
                            )
                            return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                    except ValueError:
                        pass
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}ALMpa")
                else:
                    success = await self._device._send_command(f"Z{zone}ADN")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.SELECT_FIRST:
                first_mode = options[0] if options else "None"
                mode_num = mode_map.get(first_mode, 0)
                success = await self._device._send_command(
                    self._get_alm_command(zone, mode_num)
                )
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.SELECT_LAST:
                last_mode = options[-1] if options else "All Channel Mono"
                mode_num = mode_map.get(last_mode)
                if mode_num is None:
                    mode_num = LISTENING_MODES_X40.get(last_mode, 8)
                success = await self._device._send_command(
                    self._get_alm_command(zone, mode_num)
                )
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            else:
                _LOG.warning("[%s] Unsupported command: %s", self.id, cmd_id)
                return StatusCodes.NOT_FOUND

        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    @property
    def zone_number(self) -> int:
        return self._zone_config.zone_number
