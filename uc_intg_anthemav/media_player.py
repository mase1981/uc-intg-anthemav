"""
Anthem Media Player entity implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
<<<<<<< HEAD
from ucapi.media_player import Attributes, Commands, DeviceClasses, Features, MediaPlayer, States, Options
=======
from ucapi.media_player import (
    Attributes,
    Commands,
    DeviceClasses,
    Features,
    MediaPlayer,
    States,
    Options,
)
from ucapi_framework import DeviceEvents
>>>>>>> main

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemMediaPlayer(MediaPlayer):
    """Media player entity for Anthem A/V receiver zone."""
<<<<<<< HEAD
    
    def __init__(self, device_config: AnthemDeviceConfig, device: AnthemDevice, zone_config: ZoneConfig):
        """Initialize media player entity."""
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config
        
        # Create entity ID
=======

    def __init__(
        self,
        entity_id: str,
        device: AnthemDevice,
        device_config: AnthemDeviceConfig,
        zone_config: ZoneConfig,
    ):
        self._device = device
        self._device_config = device_config
        self._zone_config = zone_config

>>>>>>> main
        if zone_config.zone_number == 1:
            entity_id = f"media_player.{device_config.identifier}"
            entity_name = device_config.name
        else:
            entity_id = f"media_player.{device_config.identifier}.zone{zone_config.zone_number}"
            entity_name = f"{device_config.name} {zone_config.name}"
<<<<<<< HEAD
        
        # Define features
=======

>>>>>>> main
        features = [
            Features.ON_OFF,
            Features.VOLUME,
            Features.VOLUME_UP_DOWN,
            Features.MUTE_TOGGLE,
            Features.MUTE,
            Features.UNMUTE,
            Features.SELECT_SOURCE,
        ]
<<<<<<< HEAD
        
        # Initial attributes
        # CRITICAL: SOURCE_LIST must be empty initially!
        # It gets populated after input discovery via device events
=======

        source_list = [
            "HDMI 1",
            "HDMI 2",
            "HDMI 3",
            "HDMI 4",
            "HDMI 5",
            "HDMI 6",
            "HDMI 7",
            "HDMI 8",
            "Analog 1",
            "Analog 2",
            "Digital 1",
            "Digital 2",
            "USB",
            "Network",
            "ARC",
        ]

>>>>>>> main
        attributes = {
            Attributes.STATE: States.UNAVAILABLE,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE: "",
<<<<<<< HEAD
            Attributes.SOURCE_LIST: []  # Empty! Gets populated after discovery
        }
        
        # Simple commands
=======
            Attributes.SOURCE_LIST: source_list,
        }

>>>>>>> main
        options = {
            Options.SIMPLE_COMMANDS: [
                Commands.ON,
                Commands.OFF,
                Commands.VOLUME_UP,
                Commands.VOLUME_DOWN,
                Commands.MUTE_TOGGLE,
            ]
        }

        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            device_class=DeviceClasses.RECEIVER,
            cmd_handler=self.handle_command,
            options=options,
        )
<<<<<<< HEAD
        
        _LOG.info("[%s] Entity initialized for Zone %d", self.id, zone_config.zone_number)
    
    async def handle_command(
        self,
        entity: MediaPlayer,
        cmd_id: str,
        params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle media player commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")
        
=======

    # Event handlers are handled by the driver. I moved yours there and deleted the ones that the framework was generically handling
    # Driver also registers them so no need to do that either.
    # You are updating state a bit differently than me. Instead of gathering the data in the event handler, you
    # could gather it in the device and then send it all in update_data and the default implementation would update it.
    # But instead of update_data["state"] you need to use the enum update_data[MediaAttr.STATE]

    # If you do want to leave it here, you need to override the driver method setup_device_event_handlers and
    # and just pass as you don't want to register the default handlers.

    def _db_to_percentage(self, db_value: int) -> float:
        """Convert dB value to percentage (0-100)."""
        db_range = 90
        percentage = ((db_value + 90) / db_range) * 100
        return max(0.0, min(100.0, percentage))

    def _percentage_to_db(self, percentage: float) -> int:
        """Convert percentage to dB value (-90 to 0)."""
        db_range = 90
        db_value = int((percentage * db_range / 100) - 90)
        return max(-90, min(0, db_value))

    async def handle_command(
        self, entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle entity commands."""
        _LOG.info(f"Command {cmd_id} for {self.id}")

>>>>>>> main
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
                return StatusCodes.OK
<<<<<<< HEAD
        
        except Exception as err:
            _LOG.error("[%s] Error executing command %s: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR
    
=======

        except Exception as e:
            _LOG.error(f"Error executing command {cmd_id}: {e}")
            return StatusCodes.SERVER_ERROR

    async def push_update(self) -> None:
        """Query device for current state."""
        await self._device.query_all_status(self._zone_config.zone_number)

>>>>>>> main
    @property
    def zone_number(self) -> int:
        """Get zone number."""
        return self._zone_config.zone_number
