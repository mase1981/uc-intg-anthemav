"""
Anthem Select Entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.select import Attributes, Commands, Select, States

from .config import AnthemDeviceConfig, ZoneConfig
from . import const
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


LISTENING_MODES = {
    "None": 0,
    "AnthemLogic Cinema": 1,
    "AnthemLogic Music": 2,
    "Dolby Surround": 3,
    "DTS Neural:X": 4,
    "Stereo": 5,
    "Multi-Channel Stereo": 6,
    "All-Channel Stereo": 7,
    "PLIIx Movie": 8,
    "PLIIx Music": 9,
    "Neo:6 Cinema": 10,
    "Neo:6 Music": 11,
    "Dolby Digital": 12,
    "DTS": 13,
    "PCM Stereo": 14,
    "Direct": 15,
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

LISTENING_MODE_NAMES = {v: k for k, v in LISTENING_MODES.items()}


class AnthemListeningModeSelect(Select):
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
            entity_id = f"select.{device_config.identifier}_listening_mode"
            entity_name = f"{device_config.name} Listening Mode"
        else:
            entity_id = f"select.{device_config.identifier}.zone{zone_config.zone_number}_listening_mode"
            entity_name = f"{device_config.name} Zone {zone_config.zone_number} Listening Mode"

        if device_config.is_x20_series:
            options_list = list(LISTENING_MODES_X20.keys())
        else:
            options_list = list(LISTENING_MODES.keys())

        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.OPTIONS: options_list,
            Attributes.CURRENT_OPTION: "",
        }

        super().__init__(
            entity_id,
            entity_name,
            attributes,
            cmd_handler=self.handle_command,
        )

        _LOG.info(
            "[%s] Listening mode select initialized for Zone %d with %d options",
            entity_id,
            zone_config.zone_number,
            len(options_list),
        )

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """Handle device updates for listening mode select."""
        expected_sensor_id = (
            f"sensor.{self._device_config.identifier}_listening_mode"
            if self._zone_config.zone_number == 1
            else f"sensor.{self._device_config.identifier}.zone{self._zone_config.zone_number}_listening_mode"
        )

        if entity_id == expected_sensor_id:
            zone_state = self._device.get_zone_state(self._zone_config.zone_number)
            mode_name = zone_state.listening_mode
            self.attributes[Attributes.STATE] = States.ON
            self.attributes[Attributes.CURRENT_OPTION] = mode_name
            _LOG.debug("[%s] Listening mode updated to %s", self.id, mode_name)

    def _get_alm_command(self, zone: int, mode_num: int) -> str:
        if self._device.is_x20_series:
            return f"Z{zone}ALM{mode_num:02d}"
        return f"Z{zone}ALM{mode_num}"

    def _get_mode_map(self) -> dict[str, int]:
        return LISTENING_MODES_X20 if self._device.is_x20_series else LISTENING_MODES

    async def handle_command(
        self, entity: Select, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle select commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            zone = self._zone_config.zone_number
            is_x20 = self._device.is_x20_series
            mode_map = self._get_mode_map()
            current_mode = self.attributes.get(Attributes.CURRENT_OPTION, "")
            options = self.attributes.get(Attributes.OPTIONS, [])

            if cmd_id == Commands.SELECT_OPTION:
                if not params or "option" not in params:
                    _LOG.error("[%s] Missing option parameter", self.id)
                    return StatusCodes.BAD_REQUEST

                option = params["option"]
                mode_num = mode_map.get(option)
                if mode_num is None:
                    mode_num = LISTENING_MODES.get(option)
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
                last_mode = options[-1] if options else "Direct"
                mode_num = mode_map.get(last_mode)
                if mode_num is None:
                    mode_num = LISTENING_MODES.get(last_mode, 15)
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
        """Get zone number."""
        return self._zone_config.zone_number
