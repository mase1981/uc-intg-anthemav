"""
Anthem A/V Receiver Client Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
from typing import Any, Dict, Optional, Callable

from uc_intg_anthemav.config import DeviceConfig, ZoneConfig

_LOG = logging.getLogger(__name__)


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
        self._input_count = 0
        self._input_names: Dict[int, str] = {}
        self._input_discovery_complete = False
        
    async def connect(self) -> bool:
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                async with self._lock:
                    if self._connected:
                        return True
                    
                    _LOG.info(f"Connecting to {self._device_config.name} at {self._device_config.ip_address}:{self._device_config.port} (attempt {attempt + 1}/{max_retries})")
                    
                    try:
                        self._reader, self._writer = await asyncio.wait_for(
                            asyncio.open_connection(
                                self._device_config.ip_address,
                                self._device_config.port
                            ),
                            timeout=self._device_config.timeout
                        )
                    except asyncio.TimeoutError:
                        _LOG.error(f"Connection timeout after {self._device_config.timeout}s")
                        raise
                    except OSError as e:
                        _LOG.error(f"OSError during connection: {e} (errno: {e.errno if hasattr(e, 'errno') else 'N/A'})")
                        raise
                    
                    self._connected = True
                    _LOG.info(f"TCP connection established to {self._device_config.name}")
                    
                    peer = self._writer.get_extra_info('peername')
                    sock = self._writer.get_extra_info('socket')
                    _LOG.info(f"Connection details - Peer: {peer}, Socket: {sock}")
                    
                    self._listen_task = asyncio.create_task(self._listen())
                    _LOG.info(f"Listen task created for {self._device_config.name}")
                    
                    await asyncio.sleep(0.2)
                    
                    _LOG.info("Sending initialization sequence...")
                    await self._send_command("ECH0")
                    await asyncio.sleep(0.1)
                    
                    await self._send_command("ICN?")
                    await asyncio.sleep(0.2)
                    
                    await self._send_command("Z1POW?")
                    await asyncio.sleep(0.1)
                    
                    _LOG.info(f"Initialization sequence complete for {self._device_config.name}")
                    
                    return True
                    
            except asyncio.TimeoutError:
                _LOG.error(f"Connection timeout to {self._device_config.name} (attempt {attempt + 1})")
                await self.disconnect()
                if attempt < max_retries - 1:
                    _LOG.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
            except OSError as e:
                _LOG.error(f"Network error connecting to {self._device_config.name}: {e} (attempt {attempt + 1})")
                await self.disconnect()
                if attempt < max_retries - 1:
                    _LOG.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                _LOG.error(f"Unexpected connection error to {self._device_config.name}: {e} (attempt {attempt + 1})", exc_info=True)
                await self.disconnect()
                if attempt < max_retries - 1:
                    _LOG.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
        
        _LOG.error(f"Failed to connect to {self._device_config.name} after {max_retries} attempts")
        return False
    
    async def disconnect(self) -> None:
        async with self._lock:
            if not self._connected and not self._writer:
                return
            
            _LOG.info(f"Disconnecting from {self._device_config.name}")
            
            if self._listen_task:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    _LOG.debug("Listen task cancelled")
                except Exception as e:
                    _LOG.error(f"Error cancelling listen task: {e}")
                self._listen_task = None
            
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                    _LOG.debug("Writer closed successfully")
                except Exception as e:
                    _LOG.error(f"Error closing writer: {e}")
            
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
            _LOG.debug(f"Sending {len(cmd_bytes)} bytes: {cmd_bytes}")
            self._writer.write(cmd_bytes)
            await self._writer.drain()
            _LOG.info(f"Sent command: {command}")
            return True
        except Exception as e:
            _LOG.error(f"Error sending command {command}: {e}", exc_info=True)
            self._connected = False
            return False
    
    async def _listen(self) -> None:
        buffer = ""
        _LOG.info(f"Listen loop started for {self._device_config.name}")
        
        receive_count = 0
        
        while self._connected and self._reader:
            try:
                _LOG.debug(f"Waiting for data (receive #{receive_count + 1})...")
                data = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=120.0
                )
                
                if not data:
                    _LOG.warning(f"Connection closed by {self._device_config.name} (empty read)")
                    self._connected = False
                    break
                
                receive_count += 1
                _LOG.info(f"Received {len(data)} bytes (receive #{receive_count}): {data}")
                
                try:
                    decoded = data.decode('ascii', errors='ignore')
                    _LOG.debug(f"Decoded string: '{decoded}' (len={len(decoded)})")
                    buffer += decoded
                except Exception as e:
                    _LOG.error(f"Error decoding data: {e}")
                    continue
                
                _LOG.debug(f"Current buffer: '{buffer}' (len={len(buffer)})")
                
                lines_processed = 0
                while '\r' in buffer or '\n' in buffer:
                    if '\r' in buffer:
                        line, buffer = buffer.split('\r', 1)
                        _LOG.debug(f"Split on \\r: line='{line}', remaining buffer='{buffer}'")
                    elif '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        _LOG.debug(f"Split on \\n: line='{line}', remaining buffer='{buffer}'")
                    
                    line = line.strip()
                    
                    if line:
                        lines_processed += 1
                        _LOG.info(f"Processing line {lines_processed}: '{line}'")
                        await self._process_response(line)
                    else:
                        _LOG.debug("Empty line after strip, skipping")
                
                if lines_processed > 0:
                    _LOG.debug(f"Processed {lines_processed} lines from this receive")
                
            except asyncio.TimeoutError:
                _LOG.debug("Read timeout (120s), continuing...")
                continue
            except asyncio.CancelledError:
                _LOG.info("Listen task cancelled")
                break
            except Exception as e:
                _LOG.error(f"Error in listen loop: {e}", exc_info=True)
                self._connected = False
                break
        
        _LOG.info(f"Listen loop ended for {self._device_config.name} (received {receive_count} messages total)")
    
    async def _process_response(self, response: str) -> None:
        _LOG.info(f"RECEIVED: {response}")
        
        try:
            self._update_state_from_response(response)
        except Exception as e:
            _LOG.error(f"Error updating state from response '{response}': {e}", exc_info=True)
        
        if self._update_callback:
            try:
                self._update_callback(response)
            except Exception as e:
                _LOG.error(f"Error in update callback: {e}", exc_info=True)
    
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
        
        elif response.startswith("ICN"):
            count_match = re.match(r'ICN(\d+)', response)
            if count_match:
                self._input_count = int(count_match.group(1))
                _LOG.info(f"Input count: {self._input_count}")
                asyncio.create_task(self._discover_input_names())
        
        elif response.startswith("ISN") and len(response) > 5:
            input_match = re.match(r'ISN(\d{2})(.+)', response)
            if input_match:
                input_num = int(input_match.group(1))
                input_name = input_match.group(2).strip()
                self._input_names[input_num] = input_name
                _LOG.info(f"Input {input_num} name: {input_name}")
                
                if len(self._input_names) >= self._input_count:
                    self._input_discovery_complete = True
                    _LOG.info(f"Input name discovery complete: {len(self._input_names)} inputs discovered")
        
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
                    _LOG.debug(f"Zone {zone_num} power: {power}")
                
                elif "VOL" in response:
                    vol_match = re.search(r'VOL(-?\d+)', response)
                    if vol_match:
                        volume = int(vol_match.group(1))
                        self._state_cache[zone_key]["volume"] = volume
                        _LOG.debug(f"Zone {zone_num} volume: {volume}dB")
                
                elif "MUT" in response:
                    muted = "1" in response
                    self._state_cache[zone_key]["muted"] = muted
                    _LOG.debug(f"Zone {zone_num} muted: {muted}")
                
                elif "INP" in response:
                    inp_match = re.search(r'INP(\d+)', response)
                    if inp_match:
                        input_num = int(inp_match.group(1))
                        self._state_cache[zone_key]["input"] = input_num
                        _LOG.debug(f"Zone {zone_num} input: {input_num}")
                        
                        if input_num in self._input_names:
                            self._state_cache[zone_key]["input_name"] = self._input_names[input_num]
                
                elif "SIP" in response:
                    inp_match = re.search(r'SIP"([^"]*)"', response)
                    if inp_match:
                        input_name = inp_match.group(1)
                        self._state_cache[zone_key]["input_name"] = input_name
                        _LOG.debug(f"Zone {zone_num} input name: {input_name}")
                
                elif "AIC" in response:
                    format_match = re.search(r'AIC"([^"]*)"', response)
                    if format_match:
                        audio_format = format_match.group(1)
                        self._state_cache[zone_key]["audio_format"] = audio_format
                        _LOG.debug(f"Zone {zone_num} audio format: {audio_format}")
    
    async def _discover_input_names(self) -> None:
        if self._input_count == 0:
            _LOG.warning("Input count is 0, skipping input name discovery")
            return
        
        _LOG.info(f"Starting input name discovery for {self._input_count} inputs")
        
        for input_num in range(1, self._input_count + 1):
            await self._send_command(f"ISN{input_num:02d}")
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1.0)
        
        if not self._input_discovery_complete:
            missing_inputs = set(range(1, self._input_count + 1)) - set(self._input_names.keys())
            if missing_inputs:
                _LOG.warning(f"Input name discovery incomplete. Missing inputs: {missing_inputs}")
    
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
        success = await self._send_command(f"Z{zone}INP{input_num}")
        if success:
            await asyncio.sleep(0.1)
            await self.query_input_name(zone)
        return success
    
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
    
    def get_input_list(self) -> list[str]:
        if not self._input_names:
            return [
                "HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4",
                "HDMI 5", "HDMI 6", "HDMI 7", "HDMI 8",
                "Analog 1", "Analog 2",
                "Digital 1", "Digital 2",
                "USB", "Network", "ARC"
            ]
        
        input_list = []
        for i in range(1, self._input_count + 1):
            if i in self._input_names:
                input_list.append(self._input_names[i])
            else:
                input_list.append(f"Input {i}")
        
        return input_list
    
    def get_input_number_by_name(self, name: str) -> Optional[int]:
        for num, inp_name in self._input_names.items():
            if inp_name == name:
                return num
        
        default_map = {
            "HDMI 1": 1, "HDMI 2": 2, "HDMI 3": 3, "HDMI 4": 4,
            "HDMI 5": 5, "HDMI 6": 6, "HDMI 7": 7, "HDMI 8": 8,
            "Analog 1": 9, "Analog 2": 10,
            "Digital 1": 11, "Digital 2": 12,
            "USB": 13, "Network": 14, "ARC": 15
        }
        return default_map.get(name)
    
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