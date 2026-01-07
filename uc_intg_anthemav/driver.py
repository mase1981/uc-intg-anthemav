"""
Anthem AV driver implementation.

:copyright: (c) 2025 by User.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Callable, Optional

from ucapi_framework import BaseDriver, DriverEvents

_LOG = logging.getLogger(__name__)


class AnthemDriver(BaseDriver):
    """Driver for Anthem AV receivers."""

    def __init__(self, host: str, port: int = 14999):
        """Initialize Anthem driver."""
        super().__init__()
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        
        # Callbacks for dynamic discovery
        self.on_input_discovered: Optional[Callable[[int, str], None]] = None

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._connected

    async def connect(self) -> None:
        """Connect to Anthem receiver."""
        try:
            _LOG.info("Connecting to Anthem at %s:%s", self.host, self.port)
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
            self.emit(DriverEvents.CONNECTED)
            
            # Start background read loop to catch ISN messages
            asyncio.create_task(self._read_loop())
            
        except Exception as err:
            _LOG.error("Connection failed: %s", err)
            self.emit(DriverEvents.DISCONNECTED)
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from device."""
        self._connected = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self.emit(DriverEvents.DISCONNECTED)

    async def send_command(self, command: str) -> None:
        """Send command to device."""
        if not self._writer or not self._connected:
            _LOG.warning("Attempted to send command while disconnected")
            return

        try:
            _LOG.debug("TX: %s", command)
            self._writer.write(command.encode())
            await self._writer.drain()
        except Exception as err:
            _LOG.error("Failed to send command: %s", err)
            await self.disconnect()

    async def _read_loop(self) -> None:
        """Continuous read loop for incoming data."""
        buffer = ""
        while self._connected and self._reader:
            try:
                data = await self._reader.read(1024)
                if not data:
                    break
                
                text = data.decode("utf-8", errors="ignore")
                buffer += text
                while ";" in buffer:
                    message, buffer = buffer.split(";", 1)
                    await self._process_message(message.strip())
                    
            except Exception as err:
                _LOG.error("Read loop error: %s", err)
                break
        
        await self.disconnect()

    async def _process_message(self, message: str) -> None:
        """Process incoming protocol message."""
        if not message:
            return

        _LOG.debug("RX: %s", message)
        if message.startswith("ISN"):
            try:
                # Extract ID (index 3-5) and Name (index 5+)
                input_id_str = message[3:5]
                input_name = message[5:]
                
                if input_id_str.isdigit():
                    input_id = int(input_id_str)
                    # ID 00 usually means invalid/none in Anthem protocol
                    if input_id > 0 and self.on_input_discovered:
                        self.on_input_discovered(input_id, input_name)
            except Exception as err:
                _LOG.warning("Failed to parse ISN message: %s", err)

        # Emit for generic listeners (Power, Vol, etc.)
        self.emit(DriverEvents.MESSAGE, message)