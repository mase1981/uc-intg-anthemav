"""
Anthem AV Remote implementation.

:copyright: (c) 2025 by User.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any, Dict

from ucapi import Remote, StatusCodes
from ucapi_framework import Entity

from intg_anthem.config import AnthemDeviceConfig
from intg_anthem.device import AnthemDevice

_LOG = logging.getLogger(__name__)

# Efficient mapping of Button ID -> Anthem Command
# This replaces hundreds of lines of if/elif statements
COMMAND_MAP: Dict[str, str] = {
    # Power
    Remote.Buttons.POWER_ON: "Z1POW1",
    Remote.Buttons.POWER_OFF: "Z1POW0",
    
    # Volume & Mute
    Remote.Buttons.VOLUME_UP: "Z1VUP",
    Remote.Buttons.VOLUME_DOWN: "Z1VDN",
    # Mute toggle is handled by logic, but explicit commands exist:
    Remote.Buttons.MUTE: "Z1MUT1",
    Remote.Buttons.UNMUTE: "Z1MUT0",

    # Navigation
    Remote.Buttons.CURSOR_UP: "Z1CUP",
    Remote.Buttons.CURSOR_DOWN: "Z1CDN",
    Remote.Buttons.CURSOR_LEFT: "Z1CLT",
    Remote.Buttons.CURSOR_RIGHT: "Z1CRT",
    Remote.Buttons.CURSOR_ENTER: "Z1ENT",
    Remote.Buttons.MENU: "Z1MEN",
    Remote.Buttons.BACK: "Z1RET",
    Remote.Buttons.INFO: "Z1INF",
    Remote.Buttons.HOME: "Z1MEN",  # Map Home to Setup Menu

    # Transport (Pass-through to CEC devices usually)
    Remote.Buttons.PLAY: "Z1PLY",
    Remote.Buttons.PAUSE: "Z1PAU",
    Remote.Buttons.STOP: "Z1STP",
    Remote.Buttons.NEXT: "Z1SKF",
    Remote.Buttons.PREVIOUS: "Z1SKR",
    Remote.Buttons.REWIND: "Z1RW",  # Verify model support
    Remote.Buttons.FAST_FORWARD: "Z1FF",
    
    # Audio Modes (Common on Anthem Remotes)
    "MODE_STEREO": "Z1MOSTEREO",
    "MODE_DTS": "Z1MODTS",
    "MODE_DOLBY": "Z1MODOLBY",
    "MODE_ANTHEM_LOGIC": "Z1MOANTHEM",
    "MODE_PRESET_1": "Z1P1", # Profile/Preset 1
    "MODE_PRESET_2": "Z1P2",
    
    # Tone Control
    "AUDIO_BASS_UP": "Z1BUP",
    "AUDIO_BASS_DOWN": "Z1BDN",
    "AUDIO_TREBLE_UP": "Z1TUP",
    "AUDIO_TREBLE_DOWN": "Z1TDN",
}


class AnthemRemote(Remote, Entity):
    """Anthem Physical Remote entity."""

    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice):
        """Initialize remote."""
        self._device = device
        
        # We allow the Framework to register the standard buttons based on Features.
        # Custom buttons (like Audio Modes) would be added via `self.add_button` 
        # if this were a UI generator, but for a Remote entity mapping, 
        # we focus on the command handler.

        super().__init__(
            identifier=f"{device_config.identifier}_remote",
            name=f"{device_config.name} Remote",
            cmd_handler=self.handle_command
        )

    async def handle_command(
        self, entity: Remote, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """
        Handle remote button presses.
        Uses dictionary lookup for O(1) efficiency instead of O(N) if/else blocks.
        """
        if not self._device._driver or not self._device._driver.is_connected:
            return StatusCodes.SERVER_ERROR

        # 1. Check Dictionary Mapping (Fast path)
        cmd = COMMAND_MAP.get(cmd_id)
        
        # 2. Handle Logic-based commands
        if not cmd:
            if cmd_id == Remote.Buttons.POWER_TOGGLE:
                cmd = "Z1POW0" if self._device.power else "Z1POW1"
                
            elif cmd_id == Remote.Buttons.MUTE_TOGGLE:
                cmd = "Z1MUT0" if self._device.muted else "Z1MUT1"
            
            # Dynamic Input Selection via Remote Button
            # (e.g., if mapped to a physical "Input 1" key)
            elif cmd_id.startswith("INPUT_"):
                # If the remote sends specific INPUT_HDMI1 commands
                # We can try to map them if we know the ID.
                # Since inputs are dynamic, we usually rely on `SELECT_SOURCE`
                pass

        # 3. Execution
        if cmd:
            await self._device._driver.send_command(cmd)
            return StatusCodes.OK
        
        # 4. Fallback or Not Implemented
        _LOG.debug("Unmapped remote command: %s", cmd_id)
        return StatusCodes.NOT_IMPLEMENTED