"""
Anthem AV device implementation.

:copyright: (c) 2025 by User.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ucapi_framework import PollingDevice, DeviceEvents
from intg_anthem.config import AnthemDeviceConfig
from intg_anthem.driver import AnthemDriver, DriverEvents

_LOG = logging.getLogger(__name__)


class AnthemDevice(PollingDevice):
    """Anthem AV device."""

    def __init__(self, device_config: AnthemDeviceConfig, loop=None, config_manager=None):
        """Initialize device."""
        super().__init__(
            device_config,
            loop,
            poll_interval=10,
            config_manager=config_manager
        )
        self._driver: Optional[AnthemDriver] = None
        
        # Device State
        self._power = False
        self._volume = 0
        self._muted = False
        self._source_id = 0
        
        # Dynamic Source List: Map ID (int) -> Name (str)
        # This replaces the hardcoded list from the previous version
        self._sources: Dict[int, str] = {}
        
    @property
    def source_list(self) -> List[str]:
        """Return sorted list of discovered source names."""
        sorted_ids = sorted(self._sources.keys())
        return [self._sources[uid] for uid in sorted_ids]
        
    @property
    def current_source(self) -> Optional[str]:
        """Return name of current source."""
        return self._sources.get(self._source_id)

    @property
    def power(self) -> bool:
        return self._power

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    async def establish_connection(self) -> None:
        """
        Connect to device and start discovery.
        Required by PollingDevice.
        """
        self._driver = AnthemDriver(self.device_config.host, self.device_config.port)
        
        # Hook up driver events
        self._driver.on(DriverEvents.MESSAGE, self._on_message)
        self._driver.on(DriverEvents.CONNECTED, self._on_connected)
        self._driver.on_input_discovered = self._on_input_discovered
        
        await self._driver.connect()
        
        # TRIGGER DISCOVERY: Ask receiver for all input names
        await self._driver.send_command("ISN")
        
        # Initial Poll
        await self.poll_device()

    def _on_connected(self, *args):
        _LOG.info("Anthem connected. Discovery started.")

    def _on_input_discovered(self, input_id: int, name: str):
        """Callback when driver finds a new input."""
        name = name.strip()
        if not name:
            return
            
        # Only update and emit if it's actually new or changed
        if self._sources.get(input_id) != name:
            _LOG.info("Discovered Input %d: %s", input_id, name)
            self._sources[input_id] = name
            # Important: Emit update so UI can refresh the source list immediately
            self._emit_update()

    async def poll_device(self) -> None:
        """
        Poll device state.
        Required by PollingDevice.
        """
        if not self._driver or not self._driver.is_connected:
            return
            
        # Z1 Prefix is standard for Main Zone
        await self._driver.send_command("Z1POW?")
        await self._driver.send_command("Z1VOL?")
        await self._driver.send_command("Z1MUT?")
        await self._driver.send_command("Z1INP?")

    def _on_message(self, message: str):
        """Parse state messages (Power, Vol, etc)."""
        # Anthem Protocol: Z1POW1 = Zone 1 Power On
        if message.startswith("Z1POW"):
            self._power = message.endswith("1")
            
        # Z1VOL-35 (dB) or Z1VOL50 (%)
        elif message.startswith("Z1VOL"):
            try:
                val = message[5:]
                if "-" in val:
                    # Map dB (-90 to 0) to % roughly
                    db = int(val)
                    # Simple linear map: -90db=0%, 0db=100%
                    self._volume = max(0, min(100, int((db + 90) * (100/90))))
                else:
                    self._volume = int(val)
            except ValueError:
                pass
                
        # Z1MUT1 = Muted
        elif message.startswith("Z1MUT"):
            self._muted = message.endswith("1")
            
        # Z1INP01 = Input 1
        elif message.startswith("Z1INP"):
            try:
                self._source_id = int(message[5:])
            except ValueError:
                pass

        self._emit_update()

    def _emit_update(self):
        """Emit state update to Framework."""
        self.events.emit(
            DeviceEvents.UPDATE,
            self.device_config.identifier,
            {
                "state": "ON" if self._power else "OFF",
                "volume": self._volume,
                "muted": self._muted,
                "source": self.current_source,
                # Pass the dynamic list to the entity
                "source_list": self.source_list  
            }
        )

    # --- Command Helpers ---

    async def set_power(self, state: bool):
        cmd = "Z1POW1" if state else "Z1POW0"
        await self._driver.send_command(cmd)

    async def set_volume(self, volume: int):
        # Reverse map % to dB (-90 to 0)
        db = int((volume * 0.9) - 90)
        await self._driver.send_command(f"Z1VOL{db}")

    async def set_mute(self, mute: bool):
        cmd = "Z1MUT1" if mute else "Z1MUT0"
        await self._driver.send_command(cmd)
        
    async def select_source(self, source_name: str):
        # Find ID matching the name
        for uid, name in self._sources.items():
            if name == source_name:
                cmd = f"Z1INP{uid:02d}"
                await self._driver.send_command(cmd)
                return