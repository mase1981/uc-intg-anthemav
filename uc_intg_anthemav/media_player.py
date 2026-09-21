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

from uc_intg_anthemav import const, volume as volume_scale
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

        # The receiver's Maximum Volume (GCMMV) clamps rather than rescales, so
        # everything above it is dead slider travel. Restricting VOLUME_STEPS to
        # the reachable percentage makes the core quantize to steps that land on
        # reachable values, and _to_device_volume() rescales the slider onto them.
        options = self._build_volume_options()

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

    def _build_volume_options(self) -> dict:
        """Entity options derived from the current Maximum Volume ceiling."""
        max_db = self._device.max_volume_db
        return {
            Options.SIMPLE_COMMANDS: [
                Commands.ON,
                Commands.OFF,
                Commands.VOLUME_UP,
                Commands.VOLUME_DOWN,
                Commands.MUTE_TOGGLE,
                *(
                    cmd
                    for cmd, db in const.VOLUME_DB_PRESETS.items()
                    if max_db is None or db <= max_db
                ),
            ],
            Options.VOLUME_STEPS: self._slider_max_percent,
        }

    def _refresh_volume_options(self) -> None:
        """Keep options in step with the ceiling instead of freezing them.

        The ceiling may be unknown when the entity is constructed, and the
        receiver pushes GCMMV unsolicited when it is changed in setup. ucapi
        serialises entity.options at the moment the core asks for the entity
        list, so correcting the attribute here means the next fetch sees the
        right values rather than whatever was true at registration.
        """
        rebuilt = self._build_volume_options()
        if rebuilt != self.options:
            self.options = rebuilt
            _LOG.info(
                "[%s] Volume options updated: volume_steps=%s, %d dB presets",
                self.id,
                rebuilt[Options.VOLUME_STEPS],
                len([c for c in rebuilt[Options.SIMPLE_COMMANDS] if c.startswith("VOLUME_DB")]),
            )

    @property
    def _slider_max_percent(self) -> int:
        """The receiver percentage that the slider's 100 corresponds to.

        In dB mode the receiver's front panel reads in dB, so nothing on the
        hardware contradicts a rescaled 0-100 and the whole slider is made
        usable by mapping it onto the reachable range.

        In per cent mode the panel shows the raw ZzPVOL, which is NOT adjusted
        for the Maximum Volume ceiling - it simply stops at it. Rescaling there
        would leave the remote reading up to 60 points away from the receiver's
        own display for the same volume (at a -20 dB ceiling the panel shows
        40% where a rescaled slider shows 100). The percentage is therefore
        passed through unchanged, which keeps the two displays in agreement at
        the cost of inheriting the receiver's own dead travel above the ceiling.
        """
        if self._device.volume_scale_is_percent:
            return 100
        return self._device.max_volume_percent

    def _to_ui_volume(self, device_percent: float) -> int:
        """Receiver percentage -> the 0-100 the UC slider works in."""
        return volume_scale.to_ui(device_percent, self._slider_max_percent)

    def _to_device_volume(self, ui_percent: float) -> int:
        """UC slider 0-100 -> a receiver percentage below the ceiling."""
        return volume_scale.to_device(ui_percent, self._slider_max_percent)

    async def sync_state(self):
        self._refresh_volume_options()
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if zone_state.power is None:
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return

        if (
            self._device.is_x40_series
            and not self._device.volume_scale_is_percent
            and zone_state.volume_db is not None
        ):
            # Prefer VOL over PVOL. The receiver pushes VOL on every 0.5 dB VUP/VDN
            # step but PVOL only when the integer percent changes - which in the
            # -53..-35 dB band is once every 2 dB, i.e. every fourth press. Driving
            # the UI from PVOL made the displayed value visibly lag the volume.
            #
            # Only valid in dB mode: with Master Volume Scale set to per cent the
            # receiver reports VOL as (percent - 90) rather than true dB, so PVOL
            # below - which means the same thing in both modes - is used instead.
            volume_pct = self._to_ui_volume(
                volume_scale.db_to_percent_exact(zone_state.volume_db)
            )
        elif zone_state.volume_pct is not None:
            volume_pct = self._to_ui_volume(zone_state.volume_pct)
        else:
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
                    if self._device.is_x20_series:
                        volume_db = int((volume_pct * 90 / 100) - 90)
                        success = await self._device.set_volume(volume_db, zone)
                    else:
                        success = await self._device.set_volume_percent(
                            self._to_device_volume(volume_pct), zone
                        )
                    return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                return StatusCodes.BAD_REQUEST

            elif cmd_id == Commands.VOLUME_UP:
                if self._device.is_x40_series:
                    success = await self._device.volume_up_step(zone)
                else:
                    success = await self._device.volume_up(zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == Commands.VOLUME_DOWN:
                if self._device.is_x40_series:
                    success = await self._device.volume_down_step(zone)
                else:
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

            elif cmd_id in const.VOLUME_DB_PRESETS:
                target_db = const.VOLUME_DB_PRESETS[cmd_id]
                success = await self._device.set_volume(target_db, zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            else:
                _LOG.debug("[%s] Unsupported command: %s", self.id, cmd_id)
                return StatusCodes.OK

        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    @property
    def zone_number(self) -> int:
        return self._zone_config.zone_number
