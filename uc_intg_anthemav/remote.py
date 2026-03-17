"""
Anthem Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.remote import Attributes, Commands, Features, Options, Remote, States

from .config import AnthemDeviceConfig, ZoneConfig
from . import const
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


_ALM_X40 = {
    "DOLBY_SURROUND": 3,
    "DTS_NEURAL_X": 4,
    "ANTHEMLOGIC_CINEMA": 1,
    "ANTHEMLOGIC_MUSIC": 2,
    "STEREO": 5,
    "MULTI_CHANNEL_STEREO": 6,
    "ALL_CHANNEL_STEREO": 7,
    "PLIIX_MOVIE": 8,
    "PLIIX_MUSIC": 9,
    "NEO6_CINEMA": 10,
    "NEO6_MUSIC": 11,
    "DOLBY_DIGITAL": 12,
    "DTS": 13,
    "PCM_STEREO": 14,
    "DIRECT": 15,
}

_ALM_X20 = {
    "DOLBY_SURROUND": 14,
    "ANTHEMLOGIC_CINEMA": 1,
    "ANTHEMLOGIC_MUSIC": 2,
    "ALL_CHANNEL_STEREO": 7,
    "NEO6_CINEMA": 5,
    "NEO6_MUSIC": 6,
    "STEREO": 15,
}

_SPEAKER_CH_X20 = {
    "LEVEL_SUBWOOFER": const.SPEAKER_CH_X20_SUBS,
    "LEVEL_FRONTS": const.SPEAKER_CH_X20_FRONTS,
    "LEVEL_CENTER": const.SPEAKER_CH_X20_CENTER,
    "LEVEL_SURROUNDS": const.SPEAKER_CH_X20_SURROUNDS,
    "LEVEL_BACKS": const.SPEAKER_CH_X20_BACKS,
    "LEVEL_HEIGHTS": const.SPEAKER_CH_X20_HEIGHTS,
}

_SPEAKER_CH_X40 = {
    "LEVEL_SUBWOOFER": 1,
    "LEVEL_FRONTS": 5,
    "LEVEL_CENTER": 7,
    "LEVEL_SURROUNDS": 8,
    "LEVEL_BACKS": 9,
    "LEVEL_HEIGHTS": 10,
}


class AnthemRemote(Remote):

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
            entity_id = f"remote.{device_config.identifier}"
            entity_name = f"{device_config.name} Advanced Audio"
        else:
            entity_id = (
                f"remote.{device_config.identifier}.zone{zone_config.zone_number}"
            )
            entity_name = (
                f"{device_config.name} Zone {zone_config.zone_number} Advanced Audio"
            )

        features = [Features.SEND_CMD]
        attributes = {}

        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            cmd_handler=self.handle_command,
        )

        is_x20 = device_config.is_x20_series
        simple_commands, user_interface = self._build_ui(is_x20)

        self.options = {
            Options.SIMPLE_COMMANDS: simple_commands,
            "user_interface": user_interface,
        }

        _LOG.info(
            "[%s] Remote entity initialized (%s) with %d commands",
            entity_id,
            "x20" if is_x20 else "x40",
            len(simple_commands),
        )

        device.events.on("UPDATE", self._on_device_update)

    def _build_ui(self, is_x20: bool) -> tuple[list[str], dict]:
        simple_commands = []
        pages = []

        pages.append(self._build_audio_modes_page(is_x20, simple_commands))
        pages.append(self._build_tone_control_page(simple_commands))
        pages.append(self._build_dolby_settings_page(is_x20, simple_commands))
        pages.append(self._build_system_settings_page(is_x20, simple_commands))
        pages.append(self._build_speaker_levels_page(simple_commands))

        return simple_commands, {"pages": pages}

    def _build_audio_modes_page(self, is_x20: bool, cmds: list[str]) -> dict:
        items = []
        y = 0

        if is_x20:
            modes = [
                ("Dolby\nSurround", "DOLBY_SURROUND", 2),
                ("AnthemLogic\nCinema", "ANTHEMLOGIC_CINEMA", 2),
                ("AnthemLogic\nMusic", "ANTHEMLOGIC_MUSIC", 2),
                ("Neo:6\nCinema", "NEO6_CINEMA", 2),
                ("Neo:6\nMusic", "NEO6_MUSIC", 2),
                ("All-Ch\nStereo", "ALL_CHANNEL_STEREO", 2),
                ("Stereo", "STEREO", 2),
            ]
        else:
            modes = [
                ("Dolby\nSurround", "DOLBY_SURROUND", 2),
                ("DTS\nNeural:X", "DTS_NEURAL_X", 2),
                ("AnthemLogic\nCinema", "ANTHEMLOGIC_CINEMA", 2),
                ("AnthemLogic\nMusic", "ANTHEMLOGIC_MUSIC", 2),
                ("Stereo", "STEREO", 2),
                ("Multi-Ch\nStereo", "MULTI_CHANNEL_STEREO", 2),
                ("Direct", "DIRECT", 1),
                ("All-Ch\nStereo", "ALL_CHANNEL_STEREO", 1),
                ("PLIIx\nMovie", "PLIIX_MOVIE", 1),
                ("PLIIx\nMusic", "PLIIX_MUSIC", 1),
                ("Neo:6\nCinema", "NEO6_CINEMA", 1),
                ("Neo:6\nMusic", "NEO6_MUSIC", 1),
                ("Dolby\nDigital", "DOLBY_DIGITAL", 1),
                ("DTS", "DTS", 1),
                ("PCM\nStereo", "PCM_STEREO", 1),
            ]

        x = 0
        for label, cmd_id, width in modes:
            if x + width > 4:
                y += 1
                x = 0
            items.append({
                "type": "text", "text": label,
                "command": {"cmd_id": cmd_id},
                "location": {"x": x, "y": y},
                "size": {"width": width, "height": 1},
            })
            cmds.append(cmd_id)
            x += width
            if x >= 4:
                y += 1
                x = 0

        if x > 0:
            y += 1
            x = 0

        cmds.extend(["AUDIO_MODE_UP", "AUDIO_MODE_DOWN"])
        items.append({
            "type": "icon", "icon": "uc:up-arrow",
            "command": {"cmd_id": "AUDIO_MODE_UP"},
            "location": {"x": 0, "y": y},
        })
        items.append({
            "type": "icon", "icon": "uc:down-arrow",
            "command": {"cmd_id": "AUDIO_MODE_DOWN"},
            "location": {"x": 1, "y": y},
        })

        if not is_x20:
            cmds.append("INFO")
            items.append({
                "type": "text", "text": "Info",
                "command": {"cmd_id": "INFO"},
                "location": {"x": 3, "y": y},
                "size": {"width": 1, "height": 1},
            })

        return {
            "page_id": "audio_modes", "name": "Audio Modes",
            "grid": {"width": 4, "height": y + 1}, "items": items,
        }

    def _build_tone_control_page(self, cmds: list[str]) -> dict:
        cmds.extend([
            "BASS_UP", "BASS_DOWN", "TREBLE_UP", "TREBLE_DOWN",
            "BALANCE_LEFT", "BALANCE_RIGHT",
        ])
        return {
            "page_id": "tone_control", "name": "Tone Control",
            "grid": {"width": 4, "height": 3},
            "items": [
                {"type": "text", "text": "Bass", "location": {"x": 0, "y": 0}, "size": {"width": 2, "height": 1}},
                {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "BASS_UP"}, "location": {"x": 2, "y": 0}},
                {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "BASS_DOWN"}, "location": {"x": 3, "y": 0}},
                {"type": "text", "text": "Treble", "location": {"x": 0, "y": 1}, "size": {"width": 2, "height": 1}},
                {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "TREBLE_UP"}, "location": {"x": 2, "y": 1}},
                {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "TREBLE_DOWN"}, "location": {"x": 3, "y": 1}},
                {"type": "text", "text": "Balance", "location": {"x": 0, "y": 2}, "size": {"width": 2, "height": 1}},
                {"type": "icon", "icon": "uc:left-arrow", "command": {"cmd_id": "BALANCE_LEFT"}, "location": {"x": 2, "y": 2}},
                {"type": "icon", "icon": "uc:right-arrow", "command": {"cmd_id": "BALANCE_RIGHT"}, "location": {"x": 3, "y": 2}},
            ],
        }

    def _build_dolby_settings_page(self, is_x20: bool, cmds: list[str]) -> dict:
        cmds.extend(["DOLBY_DRC_NORMAL", "DOLBY_DRC_REDUCED", "DOLBY_DRC_LATE_NIGHT"])
        items = [
            {"type": "text", "text": "DRC\nNormal", "command": {"cmd_id": "DOLBY_DRC_NORMAL"}, "location": {"x": 0, "y": 0}, "size": {"width": 2, "height": 1}},
            {"type": "text", "text": "DRC\nReduced", "command": {"cmd_id": "DOLBY_DRC_REDUCED"}, "location": {"x": 2, "y": 0}, "size": {"width": 2, "height": 1}},
            {"type": "text", "text": "DRC\nLate Night", "command": {"cmd_id": "DOLBY_DRC_LATE_NIGHT"}, "location": {"x": 0, "y": 1}, "size": {"width": 2, "height": 1}},
        ]
        height = 2
        if not is_x20:
            cmds.extend(["DOLBY_CENTER_SPREAD_ON", "DOLBY_CENTER_SPREAD_OFF"])
            items.extend([
                {"type": "text", "text": "Center\nSpread ON", "command": {"cmd_id": "DOLBY_CENTER_SPREAD_ON"}, "location": {"x": 0, "y": 2}, "size": {"width": 2, "height": 1}},
                {"type": "text", "text": "Center\nSpread OFF", "command": {"cmd_id": "DOLBY_CENTER_SPREAD_OFF"}, "location": {"x": 2, "y": 2}, "size": {"width": 2, "height": 1}},
            ])
            height = 3
        return {
            "page_id": "dolby_settings", "name": "Dolby Settings",
            "grid": {"width": 4, "height": height}, "items": items,
        }

    def _build_system_settings_page(self, is_x20: bool, cmds: list[str]) -> dict:
        items = []
        y = 0

        cmds.extend(["BRIGHTNESS_UP", "BRIGHTNESS_DOWN"])
        items.extend([
            {"type": "text", "text": "Display\nBrightness", "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
            {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "BRIGHTNESS_UP"}, "location": {"x": 2, "y": y}},
            {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "BRIGHTNESS_DOWN"}, "location": {"x": 3, "y": y}},
        ])
        y += 1

        if not is_x20:
            cmds.extend(["DISPLAY_ALL", "DISPLAY_VOLUME_ONLY"])
            items.extend([
                {"type": "text", "text": "Display\nAll Info", "command": {"cmd_id": "DISPLAY_ALL"}, "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
                {"type": "text", "text": "Display\nVol Only", "command": {"cmd_id": "DISPLAY_VOLUME_ONLY"}, "location": {"x": 2, "y": y}, "size": {"width": 2, "height": 1}},
            ])
            y += 1

            cmds.extend(["HDMI_BYPASS_OFF", "HDMI_BYPASS_LAST"])
            items.extend([
                {"type": "text", "text": "HDMI\nBypass OFF", "command": {"cmd_id": "HDMI_BYPASS_OFF"}, "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
                {"type": "text", "text": "HDMI\nBypass ON", "command": {"cmd_id": "HDMI_BYPASS_LAST"}, "location": {"x": 2, "y": y}, "size": {"width": 2, "height": 1}},
            ])
            y += 1

            cmds.extend(["CEC_ON", "CEC_OFF"])
            items.extend([
                {"type": "text", "text": "CEC\nON", "command": {"cmd_id": "CEC_ON"}, "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
                {"type": "text", "text": "CEC\nOFF", "command": {"cmd_id": "CEC_OFF"}, "location": {"x": 2, "y": y}, "size": {"width": 2, "height": 1}},
            ])
            y += 1

        cmds.extend(["ARC_ON", "ARC_OFF"])
        items.extend([
            {"type": "text", "text": "ARC\nON", "command": {"cmd_id": "ARC_ON"}, "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
            {"type": "text", "text": "ARC\nOFF", "command": {"cmd_id": "ARC_OFF"}, "location": {"x": 2, "y": y}, "size": {"width": 2, "height": 1}},
        ])
        y += 1

        return {
            "page_id": "system_settings", "name": "System Settings",
            "grid": {"width": 4, "height": y}, "items": items,
        }

    def _build_speaker_levels_page(self, cmds: list[str]) -> dict:
        speakers = [
            ("Subwoofer", "LEVEL_SUBWOOFER"),
            ("Fronts", "LEVEL_FRONTS"),
            ("Center", "LEVEL_CENTER"),
            ("Surrounds", "LEVEL_SURROUNDS"),
            ("Backs", "LEVEL_BACKS"),
            ("Heights", "LEVEL_HEIGHTS"),
        ]
        items = []
        for y, (label, prefix) in enumerate(speakers):
            cmds.extend([f"{prefix}_UP", f"{prefix}_DOWN"])
            items.extend([
                {"type": "text", "text": label, "location": {"x": 0, "y": y}, "size": {"width": 2, "height": 1}},
                {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": f"{prefix}_UP"}, "location": {"x": 2, "y": y}},
                {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": f"{prefix}_DOWN"}, "location": {"x": 3, "y": y}},
            ])
        return {
            "page_id": "speaker_levels", "name": "Speaker Levels",
            "grid": {"width": 4, "height": len(speakers)}, "items": items,
        }

    async def _on_device_update(
        self, entity_id: str, update_data: dict[str, Any]
    ) -> None:
        if entity_id == self._get_media_player_id():
            state_val = update_data.get("state")
            if state_val in ("ON", "OFF"):
                new_state = States.ON if state_val == "ON" else States.OFF
                if self.attributes.get(Attributes.STATE) != new_state:
                    self.attributes[Attributes.STATE] = new_state
                    _LOG.debug("[%s] State updated to %s", self.id, state_val)

    def _get_media_player_id(self) -> str:
        if self._zone_config.zone_number == 1:
            return f"media_player.{self._device_config.identifier}"
        return f"media_player.{self._device_config.identifier}.zone{self._zone_config.zone_number}"

    def _get_alm_command(self, zone: int, mode_num: int) -> str:
        if self._device.is_x20_series:
            return f"Z{zone}ALM{mode_num:02d}"
        return f"Z{zone}ALM{mode_num}"

    async def handle_command(
        self, entity: Remote, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            zone = self._zone_config.zone_number
            is_x20 = self._device.is_x20_series

            if cmd_id != Commands.SEND_CMD:
                _LOG.warning("[%s] Unsupported command type: %s", self.id, cmd_id)
                return StatusCodes.NOT_FOUND

            if not params or "command" not in params:
                _LOG.error("[%s] Missing command parameter", self.id)
                return StatusCodes.BAD_REQUEST

            command = params["command"]
            success = False

            alm_map = _ALM_X20 if is_x20 else _ALM_X40
            alm_num = alm_map.get(command)
            if alm_num is not None:
                success = await self._device._send_command(
                    self._get_alm_command(zone, alm_num)
                )
            elif command in _ALM_X40 and is_x20:
                _LOG.info("[%s] %s not available on x20 series", self.id, command)
                return StatusCodes.OK
            elif command == "AUDIO_MODE_UP":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}ALMna")
                else:
                    success = await self._device._send_command(f"Z{zone}AUP")
            elif command == "AUDIO_MODE_DOWN":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}ALMpa")
                else:
                    success = await self._device._send_command(f"Z{zone}ADN")
            elif command == "BASS_UP":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TUP001")
                else:
                    success = await self._device._send_command(f"Z{zone}TUP0")
            elif command == "BASS_DOWN":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TDN001")
                else:
                    success = await self._device._send_command(f"Z{zone}TDN0")
            elif command == "TREBLE_UP":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TUP101")
                else:
                    success = await self._device._send_command(f"Z{zone}TUP1")
            elif command == "TREBLE_DOWN":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TDN101")
                else:
                    success = await self._device._send_command(f"Z{zone}TDN1")
            elif command == "BALANCE_LEFT":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TDN201")
                else:
                    success = await self._device._send_command(f"Z{zone}BLT")
            elif command == "BALANCE_RIGHT":
                if is_x20:
                    success = await self._device._send_command(f"Z{zone}TUP201")
                else:
                    success = await self._device._send_command(f"Z{zone}BRT")
            elif command == "DOLBY_DRC_NORMAL":
                success = await self._device._send_command(f"Z{zone}DYN0")
            elif command == "DOLBY_DRC_REDUCED":
                success = await self._device._send_command(f"Z{zone}DYN1")
            elif command == "DOLBY_DRC_LATE_NIGHT":
                success = await self._device._send_command(f"Z{zone}DYN2")
            elif command == "DOLBY_CENTER_SPREAD_ON":
                if is_x20:
                    _LOG.info("[%s] Center Spread not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device._send_command(f"Z{zone}DSCS1")
            elif command == "DOLBY_CENTER_SPREAD_OFF":
                if is_x20:
                    _LOG.info("[%s] Center Spread not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device._send_command(f"Z{zone}DSCS0")
            elif command == "INFO":
                if is_x20:
                    _LOG.info("[%s] OSD info not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_osd_info(1)
            elif command == "ARC_ON":
                input_num = self._device.get_zone_state(zone).input_number
                success = await self._device.set_arc(True, input_num)
            elif command == "ARC_OFF":
                input_num = self._device.get_zone_state(zone).input_number
                success = await self._device.set_arc(False, input_num)
            elif command == "BRIGHTNESS_UP":
                if is_x20:
                    success = await self._device.set_front_panel_brightness(3)
                else:
                    success = await self._device.set_front_panel_brightness(50)
            elif command == "BRIGHTNESS_DOWN":
                if is_x20:
                    success = await self._device.set_front_panel_brightness(1)
                else:
                    success = await self._device.set_front_panel_brightness(20)
            elif command == "DISPLAY_ALL":
                if is_x20:
                    _LOG.info("[%s] Display mode not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_front_panel_display(0)
            elif command == "DISPLAY_VOLUME_ONLY":
                if is_x20:
                    _LOG.info("[%s] Display mode not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_front_panel_display(1)
            elif command == "HDMI_BYPASS_OFF":
                if is_x20:
                    _LOG.info("[%s] HDMI bypass not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_hdmi_standby_bypass(0)
            elif command == "HDMI_BYPASS_LAST":
                if is_x20:
                    _LOG.info("[%s] HDMI bypass not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_hdmi_standby_bypass(1)
            elif command == "CEC_ON":
                if is_x20:
                    _LOG.info("[%s] CEC control not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_cec_control(True)
            elif command == "CEC_OFF":
                if is_x20:
                    _LOG.info("[%s] CEC control not available on x20 series", self.id)
                    return StatusCodes.OK
                success = await self._device.set_cec_control(False)
            elif command.startswith("LEVEL_") and command.endswith(("_UP", "_DOWN")):
                is_up = command.endswith("_UP")
                base = command.rsplit("_", 1)[0]
                ch_map = _SPEAKER_CH_X20 if is_x20 else _SPEAKER_CH_X40
                channel = ch_map.get(base)
                if channel is not None:
                    if is_up:
                        success = await self._device.speaker_level_up(channel, zone)
                    else:
                        success = await self._device.speaker_level_down(channel, zone)
                else:
                    _LOG.warning("[%s] Unknown speaker channel: %s", self.id, base)
                    return StatusCodes.NOT_FOUND
            else:
                _LOG.warning("[%s] Unknown audio command: %s", self.id, command)
                return StatusCodes.NOT_FOUND

            if not success:
                _LOG.error("[%s] Command failed to send to device", self.id)
                return StatusCodes.SERVER_ERROR

            return StatusCodes.OK

        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    @property
    def zone_number(self) -> int:
        return self._zone_config.zone_number