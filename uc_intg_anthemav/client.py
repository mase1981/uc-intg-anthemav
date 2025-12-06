"""
Anthem A/V Receiver Client Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional, Callable
import errno

from uc_intg_anthemav.config import DeviceConfig, ZoneConfig

_LOG = logging.getLogger(__name__)

NETWORK_RETRY_DELAY = 2.0
MAX_NETWORK_RETRIES = 5


class ConnectionError(Exception):
    pass


class CommandError(Exception):
    pass


class AnthemClient:
    
    def __init__(self, device_config: DeviceConfig):
        self._device_config = device_config
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._update_callback: Optional[Callable[[str], None]] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._state_cache: Dict[str, Any] = {}
        self._zones_initialized = False
        
    async def connect(self) -> bool:
        async with self._lock:
            if self._connected:
                return True
            
            retry_count = 0
            last_error = None
            
            while retry_count < MAX_NETWORK_RETRIES:
                try:
                    _LOG.info(f"Connecting to {self._device_config.name} at {self._device_config.ip_address}:{self._device_config.port} (attempt {retry_count + 1}/{MAX_NETWORK_RETRIES})")
                    
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(
                            self._device_config.ip_address,
                            self._device_config.port
                        ),
                        timeout=self._device_config.timeout
                    )
                    
                    self._connected = True
                    _LOG.info(f"Connected to {self._device_config.name}")
                    
                    self._listen_task = asyncio.create_task(self._listen())
                    
                    await asyncio.sleep(0.2)
                    
                    _LOG.info(f"Listen task started for {self._device_config.name}")
                    
                    await self._send_command("ECH0")
                    await asyncio.sleep(0.1)
                    await self._send_command("Z1POW?")
                    
                    return True
                    
                except OSError as e:
                    if e.errno == errno.ENETUNREACH:
                        last_error = e
                        retry_count += 1
                        _LOG.warning(f"Network unreachable for {self._device_config.name}, retrying in {NETWORK_RETRY_DELAY}s (attempt {retry_count}/{MAX_NETWORK_RETRIES})")
                        if retry_count < MAX_NETWORK_RETRIES:
                            await asyncio.sleep(NETWORK_RETRY_DELAY)
                            continue
                        else:
                            _LOG.error(f"Network still unreachable after {MAX_NETWORK_RETRIES} attempts")
                            return False
                    else:
                        _LOG.error(f"OS error connecting to {self._device_config.name}: {e}")
                        return False
                        
                except asyncio.TimeoutError:
                    _LOG.error(f"Connection timeout to {self._device_config.name}")
                    return False
                    
                except Exception as e:
                    _LOG.error(f"Connection error to {self._device_config.name}: {e}")
                    return False
            
            return False
    
    async def disconnect(self) -> None:
        async with self._lock:
            if not self._connected:
                return
            
            _LOG.info(f"Disconnecting from {self._device_config.name}")
            
            if self._listen_task:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None
            
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception as e:
                    _LOG.debug(f"Error closing writer: {e}")
            
            self._connected = False
            self._reader = None
            self._writer = None
            _LOG.info(f"Disconnected from {self._device_config.name}")
    
    async def _send_command(self, command: str) -> bool:
        if not self._connected or not self._writer:
            _LOG.warning(f"Cannot send command {command}: not connected")
            return False
        
        try:
            cmd_bytes = f"{command}\r".encode('ascii')
            self._writer.write(cmd_bytes)
            await self._writer.drain()
            _LOG.info(f"Sent command: {command}")
            return True
        except Exception as e:
            _LOG.error(f"Error sending command {command}: {e}")
            self._connected = False
            return False
    
    async def _listen(self) -> None:
        buffer = ""
        
        while self._connected and self._reader:
            try:
                data = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=60.0
                )
                
                if not data:
                    _LOG.warning(f"Connection closed by {self._device_config.name}")
                    self._connected = False
                    break
                
                buffer += data.decode('ascii', errors='ignore')
                
                lines = buffer.splitlines(keepends=True)
                
                if lines and not lines[-1].endswith(('\r', '\n')):
                    buffer = lines.pop()
                else:
                    buffer = ""
                
                for line in lines:
                    line = line.strip()
                    if line:
                        await self._process_response(line)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                _LOG.error(f"Error in listen loop: {e}")
                self._connected = False
                break
        
        _LOG.info(f"Listen task ended for {self._device_config.name}")
    
    async def _process_response(self, response: str) -> None:
        _LOG.info(f"Received: {response}")
        
        self._update_state_from_response(response)
        
        if self._update_callback:
            try:
                self._update_callback(response)
            except Exception as e:
                _LOG.error(f"Error in update callback: {e}")
    
    def _update_state_from_response(self, response: str) -> None:
        if response.startswith("IDM"):
            model = response[3:].strip()
            self._state_cache["model"] = model
            _LOG.info(f"Device model: {model}")
        
        elif response.startswith("IDN"):
            name = response[3:].strip()
            self._state_cache["device_name"] = name
        
        elif response.startswith("IDR"):
            region = response[3:].strip()
            self._state_cache["region"] = region
        
        elif response.startswith("IDS"):
            software = response[3:].strip()
            self._state_cache["software_version"] = software
        
        elif response.startswith("Z"):
            zone_match = re.match(r'Z(\d+)', response)
            if zone_match:
                zone_num = int(zone_match.group(1))
                zone_key = f"zone_{zone_num}"
                
                if zone_key not in self._state_cache:
                    self._state_cache[zone_key] = {}
                
                if "POW" in response:
                    power = "1" in response
                    self._state_cache[zone_key]["power"] = power
                
                elif "VOL" in response:
                    vol_match = re.search(r'VOL(-?\d+)', response)
                    if vol_match:
                        volume = int(vol_match.group(1))
                        self._state_cache[zone_key]["volume"] = volume
                
                elif "MUT" in response:
                    muted = "1" in response
                    self._state_cache[zone_key]["muted"] = muted
                
                elif "INP" in response:
                    inp_match = re.search(r'INP(\d+)', response)
                    if inp_match:
                        input_num = int(inp_match.group(1))
                        self._state_cache[zone_key]["input"] = input_num
                
                elif "SIP" in response:
                    inp_match = re.search(r'SIP"([^"]*)"', response)
                    if inp_match:
                        input_name = inp_match.group(1)
                        self._state_cache[zone_key]["input_name"] = input_name
                
                elif "AIC" in response:
                    format_match = re.search(r'AIC"([^"]*)"', response)
                    if format_match:
                        audio_format = format_match.group(1)
                        self._state_cache[zone_key]["audio_format"] = audio_format
    
    def set_update_callback(self, callback: Callable[[str], None]) -> None:
        self._update_callback = callback
    
    async def power_on(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}POW1")
    
    async def power_off(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}POW0")
    
    async def set_volume(self, volume: int, zone: int = 1) -> bool:
        volume = max(-90, min(0, volume))
        return await self._send_command(f"Z{zone}VOL{volume}")
    
    async def volume_up(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}VUP")
    
    async def volume_down(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}VDN")
    
    async def set_mute(self, muted: bool, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}MUT{'1' if muted else '0'}")
    
    async def select_input(self, input_num: int, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}INP{input_num}")
    
    async def query_power(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}POW?")
    
    async def query_volume(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}VOL?")
    
    async def query_mute(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}MUT?")
    
    async def query_input(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}INP?")
    
    async def query_input_name(self, zone: int = 1) -> bool:
        return await self._send_command(f"Z{zone}SIP?")
    
    async def query_model(self) -> bool:
        return await self._send_command("IDM?")
    
    async def query_all_status(self, zone: int = 1) -> bool:
        await self.query_power(zone)
        await asyncio.sleep(0.1)
        await self.query_volume(zone)
        await asyncio.sleep(0.1)
        await self.query_mute(zone)
        await asyncio.sleep(0.1)
        await self.query_input(zone)
        await asyncio.sleep(0.1)
        await self.query_input_name(zone)
        return True
    
    def get_zone_state(self, zone: int) -> Dict[str, Any]:
        zone_key = f"zone_{zone}"
        return self._state_cache.get(zone_key, {})
    
    def get_cached_state(self, key: str, zone: Optional[int] = None) -> Any:
        if zone is not None:
            zone_key = f"zone_{zone}"
            zone_data = self._state_cache.get(zone_key, {})
            return zone_data.get(key)
        return self._state_cache.get(key)
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def device_config(self) -> DeviceConfig:
        return self._device_config
    
    @property
    def device_name(self) -> str:
        return self._device_config.name
    
    @property
    def device_ip(self) -> str:
        return self._device_config.ip_address
    
    async def close(self) -> None:
        await self.disconnect()