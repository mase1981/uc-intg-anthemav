"""
Anthem Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.remote import Attributes, Commands, Features, Remote, States
from ucapi_framework import RemoteEntity

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav import const
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


_ALM_X40 = {
    "ANTHEMLOGIC_CINEMA": 1,
    "ANTHEMLOGIC_MUSIC": 2,
    "DOLBY_SURROUND": 3,
    "DTS_NEURAL_X": 4,
    "DTS_VIRTUAL_X": 5,
    "ALL_CHANNEL_STEREO": 6,
    "MONO": 7,
    "ALL_CHANNEL_MONO": 8,
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

# Simulated-IR (ZxSIMyyyy) keys. Identical codes on x20 and x40 (verified
# against both IP/RS-232 specs), so no platform branching is needed. Main-Zone
# only per both specs. Event-model: set-only, no state feedback -- the only
# protocol path to drive the on-screen Setup/OSD menu and numeric entry.
_SIM_CODES = {
    "CURSOR_UP": "0018",
    "CURSOR_DOWN": "0019",
    "CURSOR_LEFT": "0020",
    "CURSOR_RIGHT": "0021",
    "CURSOR_ENTER": "0022",
    "SETUP": "0012",
    "BACK": "0028",
    "INFO_IR": "0017",
    "PAGE_UP": "0023",
    "PAGE_DOWN": "0024",
    "CLEAR": "0035",
    "PRESET": "0036",
    "DIGIT_0": "0000",
    "DIGIT_1": "0001",
    "DIGIT_2": "0002",
    "DIGIT_3": "0003",
    "DIGIT_4": "0004",
    "DIGIT_5": "0005",
    "DIGIT_6": "0006",
    "DIGIT_7": "0007",
    "DIGIT_8": "0008",
    "DIGIT_9": "0009",
}


def _build_ui(is_x20: bool, zone_number: int) -> tuple[list[str], dict]:
    simple_commands = []
    pages = []

    pages.append(_build_audio_modes_page(is_x20, simple_commands))
    pages.append(_build_tone_control_page(simple_commands))
    pages.append(_build_dolby_settings_page(is_x20, simple_commands))
    pages.append(_build_system_settings_page(is_x20, simple_commands))
    pages.append(_build_speaker_levels_page(simple_commands))

    # Navigation/OSD + keypad keys are Main-Zone only per both specs.
    if zone_number == 1:
        pages.append(_build_navigation_page(simple_commands))
        pages.append(_build_keypad_page(simple_commands))

    return simple_commands, {"pages": pages}


def _build_audio_modes_page(is_x20: bool, cmds: list[str]) -> dict:
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
            ("DTS\nVirtual:X", "DTS_VIRTUAL_X", 2),
            ("AnthemLogic\nCinema", "ANTHEMLOGIC_CINEMA", 2),
            ("AnthemLogic\nMusic", "ANTHEMLOGIC_MUSIC", 2),
            ("All-Ch\nStereo", "ALL_CHANNEL_STEREO", 2),
            ("Mono", "MONO", 2),
            ("All-Ch\nMono", "ALL_CHANNEL_MONO", 2),
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


def _build_tone_control_page(cmds: list[str]) -> dict:
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


def _build_dolby_settings_page(is_x20: bool, cmds: list[str]) -> dict:
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


def _build_system_settings_page(is_x20: bool, cmds: list[str]) -> dict:
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


def _build_speaker_levels_page(cmds: list[str]) -> dict:
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


def _build_navigation_page(cmds: list[str]) -> dict:
    # Echoes the physical RC-MRX 2 nav cluster: Setup/Info above the D-pad,
    # Clear/Last below it, page keys at the bottom corners.
    # Info here is the simulated-IR remote key (INFO_IR / SIM 0017), distinct
    # from the native OSD-overlay "INFO" command on the Audio Modes page.
    cmds.extend([
        "CURSOR_UP", "CURSOR_DOWN", "CURSOR_LEFT", "CURSOR_RIGHT",
        "CURSOR_ENTER", "SETUP", "BACK", "INFO_IR", "PAGE_UP", "PAGE_DOWN",
        "CLEAR",
    ])
    items = [
        {"type": "text", "text": "Setup", "command": {"cmd_id": "SETUP"}, "location": {"x": 0, "y": 0}, "size": {"width": 1, "height": 1}},
        {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "CURSOR_UP"}, "location": {"x": 1, "y": 0}},
        {"type": "text", "text": "Info", "command": {"cmd_id": "INFO_IR"}, "location": {"x": 3, "y": 0}, "size": {"width": 1, "height": 1}},
        {"type": "icon", "icon": "uc:left-arrow", "command": {"cmd_id": "CURSOR_LEFT"}, "location": {"x": 0, "y": 1}},
        {"type": "text", "text": "OK", "command": {"cmd_id": "CURSOR_ENTER"}, "location": {"x": 1, "y": 1}, "size": {"width": 1, "height": 1}},
        {"type": "icon", "icon": "uc:right-arrow", "command": {"cmd_id": "CURSOR_RIGHT"}, "location": {"x": 2, "y": 1}},
        {"type": "text", "text": "Clear", "command": {"cmd_id": "CLEAR"}, "location": {"x": 0, "y": 2}, "size": {"width": 1, "height": 1}},
        {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "CURSOR_DOWN"}, "location": {"x": 1, "y": 2}},
        {"type": "text", "text": "Last", "command": {"cmd_id": "BACK"}, "location": {"x": 3, "y": 2}, "size": {"width": 1, "height": 1}},
        {"type": "text", "text": "Page\nUp", "command": {"cmd_id": "PAGE_UP"}, "location": {"x": 0, "y": 3}, "size": {"width": 1, "height": 1}},
        {"type": "text", "text": "Page\nDown", "command": {"cmd_id": "PAGE_DOWN"}, "location": {"x": 3, "y": 3}, "size": {"width": 1, "height": 1}},
    ]
    return {
        "page_id": "navigation", "name": "Navigation",
        "grid": {"width": 4, "height": 4}, "items": items,
    }


def _build_keypad_page(cmds: list[str]) -> dict:
    # Phone-style keypad echoing the RC-MRX 2: 1-9 grid, Preset/0 at the bottom.
    # The remote's Input key (bottom-right) is omitted -- input stays native.
    # Grid is 4 wide (the Remote's fixed column count); digits use columns 0-2.
    cmds.extend([f"DIGIT_{n}" for n in range(10)])
    cmds.append("PRESET")
    items = []
    for i in range(1, 10):
        y, x = divmod(i - 1, 3)
        items.append({
            "type": "text", "text": str(i),
            "command": {"cmd_id": f"DIGIT_{i}"},
            "location": {"x": x, "y": y},
            "size": {"width": 1, "height": 1},
        })
    items.append({"type": "text", "text": "Preset", "command": {"cmd_id": "PRESET"}, "location": {"x": 0, "y": 3}, "size": {"width": 1, "height": 1}})
    items.append({"type": "text", "text": "0", "command": {"cmd_id": "DIGIT_0"}, "location": {"x": 1, "y": 3}, "size": {"width": 1, "height": 1}})
    return {
        "page_id": "keypad", "name": "Keypad",
        "grid": {"width": 4, "height": 4}, "items": items,
    }


class AnthemRemote(RemoteEntity):

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

        is_x20 = device_config.is_x20_series
        simple_commands, user_interface = _build_ui(
            is_x20, zone_config.zone_number
        )

        features = [Features.SEND_CMD]
        attributes = {Attributes.STATE: States.UNAVAILABLE}

        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            simple_commands=simple_commands,
            ui_pages=user_interface["pages"],
            cmd_handler=self._handle_command,
        )

        self.subscribe_to_device(device)

    async def sync_state(self):
        zone_state = self._device.get_zone_state(self._zone_config.zone_number)
        if zone_state.power is None:
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        self.update({
            Attributes.STATE: States.ON if zone_state.power else States.OFF,
        })

    def _get_alm_command(self, zone: int, mode_num: int) -> str:
        if self._device.is_x20_series:
            return f"Z{zone}ALM{mode_num:02d}"
        return f"Z{zone}ALM{mode_num}"

    async def _handle_command(
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
                    return StatusCodes.OK
                success = await self._device._send_command(f"Z{zone}DSCS1")
            elif command == "DOLBY_CENTER_SPREAD_OFF":
                if is_x20:
                    return StatusCodes.OK
                success = await self._device._send_command(f"Z{zone}DSCS0")
            elif command == "INFO":
                if is_x20:
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
                    return StatusCodes.OK
                success = await self._device.set_front_panel_display(0)
            elif command == "DISPLAY_VOLUME_ONLY":
                if is_x20:
                    return StatusCodes.OK
                success = await self._device.set_front_panel_display(1)
            elif command == "HDMI_BYPASS_OFF":
                if is_x20:
                    return StatusCodes.OK
                success = await self._device.set_hdmi_standby_bypass(0)
            elif command == "HDMI_BYPASS_LAST":
                if is_x20:
                    return StatusCodes.OK
                success = await self._device.set_hdmi_standby_bypass(1)
            elif command == "CEC_ON":
                if is_x20:
                    return StatusCodes.OK
                success = await self._device.set_cec_control(True)
            elif command == "CEC_OFF":
                if is_x20:
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
            elif command in _SIM_CODES:
                if zone != 1:
                    # Simulated-IR keys are Main-Zone only per both specs.
                    return StatusCodes.OK
                success = await self._device._send_command(
                    f"Z{zone}SIM{_SIM_CODES[command]}"
                )
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
