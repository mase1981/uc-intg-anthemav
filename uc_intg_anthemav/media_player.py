"""
Anthem Media Player Entity.

:copyright: (c) 2025 by User.
:license: MPL-2.0, see LICENSE for more details.
"""

from typing import Any, List

from ucapi import MediaPlayer, StatusCodes, media_player
from ucapi_framework import Entity

from intg_anthem.config import AnthemDeviceConfig
from intg_anthem.device import AnthemDevice


class AnthemMediaPlayer(MediaPlayer, Entity):
    """Anthem Media Player entity."""

    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice):
        """Initialize entity."""
        self._device = device
        
        # Initial attributes
        attributes = {
            media_player.Attributes.STATE: media_player.States.OFF,
            media_player.Attributes.VOLUME: 0,
            media_player.Attributes.MUTED: False,
            # Start with empty list, populate later via update_state
            media_player.Attributes.SOURCE_LIST: [], 
        }

        super().__init__(
            identifier=device_config.identifier,
            name={"en": device_config.name},
            features=[
                media_player.Features.ON_OFF,
                media_player.Features.VOLUME,
                media_player.Features.MUTE,
                media_player.Features.SELECT_SOURCE
            ],
            attributes=attributes,
            device_class=media_player.DeviceClasses.RECEIVER,
            cmd_handler=self.handle_command
        )

    def update_state(self, state_data: dict[str, Any]) -> None:
        """
        Update entity state from device events.
        Overrides Entity.update_state to handle dynamic source lists.
        """
        # 1. Update Standard Attributes
        if state_data.get("state") == "ON":
            self.attributes[media_player.Attributes.STATE] = media_player.States.ON
        else:
            self.attributes[media_player.Attributes.STATE] = media_player.States.OFF
            
        self.attributes[media_player.Attributes.VOLUME] = state_data.get("volume", 0)
        self.attributes[media_player.Attributes.MUTED] = state_data.get("muted", False)
        
        # 2. Update Dynamic Source List
        # This is the key fix: pulling the list from device.py into the UI entity
        if "source_list" in state_data:
            self.attributes[media_player.Attributes.SOURCE_LIST] = state_data["source_list"]
            
        # 3. Update Current Source
        current_source = state_data.get("source")
        if current_source:
            self.attributes[media_player.Attributes.SOURCE] = current_source
            
        # 4. Notify Framework (updates WebSocket/UI)
        super().update_state(state_data)

    async def handle_command(
        self, entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle incoming UI commands."""
        try:
            if cmd_id == media_player.Commands.ON:
                await self._device.set_power(True)
                
            elif cmd_id == media_player.Commands.OFF:
                await self._device.set_power(False)
                
            elif cmd_id == media_player.Commands.VOLUME:
                vol = params.get("volume", 0)
                await self._device.set_volume(vol)
                
            elif cmd_id == media_player.Commands.MUTE_TOGGLE:
                await self._device.set_mute(not self._device.muted)
                
            elif cmd_id == media_player.Commands.SELECT_SOURCE:
                src = params.get("source")
                if src:
                    await self._device.select_source(src)
                else:
                    return StatusCodes.BAD_REQUEST
            else:
                return StatusCodes.NOT_IMPLEMENTED
                
            return StatusCodes.OK
            
        except Exception:
            return StatusCodes.SERVER_ERROR