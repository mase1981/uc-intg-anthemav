"""
Anthem Media Player entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.media_player import Attributes, Commands, DeviceClasses, Features, MediaPlayer, States, Options

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemMediaPlayer(MediaPlayer):
    """Media player entity for Anthem A/V receiver zone."""
    
    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice, zone_config: ZoneConfig):
        """Initialize media player entity."""
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
            Features.SELECT_SOURCE
        ]
        
        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: []
        }
        
        options = {
            Options.SIMPLE_COMMANDS: [
                Commands.ON,
                Commands.OFF,
                Commands.VOLUME_UP,
                Commands.VOLUME_DOWN,
                Commands.MUTE_TOGGLE
            ]
        }
        
        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            device_class=DeviceClasses.RECEIVER,
            cmd_handler=self.handle_command,
            options=options
        )
        
        _LOG.info("[%s] Entity initialized for Zone %d", self.id, zone_config.zone_number)
    
    async def handle_command(
        self,
        entity: MediaPlayer,
        cmd_id: str,
        params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle media player commands."""
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
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            elif cmd_id == Commands.MUTE:
                success = await self._device.set_mute(True, zone)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
            
            elif cmd_id == Commands.UNMUTE:
                success = await self._device.set_mute(False, zone)
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
        """Get zone number."""
        return self._zone_config.zone_number