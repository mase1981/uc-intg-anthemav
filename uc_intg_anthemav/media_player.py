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
from ucapi_framework import DeviceEvents

from .config import AnthemDeviceConfig, ZoneConfig
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemMediaPlayer(MediaPlayer):
    """Media player entity for Anthem A/V receiver zone."""
    
    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice, zone_config: ZoneConfig):
        """
        Initialize media player entity.
        
        :param device_config: Device configuration
        :param device: Anthem device instance
        :param zone_config: Zone configuration
        """
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config
        
        # Create entity ID
        if zone_config.zone_number == 1:
            entity_id = f"media_player.{device_config.identifier}"
            entity_name = device_config.name
        else:
            entity_id = f"media_player.{device_config.identifier}.zone{zone_config.zone_number}"
            entity_name = f"{device_config.name} {zone_config.name}"
        
        # Define features
        features = [
            Features.ON_OFF,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.SELECT_SOURCE
        ]
        
        # Initial attributes - will be updated after connection
        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
            Attributes.SOURCE_LIST: []  # Empty initially, populated after input discovery
        }
        
        # Simple commands
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
        
        # Register for device events
        device.events.on(DeviceEvents.UPDATE, self._on_device_update)
        
        _LOG.info("[%s] Entity initialized for Zone %d", self.id, zone_config.zone_number)
    
    async def _on_device_update(self, entity_id: str, update_data: dict[str, Any]) -> None:
        """
        Handle device state updates.
        
        Called when device emits UPDATE events with new state data.
        Framework automatically propagates attribute changes.
        """
        if entity_id != self.id:
            return
        
        _LOG.debug("[%s] Device update: %s", self.id, update_data)
        
        # Update entity attributes - framework handles propagation
        for key, value in update_data.items():
            if key == "state":
                # Convert string state to States enum
                if value == "ON":
                    self.attributes[Attributes.STATE] = States.ON
                elif value == "OFF":
                    self.attributes[Attributes.STATE] = States.OFF
                else:
                    self.attributes[Attributes.STATE] = States.UNAVAILABLE
                _LOG.debug("[%s] State updated: %s", self.id, self.attributes[Attributes.STATE])
                
            elif key == "volume":
                self.attributes[Attributes.VOLUME] = value
                _LOG.debug("[%s] Volume updated: %d%%", self.id, value)
                
            elif key == "muted":
                self.attributes[Attributes.MUTED] = value
                _LOG.debug("[%s] Mute updated: %s", self.id, value)
                
            elif key == "source":
                self.attributes[Attributes.SOURCE] = value
                _LOG.debug("[%s] Source updated: %s", self.id, value)
                
            elif key == "source_list":
                # Update source list when device discovers inputs
                self.attributes[Attributes.SOURCE_LIST] = value
                _LOG.info("[%s] Source list updated: %d sources available", self.id, len(value))
    
    async def push_update(self) -> None:
        """
        Query device for current status and update entity.
        
        Called when entity is first subscribed to get initial state.
        """
        _LOG.info("[%s] Querying initial status for Zone %d", self.id, self._zone_config.zone_number)
        
        # Query all status for this zone
        await self._device.query_status(self._zone_config.zone_number)
        
        # Wait for responses to be processed
        await asyncio.sleep(0.3)
    
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
                    # Convert percentage to dB (-90 to 0)
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
                current_mute = self.attributes.get(Attributes.MUTED, False)
                success = await self._device.set_mute(not current_mute, zone)
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
                return StatusCodes.OK  # Return OK for unsupported commands
        
        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR
    
    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number