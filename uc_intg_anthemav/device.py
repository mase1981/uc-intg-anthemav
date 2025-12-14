"""
Anthem A/V Receiver Device Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
from typing import Any
from ucapi import EntityTypes

from ucapi_framework import PersistentConnectionDevice, DeviceEvents, create_entity_id

from uc_intg_anthemav.config import AnthemDeviceConfig

_LOG = logging.getLogger(__name__)


class AnthemDevice(PersistentConnectionDevice):
    """Anthem A/V receiver device with TCP connection."""

    _device_config: AnthemDeviceConfig

    def __init__(self, device_config: AnthemDeviceConfig):
        super().__init__(device_config)

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._state_cache: dict[str, Any] = {}
        self._input_count = 0
        self._input_names: dict[int, str] = {}
        self._input_discovery_complete = False

    async def establish_connection(self) -> bool:
        """Establish TCP connection to Anthem receiver."""
        try:
            _LOG.info(
                f"Connecting to {self.device_config.name} at {self.device_config.host}:{self.device_config.port}"
            )

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.device_config.host, self.device_config.port
                ),
                timeout=self.device_config.timeout,
            )

            peer = self._writer.get_extra_info("peername")
            _LOG.info(
                f"TCP connection established to {self.device_config.name} - Peer: {peer}"
            )

            await asyncio.sleep(0.2)

            _LOG.info("Sending initialization sequence...")
            await self._send_command("ECH0")
            await asyncio.sleep(0.1)

            await self._send_command("SIP1")
            _LOG.info(
                "Enabled Standby IP Control (SIP1) - device will respond in standby"
            )
            await asyncio.sleep(0.1)

            await self._send_command("ICN?")
            await asyncio.sleep(0.2)

            await self._send_command("Z1POW?")
            await asyncio.sleep(0.1)

            _LOG.info(f"Initialization complete for {self.device_config.name}")
            return True

        except asyncio.TimeoutError:
            _LOG.error(f"Connection timeout after {self.device_config.timeout}s")
            return False
        except OSError as e:
            _LOG.error(f"Network error: {e}")
            return False
        except Exception as e:
            _LOG.error(f"Unexpected error during connection: {e}", exc_info=True)
            return False

    async def maintain_connection(self) -> None:
        """Maintain connection and process incoming messages."""
        buffer = ""
        receive_count = 0

        _LOG.info(f"Message receive loop started for {self.device_config.name}")

        while self.is_connected and self._reader:
            try:
                _LOG.debug(f"Waiting for data (receive #{receive_count + 1})...")
                data = await asyncio.wait_for(self._reader.read(1024), timeout=120.0)

                if not data:
                    _LOG.warning(
                        f"Connection closed by {self.device_config.name} (empty read)"
                    )
                    break

                receive_count += 1
                _LOG.info(
                    f"Received {len(data)} bytes (receive #{receive_count}): {data}"
                )

                decoded = data.decode("ascii", errors="ignore")
                _LOG.debug(f"Decoded string: '{decoded}' (len={len(decoded)})")
                buffer += decoded

                _LOG.debug(f"Current buffer: '{buffer}' (len={len(buffer)})")

                lines_processed = 0
                while ";" in buffer:
                    line, buffer = buffer.split(";", 1)
                    _LOG.debug(
                        f"Split on semicolon: line='{line}', remaining buffer='{buffer}'"
                    )

                    line = line.strip()

                    if line:
                        lines_processed += 1
                        _LOG.info(f"Processing line {lines_processed}: '{line}'")
                        await self._process_response(line)

                if lines_processed > 0:
                    _LOG.debug(f"Processed {lines_processed} lines from this receive")

            except asyncio.TimeoutError:
                _LOG.debug("Read timeout (120s), continuing...")
                continue
            except Exception as e:
                _LOG.error(f"Error in receive loop: {e}", exc_info=True)
                break

        _LOG.info(
            f"Receive loop ended for {self.device_config.name} (received {receive_count} messages total)"
        )

    async def close_connection(self) -> None:
        """Close TCP connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
                _LOG.debug("Connection closed successfully")
            except Exception as e:
                _LOG.error(f"Error closing connection: {e}")

        self._reader = None
        self._writer = None

    async def _send_command(self, command: str) -> bool:
        """Send command to receiver."""
        if not self.is_connected or not self._writer:
            _LOG.warning(f"Cannot send command {command}: not connected")
            return False

        try:
            cmd_bytes = f"{command}\r".encode("ascii")
            _LOG.debug(f"Sending {len(cmd_bytes)} bytes: {cmd_bytes}")
            self._writer.write(cmd_bytes)
            await self._writer.drain()
            _LOG.info(f"Sent command: {command}")
            return True
        except Exception as e:
            _LOG.error(f"Error sending command {command}: {e}", exc_info=True)
            return False

    async def _process_response(self, response: str) -> None:
        """Process incoming response from receiver."""
        _LOG.info(f"RECEIVED: {response}")

        if response.startswith("!I") or response.startswith("!E"):
            _LOG.warning(f"Device returned error response: {response}")
            return

        try:
            self._update_state_from_response(response)
        except Exception as e:
            _LOG.error(
                f"Error updating state from response '{response}': {e}", exc_info=True
            )

    def _update_state_from_response(self, response: str) -> None:
        """Update internal state cache and emit events."""
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
            count_match = re.match(r"ICN(\d+)", response)
            if count_match:
                self._input_count = int(count_match.group(1))
                _LOG.info(f"Input count: {self._input_count}")
                asyncio.create_task(self._discover_input_names())

        elif response.startswith("ISN") and len(response) > 5:
            input_match = re.match(r"ISN(\d{2})(.+)", response)
            if input_match:
                input_num = int(input_match.group(1))
                input_name = input_match.group(2).strip()
                self._input_names[input_num] = input_name
                _LOG.info(f"Input {input_num} name: {input_name}")

                if len(self._input_names) >= self._input_count:
                    self._input_discovery_complete = True
                    _LOG.info(
                        f"Input name discovery complete: {len(self._input_names)} inputs"
                    )
                    # The update event should receive an entity_id. I updated both occurrences.
                    # This one also needed a zone number that wasn't available, so I made an assumption,
                    # that all zones would share the same the same source list and updated all.
                    # IF this is incorrect, you need a way to determine which zone you're updating here.
                    for zone_num in self._device_config.zones:
                        self.events.emit(
                            DeviceEvents.UPDATE,
                            create_entity_id(
                                EntityTypes.MEDIA_PLAYER,
                                self._device_config.identifier,
                                zone_num,
                            ),
                            {"inputs_discovered": True},
                        )

        elif response.startswith("SIP"):
            sip_value = response[3:].strip()
            if sip_value == "1":
                _LOG.info("Standby IP Control confirmed ENABLED")
            elif sip_value == "0":
                _LOG.warning("Standby IP Control is DISABLED - re-enabling...")
                asyncio.create_task(self._send_command("SIP1"))

        elif response.startswith("Z"):
            zone_match = re.match(r"Z(\d+)", response)
            if zone_match:
                zone_num = int(zone_match.group(1))
                zone_key = f"zone_{zone_num}"

                if zone_key not in self._state_cache:
                    self._state_cache[zone_key] = {}

                zone_state = self._state_cache[zone_key]
                state_changed = False

                if "POW" in response:
                    power = "1" in response
                    if zone_state.get("power") != power:
                        zone_state["power"] = power
                        state_changed = True
                        _LOG.debug(f"Zone {zone_num} power: {power}")

                elif "VOL" in response:
                    vol_match = re.search(r"VOL(-?\d+(?:\.\d+)?)", response)
                    if vol_match:
                        volume = int(float(vol_match.group(1)))
                        if zone_state.get("volume") != volume:
                            zone_state["volume"] = volume
                            state_changed = True
                            _LOG.debug(f"Zone {zone_num} volume: {volume}dB")

                elif "MUT" in response:
                    muted = "1" in response
                    if zone_state.get("muted") != muted:
                        zone_state["muted"] = muted
                        state_changed = True
                        _LOG.debug(f"Zone {zone_num} muted: {muted}")

                elif "INP" in response:
                    inp_match = re.search(r"INP(\d+)", response)
                    if inp_match:
                        input_num = int(inp_match.group(1))
                        if zone_state.get("input") != input_num:
                            zone_state["input"] = input_num
                            state_changed = True
                            _LOG.debug(f"Zone {zone_num} input: {input_num}")

                            if input_num in self._input_names:
                                zone_state["input_name"] = self._input_names[input_num]

                if state_changed:
                    self.events.emit(
                        DeviceEvents.UPDATE,
                        create_entity_id(
                            EntityTypes.MEDIA_PLAYER,
                            self.device_config.identifier,
                            zone_num,
                        ),
                        {"zone": zone_num, "state": zone_state.copy()},
                    )

    async def _discover_input_names(self) -> None:
        """Discover input names from receiver."""
        if self._input_count == 0:
            _LOG.warning("Input count is 0, skipping input name discovery")
            return

        _LOG.info(f"Starting input name discovery for {self._input_count} inputs")

        for input_num in range(1, self._input_count + 1):
            await self._send_command(f"ISN{input_num:02d}?")
            await asyncio.sleep(0.1)

        await asyncio.sleep(1.0)

        if not self._input_discovery_complete:
            missing_inputs = set(range(1, self._input_count + 1)) - set(
                self._input_names.keys()
            )
            if missing_inputs:
                _LOG.warning(
                    f"Input name discovery incomplete. Missing inputs: {missing_inputs}"
                )

    async def power_on(self, zone: int = 1) -> bool:
        """Power on zone."""
        return await self._send_command(f"Z{zone}POW1")

    async def power_off(self, zone: int = 1) -> bool:
        """Power off zone."""
        return await self._send_command(f"Z{zone}POW0")

    async def set_volume(self, volume: int, zone: int = 1) -> bool:
        """Set volume (-90 to 0 dB)."""
        volume = max(-90, min(0, volume))
        return await self._send_command(f"Z{zone}VOL{volume}")

    async def volume_up(self, zone: int = 1) -> bool:
        """Increase volume by 1dB."""
        return await self._send_command(f"Z{zone}VUP")

    async def volume_down(self, zone: int = 1) -> bool:
        """Decrease volume by 1dB."""
        return await self._send_command(f"Z{zone}VDN")

    async def set_mute(self, muted: bool, zone: int = 1) -> bool:
        """Set mute state."""
        return await self._send_command(f"Z{zone}MUT{'1' if muted else '0'}")

    async def select_input(self, input_num: int, zone: int = 1) -> bool:
        """Select input source."""
        return await self._send_command(f"Z{zone}INP{input_num}")

    async def query_power(self, zone: int = 1) -> bool:
        """Query power state."""
        return await self._send_command(f"Z{zone}POW?")

    async def query_volume(self, zone: int = 1) -> bool:
        """Query volume level."""
        return await self._send_command(f"Z{zone}VOL?")

    async def query_mute(self, zone: int = 1) -> bool:
        """Query mute state."""
        return await self._send_command(f"Z{zone}MUT?")

    async def query_input(self, zone: int = 1) -> bool:
        """Query selected input."""
        return await self._send_command(f"Z{zone}INP?")

    async def query_model(self) -> bool:
        """Query device model."""
        return await self._send_command("IDM?")

    async def query_all_status(self, zone: int = 1) -> bool:
        """Query all status for zone."""
        await self.query_power(zone)
        await asyncio.sleep(0.1)
        await self.query_volume(zone)
        await asyncio.sleep(0.1)
        await self.query_mute(zone)
        await asyncio.sleep(0.1)
        await self.query_input(zone)
        await asyncio.sleep(0.1)
        return True

    def get_zone_state(self, zone: int) -> dict[str, Any]:
        """Get cached state for zone."""
        zone_key = f"zone_{zone}"
        return self._state_cache.get(zone_key, {})

    def get_cached_state(self, key: str, zone: int | None = None) -> Any:
        """Get cached state value."""
        if zone is not None:
            zone_key = f"zone_{zone}"
            zone_data = self._state_cache.get(zone_key, {})
            return zone_data.get(key)
        return self._state_cache.get(key)

    def get_input_list(self) -> list[str]:
        """Get list of available inputs."""
        if not self._input_names:
            return [
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

        input_list = []
        for i in range(1, self._input_count + 1):
            if i in self._input_names:
                input_list.append(self._input_names[i])
            else:
                input_list.append(f"Input {i}")

        return input_list

    def get_input_number_by_name(self, name: str) -> int | None:
        """Get input number by name."""
        for num, inp_name in self._input_names.items():
            if inp_name == name:
                return num

        default_map = {
            "HDMI 1": 1,
            "HDMI 2": 2,
            "HDMI 3": 3,
            "HDMI 4": 4,
            "HDMI 5": 5,
            "HDMI 6": 6,
            "HDMI 7": 7,
            "HDMI 8": 8,
            "Analog 1": 9,
            "Analog 2": 10,
            "Digital 1": 11,
            "Digital 2": 12,
            "USB": 13,
            "Network": 14,
            "ARC": 15,
        }
        return default_map.get(name)
