"""
Anthem Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

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
            entity_name = f"{device_config.name} Audio Controls"
        else:
            entity_id = (
                f"remote.{device_config.identifier}.zone{zone_config.zone_number}"
            )
            entity_name = (
                f"{device_config.name} Zone {zone_config.zone_number} Audio Controls"
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
            "DIRECT",
            "PLIIX_MOVIE",
            "PLIIX_MUSIC",
            "NEO6_CINEMA",
            "NEO6_MUSIC",
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
                            "size": {"width": 2, "height": 1},
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
                            "text": "Info",
                            "command": {"cmd_id": "INFO"},
                            "location": {"x": 0, "y": 4},
                            "size": {"width": 2, "height": 1},
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
            ]
        }

        self.options = {
            Options.SIMPLE_COMMANDS: simple_commands,
            "user_interface": user_interface,
        }

        _LOG.info(
            "[%s] Remote entity initialized with %d commands and 3 UI pages",
            entity_id,
            len(simple_commands),
        )
        
        _LOG.error(
            "[%s] DIAGNOSTIC: Remote entity created with device instance ID=%s",
            entity_id,
            id(device)
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
        
        _LOG.error(
            "[%s] DIAGNOSTIC: handle_command() called - Device instance ID=%s",
            self.id,
            id(self._device)
        )
        _LOG.error(
            "[%s] DIAGNOSTIC: Device.is_connected=%s, Device._writer is None? %s",
            self.id,
            self._device.is_connected,
            self._device._writer is None
        )

        try:
            zone = self._zone_config.zone_number

            if cmd_id != Commands.SEND_CMD:
                _LOG.warning("[%s] Unsupported command type: %s", self.id, cmd_id)
                return StatusCodes.NOT_FOUND

            if not params or "command" not in params:
                _LOG.error("[%s] Missing command parameter", self.id)
                return StatusCodes.BAD_REQUEST

            command = params["command"]
            _LOG.error("[%s] DIAGNOSTIC: About to execute command: %s", self.id, command)

            success = False
            
            if command == "DOLBY_SURROUND":
                _LOG.error("[%s] DIAGNOSTIC: Executing DOLBY_SURROUND -> Z%dALM3", self.id, zone)
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
            
            else:
                _LOG.warning("[%s] Unknown audio command: %s", self.id, command)
                return StatusCodes.NOT_FOUND

            _LOG.error("[%s] DIAGNOSTIC: Command execution result: success=%s", self.id, success)
            
            if not success:
                _LOG.error("[%s] CRITICAL ERROR: Command failed to send to device!", self.id)
                return StatusCodes.SERVER_ERROR
            
            return StatusCodes.OK

        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    @property
    def zone_number(self) -> int:
        return self._zone_config.zone_number