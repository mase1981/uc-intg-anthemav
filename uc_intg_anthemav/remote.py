"""
Anthem Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.remote import Commands, Features, Options, Remote

from .config import AnthemDeviceConfig, ZoneConfig
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemRemote(Remote):
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

        simple_commands = [
            "DOLBY_SURROUND",
            "DTS_NEURAL_X",
            "ANTHEMLOGIC_CINEMA",
            "ANTHEMLOGIC_MUSIC",
            "STEREO",
            "MULTI_CHANNEL_STEREO",
            "ALL_CHANNEL_STEREO",
            "DIRECT",
            "PLIIX_MOVIE",
            "PLIIX_MUSIC",
            "NEO6_CINEMA",
            "NEO6_MUSIC",
            "DOLBY_DIGITAL",
            "DTS",
            "PCM_STEREO",
            "AUDIO_MODE_UP",
            "AUDIO_MODE_DOWN",
            "BASS_UP",
            "BASS_DOWN",
            "TREBLE_UP",
            "TREBLE_DOWN",
            "BALANCE_LEFT",
            "BALANCE_RIGHT",
            "DOLBY_DRC_NORMAL",
            "DOLBY_DRC_REDUCED",
            "DOLBY_DRC_LATE_NIGHT",
            "DOLBY_CENTER_SPREAD_ON",
            "DOLBY_CENTER_SPREAD_OFF",
            "INFO",
            "ARC_ON",
            "ARC_OFF",
            "BRIGHTNESS_UP",
            "BRIGHTNESS_DOWN",
            "DISPLAY_ALL",
            "DISPLAY_VOLUME_ONLY",
            "HDMI_BYPASS_OFF",
            "HDMI_BYPASS_LAST",
            "CEC_ON",
            "CEC_OFF",
            "LEVEL_SUBWOOFER_UP",
            "LEVEL_SUBWOOFER_DOWN",
            "LEVEL_FRONTS_UP",
            "LEVEL_FRONTS_DOWN",
            "LEVEL_CENTER_UP",
            "LEVEL_CENTER_DOWN",
            "LEVEL_SURROUNDS_UP",
            "LEVEL_SURROUNDS_DOWN",
            "LEVEL_BACKS_UP",
            "LEVEL_BACKS_DOWN",
            "LEVEL_HEIGHTS_UP",
            "LEVEL_HEIGHTS_DOWN",
        ]

        user_interface = {
            "pages": [
                {
                    "page_id": "audio_modes",
                    "name": "Audio Modes",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        {
                            "type": "text",
                            "text": "Dolby\nSurround",
                            "command": {"cmd_id": "DOLBY_SURROUND"},
                            "location": {"x": 0, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "DTS\nNeural:X",
                            "command": {"cmd_id": "DTS_NEURAL_X"},
                            "location": {"x": 2, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "AnthemLogic\nCinema",
                            "command": {"cmd_id": "ANTHEMLOGIC_CINEMA"},
                            "location": {"x": 0, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "AnthemLogic\nMusic",
                            "command": {"cmd_id": "ANTHEMLOGIC_MUSIC"},
                            "location": {"x": 2, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Stereo",
                            "command": {"cmd_id": "STEREO"},
                            "location": {"x": 0, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Multi-Ch\nStereo",
                            "command": {"cmd_id": "MULTI_CHANNEL_STEREO"},
                            "location": {"x": 2, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Direct",
                            "command": {"cmd_id": "DIRECT"},
                            "location": {"x": 0, "y": 3},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "All-Ch\nStereo",
                            "command": {"cmd_id": "ALL_CHANNEL_STEREO"},
                            "location": {"x": 1, "y": 3},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "AUDIO_MODE_UP"},
                            "location": {"x": 2, "y": 3},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "AUDIO_MODE_DOWN"},
                            "location": {"x": 3, "y": 3},
                        },
                        {
                            "type": "text",
                            "text": "PLIIx\nMovie",
                            "command": {"cmd_id": "PLIIX_MOVIE"},
                            "location": {"x": 0, "y": 4},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "PLIIx\nMusic",
                            "command": {"cmd_id": "PLIIX_MUSIC"},
                            "location": {"x": 1, "y": 4},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Neo:6\nCinema",
                            "command": {"cmd_id": "NEO6_CINEMA"},
                            "location": {"x": 2, "y": 4},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Neo:6\nMusic",
                            "command": {"cmd_id": "NEO6_MUSIC"},
                            "location": {"x": 3, "y": 4},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Dolby\nDigital",
                            "command": {"cmd_id": "DOLBY_DIGITAL"},
                            "location": {"x": 0, "y": 5},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "DTS",
                            "command": {"cmd_id": "DTS"},
                            "location": {"x": 1, "y": 5},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "PCM\nStereo",
                            "command": {"cmd_id": "PCM_STEREO"},
                            "location": {"x": 2, "y": 5},
                            "size": {"width": 1, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Info",
                            "command": {"cmd_id": "INFO"},
                            "location": {"x": 3, "y": 5},
                            "size": {"width": 1, "height": 1},
                        },
                    ],
                },
                {
                    "page_id": "tone_control",
                    "name": "Tone Control",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        {
                            "type": "text",
                            "text": "Bass",
                            "location": {"x": 0, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "BASS_UP"},
                            "location": {"x": 2, "y": 0},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "BASS_DOWN"},
                            "location": {"x": 3, "y": 0},
                        },
                        {
                            "type": "text",
                            "text": "Treble",
                            "location": {"x": 0, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "TREBLE_UP"},
                            "location": {"x": 2, "y": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "TREBLE_DOWN"},
                            "location": {"x": 3, "y": 1},
                        },
                        {
                            "type": "text",
                            "text": "Balance",
                            "location": {"x": 0, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:left-arrow",
                            "command": {"cmd_id": "BALANCE_LEFT"},
                            "location": {"x": 2, "y": 2},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:right-arrow",
                            "command": {"cmd_id": "BALANCE_RIGHT"},
                            "location": {"x": 3, "y": 2},
                        },
                    ],
                },
                {
                    "page_id": "dolby_settings",
                    "name": "Dolby Settings",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        {
                            "type": "text",
                            "text": "DRC\nNormal",
                            "command": {"cmd_id": "DOLBY_DRC_NORMAL"},
                            "location": {"x": 0, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "DRC\nReduced",
                            "command": {"cmd_id": "DOLBY_DRC_REDUCED"},
                            "location": {"x": 2, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "DRC\nLate Night",
                            "command": {"cmd_id": "DOLBY_DRC_LATE_NIGHT"},
                            "location": {"x": 0, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Center\nSpread ON",
                            "command": {"cmd_id": "DOLBY_CENTER_SPREAD_ON"},
                            "location": {"x": 0, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Center\nSpread OFF",
                            "command": {"cmd_id": "DOLBY_CENTER_SPREAD_OFF"},
                            "location": {"x": 2, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                    ],
                },
                {
                    "page_id": "system_settings",
                    "name": "System Settings",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        {
                            "type": "text",
                            "text": "Display\nBrightness",
                            "location": {"x": 0, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "BRIGHTNESS_UP"},
                            "location": {"x": 2, "y": 0},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "BRIGHTNESS_DOWN"},
                            "location": {"x": 3, "y": 0},
                        },
                        {
                            "type": "text",
                            "text": "Display\nAll Info",
                            "command": {"cmd_id": "DISPLAY_ALL"},
                            "location": {"x": 0, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "Display\nVol Only",
                            "command": {"cmd_id": "DISPLAY_VOLUME_ONLY"},
                            "location": {"x": 2, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "HDMI\nBypass OFF",
                            "command": {"cmd_id": "HDMI_BYPASS_OFF"},
                            "location": {"x": 0, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "HDMI\nBypass ON",
                            "command": {"cmd_id": "HDMI_BYPASS_LAST"},
                            "location": {"x": 2, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "CEC\nON",
                            "command": {"cmd_id": "CEC_ON"},
                            "location": {"x": 0, "y": 3},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "CEC\nOFF",
                            "command": {"cmd_id": "CEC_OFF"},
                            "location": {"x": 2, "y": 3},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "ARC\nON",
                            "command": {"cmd_id": "ARC_ON"},
                            "location": {"x": 0, "y": 4},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "text",
                            "text": "ARC\nOFF",
                            "command": {"cmd_id": "ARC_OFF"},
                            "location": {"x": 2, "y": 4},
                            "size": {"width": 2, "height": 1},
                        },
                    ],
                },
                {
                    "page_id": "speaker_levels",
                    "name": "Speaker Levels",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        {
                            "type": "text",
                            "text": "Subwoofer",
                            "location": {"x": 0, "y": 0},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_SUBWOOFER_UP"},
                            "location": {"x": 2, "y": 0},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_SUBWOOFER_DOWN"},
                            "location": {"x": 3, "y": 0},
                        },
                        {
                            "type": "text",
                            "text": "Fronts",
                            "location": {"x": 0, "y": 1},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_FRONTS_UP"},
                            "location": {"x": 2, "y": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_FRONTS_DOWN"},
                            "location": {"x": 3, "y": 1},
                        },
                        {
                            "type": "text",
                            "text": "Center",
                            "location": {"x": 0, "y": 2},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_CENTER_UP"},
                            "location": {"x": 2, "y": 2},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_CENTER_DOWN"},
                            "location": {"x": 3, "y": 2},
                        },
                        {
                            "type": "text",
                            "text": "Surrounds",
                            "location": {"x": 0, "y": 3},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_SURROUNDS_UP"},
                            "location": {"x": 2, "y": 3},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_SURROUNDS_DOWN"},
                            "location": {"x": 3, "y": 3},
                        },
                        {
                            "type": "text",
                            "text": "Backs",
                            "location": {"x": 0, "y": 4},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_BACKS_UP"},
                            "location": {"x": 2, "y": 4},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_BACKS_DOWN"},
                            "location": {"x": 3, "y": 4},
                        },
                        {
                            "type": "text",
                            "text": "Heights",
                            "location": {"x": 0, "y": 5},
                            "size": {"width": 2, "height": 1},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:up-arrow",
                            "command": {"cmd_id": "LEVEL_HEIGHTS_UP"},
                            "location": {"x": 2, "y": 5},
                        },
                        {
                            "type": "icon",
                            "icon": "uc:down-arrow",
                            "command": {"cmd_id": "LEVEL_HEIGHTS_DOWN"},
                            "location": {"x": 3, "y": 5},
                        },
                    ],
                },
            ]
        }

        self.options = {
            Options.SIMPLE_COMMANDS: simple_commands,
            "user_interface": user_interface,
        }

        _LOG.info(
            "[%s] Remote entity initialized with %d commands across 5 UI pages",
            entity_id,
            len(simple_commands),
        )

        device.events.on("UPDATE", self._on_device_update)

    async def _on_device_update(
        self, entity_id: str, update_data: dict[str, Any]
    ) -> None:
        pass

    async def handle_command(
        self, entity: Remote, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            zone = self._zone_config.zone_number

            if cmd_id != Commands.SEND_CMD:
                _LOG.warning("[%s] Unsupported command type: %s", self.id, cmd_id)
                return StatusCodes.NOT_FOUND

            if not params or "command" not in params:
                _LOG.error("[%s] Missing command parameter", self.id)
                return StatusCodes.BAD_REQUEST

            command = params["command"]
            success = False

            if command == "DOLBY_SURROUND":
                success = await self._device._send_command(f"Z{zone}ALM3")
            elif command == "DTS_NEURAL_X":
                success = await self._device._send_command(f"Z{zone}ALM4")
            elif command == "ANTHEMLOGIC_CINEMA":
                success = await self._device._send_command(f"Z{zone}ALM1")
            elif command == "ANTHEMLOGIC_MUSIC":
                success = await self._device._send_command(f"Z{zone}ALM2")
            elif command == "STEREO":
                success = await self._device._send_command(f"Z{zone}ALM5")
            elif command == "MULTI_CHANNEL_STEREO":
                success = await self._device._send_command(f"Z{zone}ALM6")
            elif command == "ALL_CHANNEL_STEREO":
                success = await self._device._send_command(f"Z{zone}ALM7")
            elif command == "PLIIX_MOVIE":
                success = await self._device._send_command(f"Z{zone}ALM8")
            elif command == "PLIIX_MUSIC":
                success = await self._device._send_command(f"Z{zone}ALM9")
            elif command == "NEO6_CINEMA":
                success = await self._device._send_command(f"Z{zone}ALM10")
            elif command == "NEO6_MUSIC":
                success = await self._device._send_command(f"Z{zone}ALM11")
            elif command == "DOLBY_DIGITAL":
                success = await self._device._send_command(f"Z{zone}ALM12")
            elif command == "DTS":
                success = await self._device._send_command(f"Z{zone}ALM13")
            elif command == "PCM_STEREO":
                success = await self._device._send_command(f"Z{zone}ALM14")
            elif command == "DIRECT":
                success = await self._device._send_command(f"Z{zone}ALM15")
            elif command == "AUDIO_MODE_UP":
                success = await self._device._send_command(f"Z{zone}AUP")
            elif command == "AUDIO_MODE_DOWN":
                success = await self._device._send_command(f"Z{zone}ADN")
            elif command == "BASS_UP":
                success = await self._device._send_command(f"Z{zone}TUP0")
            elif command == "BASS_DOWN":
                success = await self._device._send_command(f"Z{zone}TDN0")
            elif command == "TREBLE_UP":
                success = await self._device._send_command(f"Z{zone}TUP1")
            elif command == "TREBLE_DOWN":
                success = await self._device._send_command(f"Z{zone}TDN1")
            elif command == "BALANCE_LEFT":
                success = await self._device._send_command(f"Z{zone}BLT")
            elif command == "BALANCE_RIGHT":
                success = await self._device._send_command(f"Z{zone}BRT")
            elif command == "DOLBY_DRC_NORMAL":
                success = await self._device._send_command(f"Z{zone}DYN0")
            elif command == "DOLBY_DRC_REDUCED":
                success = await self._device._send_command(f"Z{zone}DYN1")
            elif command == "DOLBY_DRC_LATE_NIGHT":
                success = await self._device._send_command(f"Z{zone}DYN2")
            elif command == "DOLBY_CENTER_SPREAD_ON":
                success = await self._device._send_command(f"Z{zone}DSCS1")
            elif command == "DOLBY_CENTER_SPREAD_OFF":
                success = await self._device._send_command(f"Z{zone}DSCS0")
            elif command == "INFO":
                success = await self._device.set_osd_info(1)
            elif command == "ARC_ON":
                input_num = self._device.get_zone_state(zone).get("input", 1)
                success = await self._device.set_arc(True, input_num)
            elif command == "ARC_OFF":
                input_num = self._device.get_zone_state(zone).get("input", 1)
                success = await self._device.set_arc(False, input_num)
            elif command == "BRIGHTNESS_UP":
                success = await self._device._send_command("GCFPB?")
                await asyncio.sleep(0.1)
                success = await self._device.set_front_panel_brightness(50)
            elif command == "BRIGHTNESS_DOWN":
                success = await self._device._send_command("GCFPB?")
                await asyncio.sleep(0.1)
                success = await self._device.set_front_panel_brightness(20)
            elif command == "DISPLAY_ALL":
                success = await self._device.set_front_panel_display(0)
            elif command == "DISPLAY_VOLUME_ONLY":
                success = await self._device.set_front_panel_display(1)
            elif command == "HDMI_BYPASS_OFF":
                success = await self._device.set_hdmi_standby_bypass(0)
            elif command == "HDMI_BYPASS_LAST":
                success = await self._device.set_hdmi_standby_bypass(1)
            elif command == "CEC_ON":
                success = await self._device.set_cec_control(True)
            elif command == "CEC_OFF":
                success = await self._device.set_cec_control(False)
            elif command == "LEVEL_SUBWOOFER_UP":
                success = await self._device.speaker_level_up(1, zone)
            elif command == "LEVEL_SUBWOOFER_DOWN":
                success = await self._device.speaker_level_down(1, zone)
            elif command == "LEVEL_FRONTS_UP":
                success = await self._device.speaker_level_up(5, zone)
            elif command == "LEVEL_FRONTS_DOWN":
                success = await self._device.speaker_level_down(5, zone)
            elif command == "LEVEL_CENTER_UP":
                success = await self._device.speaker_level_up(7, zone)
            elif command == "LEVEL_CENTER_DOWN":
                success = await self._device.speaker_level_down(7, zone)
            elif command == "LEVEL_SURROUNDS_UP":
                success = await self._device.speaker_level_up(8, zone)
            elif command == "LEVEL_SURROUNDS_DOWN":
                success = await self._device.speaker_level_down(8, zone)
            elif command == "LEVEL_BACKS_UP":
                success = await self._device.speaker_level_up(9, zone)
            elif command == "LEVEL_BACKS_DOWN":
                success = await self._device.speaker_level_down(9, zone)
            elif command == "LEVEL_HEIGHTS_UP":
                success = await self._device.speaker_level_up(10, zone)
            elif command == "LEVEL_HEIGHTS_DOWN":
                success = await self._device.speaker_level_down(10, zone)
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