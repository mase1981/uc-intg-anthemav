"""
Anthem A/V Receiver device implementation using PersistentConnectionDevice.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import re
from typing import Any
from time import time

from ucapi_framework import PersistentConnectionDevice, DeviceEvents
from ucapi.media_player import Attributes as MediaAttributes
from ucapi.sensor import Attributes as SensorAttributes, States as SensorStates

from .config import AnthemDeviceConfig

_LOG = logging.getLogger(__name__)


class AnthemDevice(PersistentConnectionDevice):
    def __init__(self, device_config: AnthemDeviceConfig, **kwargs):
        super().__init__(device_config, **kwargs)
        self._device_config = device_config
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._zone_states: dict[int, dict[str, Any]] = {}
        self._input_names: dict[int, str] = {}
        self._input_count: int = 0

        self._last_volume_update: dict[int, tuple[int, float]] = {}
        self._volume_debounce_ms = 100

    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    async def establish_connection(self) -> Any:
        """
        Establish TCP connection to Anthem receiver.

        :return: Tuple of (reader, writer)
        """
        _LOG.info(
            "[%s] Establishing TCP connection to %s:%d",
            self.log_id,
            self._device_config.host,
            self._device_config.port,
        )

        self._reader, self._writer = await asyncio.open_connection(
            self._device_config.host, self._device_config.port
        )

        await self._send_command("ECH0")
        await asyncio.sleep(0.1)
        await self._send_command("SIP1")
        await asyncio.sleep(0.1)
        await self._send_command("ICN?")
        await asyncio.sleep(0.2)

        for zone in self._device_config.zones:
            if zone.enabled:
                await self._send_command(f"Z{zone.zone_number}POW?")
                await asyncio.sleep(0.05)

        _LOG.info("[%s] Connection established and initialized", self.log_id)
        return (self._reader, self._writer)

    async def close_connection(self) -> None:
        """Close TCP connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as err:
                _LOG.debug("[%s] Error closing connection: %s", self.log_id, err)

        self._reader = None
        self._writer = None

    async def maintain_connection(self) -> None:
        buffer = ""
        _LOG.debug("[%s] Message loop started", self.log_id)

        while self._reader and not self._reader.at_eof():
            try:
                data = await asyncio.wait_for(self._reader.read(1024), timeout=120.0)

                if not data:
                    _LOG.warning("[%s] Connection closed by device", self.log_id)
                    break

                decoded = data.decode("ascii", errors="ignore")
                buffer += decoded

                while ";" in buffer:
                    line, buffer = buffer.split(";", 1)
                    line = line.strip()
                    if line:
                        await self._process_response(line)

            except asyncio.TimeoutError:
                continue
            except Exception as err:
                _LOG.error("[%s] Error in message loop: %s", self.log_id, err)
                break

        _LOG.debug("[%s] Message loop ended", self.log_id)

    async def _send_command(self, command: str) -> bool:

        if not self._writer:
            _LOG.warning("[%s] Cannot send command - not connected", self.log_id)
            return False

        try:
            cmd_bytes = f"{command};".encode("ascii")
            self._writer.write(cmd_bytes)
            await self._writer.drain()
            _LOG.debug("[%s] Sent command: %s", self.log_id, command)
            return True
        except Exception as err:
            _LOG.error("[%s] Error sending command %s: %s", self.log_id, command, err)
            return False

    async def _process_response(self, response: str) -> None:
        """Process a response from the receiver."""
        _LOG.debug("[%s] RECEIVED: %s", self.log_id, response)

        if response.startswith("!I") or response.startswith("!E"):
            _LOG.warning("[%s] Device error: %s", self.log_id, response)
            return

        self._update_state_from_response(response)

    def _update_state_from_response(self, response: str) -> None:
        """Update device state from response."""
        if response.startswith("IDM"):
            model = response[3:].strip()
            self._state = {"model": model}
            _LOG.info("[%s] Model: %s", self.log_id, model)

        elif response.startswith("ICN"):
            count_match = re.match(r"ICN(\d+)", response)
            if count_match:
                self._input_count = int(count_match.group(1))
                _LOG.info("[%s] Input count: %d", self.log_id, self._input_count)
                asyncio.create_task(self._discover_input_names())

        elif response.startswith("IS") and "IN" in response and len(response) > 5:
            # Handle ISiINyyyy format for custom input names (i=01-30, yyyy=16 char name)
            input_match = re.match(r"IS(\d{1,2})IN(.+)", response)
            if input_match:
                input_num = int(input_match.group(1))
                input_name = input_match.group(2).strip()
                self._input_names[input_num] = input_name
                _LOG.debug("[%s] Input %d: %s", self.log_id, input_num, input_name)

                if len(self._input_names) == self._input_count:
                    _LOG.info(
                        "[%s] All %d inputs discovered, updating source lists",
                        self.log_id,
                        self._input_count,
                    )
                    source_list = self.get_input_list()

                    for zone_config in self._device_config.zones:
                        if zone_config.enabled:
                            entity_id = self._get_entity_id_for_zone(
                                zone_config.zone_number
                            )
                            if entity_id:
                                self.events.emit(
                                    DeviceEvents.UPDATE,
                                    entity_id,
                                    {MediaAttributes.SOURCE_LIST.value: source_list},
                                )

        elif response.startswith("Z"):
            zone_match = re.match(r"Z(\d+)", response)
            if zone_match:
                zone_num = int(zone_match.group(1))

                if zone_num not in self._zone_states:
                    self._zone_states[zone_num] = {}

                state = self._zone_states[zone_num]
                entity_id = self._get_entity_id_for_zone(zone_num)

                if "POW" in response:
                    power = "1" in response
                    state["power"] = power
                    new_state = "ON" if power else "OFF"
                    self._state = new_state

                    if entity_id:
                        self.events.emit(
                            DeviceEvents.UPDATE,
                            entity_id,
                            {MediaAttributes.STATE.value: new_state},
                        )

                elif "VOL" in response:
                    vol_match = re.search(r"VOL(-?\d+)", response)
                    if vol_match:
                        volume_db = int(vol_match.group(1))

                        if volume_db < -90 or volume_db > 0:
                            _LOG.warning(
                                "[%s] Invalid volume dB value: %d (must be -90 to 0), ignoring",
                                self.log_id,
                                volume_db
                            )
                            return

                        state["volume_db"] = volume_db
                        volume_pct = int(((volume_db + 90) / 90) * 100)

                        volume_pct = max(0, min(100, volume_pct))

                        current_time = time()
                        if zone_num in self._last_volume_update:
                            last_vol, last_time = self._last_volume_update[zone_num]
                            time_diff_ms = (current_time - last_time) * 1000

                            if last_vol == volume_pct and time_diff_ms < self._volume_debounce_ms:
                                _LOG.debug(
                                    "[%s] Zone %d: Ignoring duplicate volume %d%% (within %dms)",
                                    self.log_id,
                                    zone_num,
                                    volume_pct,
                                    self._volume_debounce_ms
                                )
                                return

                        self._last_volume_update[zone_num] = (volume_pct, current_time)

                        if entity_id:
                            _LOG.debug(
                                "[%s] Zone %d: Volume update %ddB → %d%%",
                                self.log_id,
                                zone_num,
                                volume_db,
                                volume_pct
                            )
                            self.events.emit(
                                DeviceEvents.UPDATE,
                                entity_id,
                                {
                                    MediaAttributes.VOLUME.value: volume_pct,
                                    MediaAttributes.STATE.value: state.get("power", False)
                                    and "ON"
                                    or "OFF",
                                },
                            )

                elif "MUT" in response:
                    muted = "1" in response
                    state["muted"] = muted

                    if entity_id:
                        self.events.emit(
                            DeviceEvents.UPDATE,
                            entity_id,
                            {
                                MediaAttributes.MUTED.value: muted,
                                MediaAttributes.STATE.value: state.get("power", False)
                                and "ON"
                                or "OFF",
                            },
                        )

                elif "INP" in response:
                    inp_match = re.search(r"INP(\d+)", response)
                    if inp_match:
                        input_num = int(inp_match.group(1))
                        state["input"] = input_num
                        input_name = self._input_names.get(
                            input_num, f"Input {input_num}"
                        )
                        state["input_name"] = input_name

                        if entity_id:
                            self.events.emit(
                                DeviceEvents.UPDATE,
                                entity_id,
                                {
                                    MediaAttributes.SOURCE.value: input_name,
                                    MediaAttributes.STATE.value: state.get("power", False)
                                    and "ON"
                                    or "OFF",
                                },
                            )

                # Sensor data parsing
                elif "AIF" in response:
                    # Audio Input Format (e.g., Z1AIFPCM, Z1AIFDolby Atmos)
                    format_match = re.search(r"AIF(.+)", response)
                    if format_match:
                        audio_format = format_match.group(1).strip()
                        state["audio_format"] = audio_format
                        sensor_id = f"sensor.{self.identifier}_audio_format"
                        self.events.emit(DeviceEvents.UPDATE, sensor_id, {
                            SensorAttributes.STATE.value: SensorStates.ON.value,
                            SensorAttributes.VALUE.value: audio_format
                        })

                elif "AIC" in response:
                    # Audio Input Channels (e.g., Z1AIC5.1, Z1AIC7.1.4)
                    channels_match = re.search(r"AIC(.+)", response)
                    if channels_match:
                        audio_channels = channels_match.group(1).strip()
                        state["audio_channels"] = audio_channels
                        sensor_id = f"sensor.{self.identifier}_audio_channels"
                        self.events.emit(DeviceEvents.UPDATE, sensor_id, {
                            SensorAttributes.STATE.value: SensorStates.ON.value,
                            SensorAttributes.VALUE.value: audio_channels
                        })

                elif "VIR" in response:
                    # Video Input Resolution (e.g., Z1VIR1080p, Z1VIR2160p60)
                    resolution_match = re.search(r"VIR(.+)", response)
                    if resolution_match:
                        video_resolution = resolution_match.group(1).strip()
                        state["video_resolution"] = video_resolution
                        sensor_id = f"sensor.{self.identifier}_video_resolution"
                        self.events.emit(DeviceEvents.UPDATE, sensor_id, {
                            SensorAttributes.STATE.value: SensorStates.ON.value,
                            SensorAttributes.VALUE.value: video_resolution
                        })

                elif "ALM" in response and "?" not in response:
                    # Audio Listening Mode (e.g., Z1ALM3 = Dolby Surround)
                    mode_match = re.search(r"ALM(\d+)", response)
                    if mode_match:
                        mode_num = int(mode_match.group(1))
                        listening_mode = self._get_listening_mode_name(mode_num)
                        state["listening_mode"] = listening_mode
                        sensor_id = f"sensor.{self.identifier}_listening_mode"
                        self.events.emit(DeviceEvents.UPDATE, sensor_id, {
                            SensorAttributes.STATE.value: SensorStates.ON.value,
                            SensorAttributes.VALUE.value: listening_mode
                        })

                elif "AIR" in response or "SRT" in response or "BDP" in response:
                    # Audio Input Rate/Sample Rate/Bit Depth
                    # (e.g., Z1AIR48kHz/24bit, Z1SRT48, Z1BDP24)
                    rate_info = response[response.find("Z") + 2:].strip()
                    if "AIR" in response:
                        rate_match = re.search(r"AIR(.+)", response)
                        if rate_match:
                            state["sample_rate"] = rate_match.group(1).strip()
                    elif "SRT" in response:
                        rate_match = re.search(r"SRT(\d+)", response)
                        if rate_match:
                            state["sample_rate"] = f"{rate_match.group(1)} kHz"
                    elif "BDP" in response:
                        depth_match = re.search(r"BDP(\d+)", response)
                        if depth_match:
                            current_rate = state.get("sample_rate", "")
                            state["sample_rate"] = f"{current_rate} / {depth_match.group(1)}-bit".strip(" /")

                    sensor_id = f"sensor.{self.identifier}_sample_rate"
                    from ucapi.sensor import Attributes as SensorAttributes, States as SensorStates
                    sample_rate_value = state.get("sample_rate", "Unknown")
                    self.events.emit(DeviceEvents.UPDATE, sensor_id, {
                        SensorAttributes.STATE.value: SensorStates.ON.value,
                        SensorAttributes.VALUE.value: sample_rate_value
                    })

    def _get_entity_id_for_zone(self, zone_num: int) -> str | None:
        """Get entity ID for a zone number."""
        if zone_num == 1:
            return f"media_player.{self.identifier}"
        return f"media_player.{self.identifier}.zone{zone_num}"

    def _get_listening_mode_name(self, mode_num: int) -> str:
        """Convert listening mode number to friendly name."""
        mode_names = {
            0: "None",
            1: "AnthemLogic Cinema",
            2: "AnthemLogic Music",
            3: "Dolby Surround",
            4: "DTS Neural:X",
            5: "Stereo",
            6: "Multi-Channel Stereo",
            7: "All-Channel Stereo",
            8: "PLIIx Movie",
            9: "PLIIx Music",
            10: "Neo:6 Cinema",
            11: "Neo:6 Music",
            12: "Dolby Digital",
            13: "DTS",
            14: "PCM Stereo",
            15: "Direct",
        }
        return mode_names.get(mode_num, f"Mode {mode_num}")

    async def _discover_input_names(self) -> None:
        """Query custom/virtual input names from receiver (supports up to 30 inputs)."""
        for input_num in range(1, self._input_count + 1):
            # Use ISiIN? format to query custom input name (i=01-30)
            await self._send_command(f"IS{input_num}IN?")
            await asyncio.sleep(0.05)

    async def power_on(self, zone: int = 1) -> bool:
        """Turn on the specified zone."""
        return await self._send_command(f"Z{zone}POW1")

    async def power_off(self, zone: int = 1) -> bool:
        """Turn off the specified zone."""
        return await self._send_command(f"Z{zone}POW0")

    async def set_volume(self, volume_db: int, zone: int = 1) -> bool:
        """Set volume in dB (-90 to 0)."""
        volume_db = max(-90, min(0, volume_db))
        return await self._send_command(f"Z{zone}VOL{volume_db}")

    async def volume_up(self, zone: int = 1) -> bool:
        """Increase volume by 1dB."""
        return await self._send_command(f"Z{zone}VUP")

    async def volume_down(self, zone: int = 1) -> bool:
        """Decrease volume by 1dB."""
        return await self._send_command(f"Z{zone}VDN")

    async def set_mute(self, muted: bool, zone: int = 1) -> bool:
        """Set mute state."""
        return await self._send_command(f"Z{zone}MUT{'1' if muted else '0'}")

    async def mute_toggle(self, zone: int = 1) -> bool:
        """Toggle mute state using native Anthem command."""
        return await self._send_command(f"Z{zone}MUTt")

    async def select_input(self, input_num: int, zone: int = 1) -> bool:
        """Select input source."""
        return await self._send_command(f"Z{zone}INP{input_num}")

    async def set_arc(self, enabled: bool, input_num: int = 1) -> bool:
        """Enable/disable Anthem Room Correction for input."""
        return await self._send_command(f"IS{input_num}ARC{'1' if enabled else '0'}")

    async def set_front_panel_brightness(self, brightness: int) -> bool:
        """Set front panel brightness (0-100%)."""
        brightness = max(0, min(100, brightness))
        return await self._send_command(f"GCFPB{brightness}")

    async def set_front_panel_display(self, mode: int) -> bool:
        """Set front panel display mode (0=All, 1=Volume only)."""
        mode = max(0, min(1, mode))
        return await self._send_command(f"GCFPDI{mode}")

    async def set_hdmi_standby_bypass(self, mode: int) -> bool:
        """Set HDMI standby bypass (0=Off, 1=Last Used, 2-8=HDMI 1-7)."""
        mode = max(0, min(8, mode))
        return await self._send_command(f"GCSHDMIB{mode}")

    async def set_cec_control(self, enabled: bool) -> bool:
        """Enable/disable CEC control."""
        return await self._send_command(f"GCCECC{'1' if enabled else '0'}")

    async def set_zone2_max_volume(self, volume_db: int) -> bool:
        """Set Zone 2 maximum volume (-40 to +10 dB)."""
        volume_db = max(-40, min(10, volume_db))
        return await self._send_command(f"GCZ2MMV{volume_db}")

    async def set_zone2_power_on_volume(self, volume_db: int | None) -> bool:
        """Set Zone 2 power-on volume (0=Last Used, or -90 to max volume)."""
        if volume_db is None or volume_db == 0:
            return await self._send_command("GCZ2POV0")
        volume_db = max(-90, min(10, volume_db))
        return await self._send_command(f"GCZ2POV{volume_db}")

    async def set_zone2_power_on_input(self, input_num: int) -> bool:
        """Set Zone 2 power-on input (0=Last Used, or input number)."""
        return await self._send_command(f"GCZ2POI{input_num}")

    async def speaker_level_up(self, channel: int, zone: int = 1) -> bool:
        """Increase speaker level by 0.5dB."""
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(f"Z{zone}LUP{channel_hex}")

    async def speaker_level_down(self, channel: int, zone: int = 1) -> bool:
        """Decrease speaker level by 0.5dB."""
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(f"Z{zone}LDN{channel_hex}")

    async def set_osd_info(self, mode: int) -> bool:
        """Set on-screen display info mode (0=Off, 1=16:9, 2=2.4:1)."""
        mode = max(0, min(2, mode))
        return await self._send_command(f"GCOSID{mode}")

    async def query_status(self, zone: int = 1) -> bool:
        """Query all status for a zone including sensor data."""
        commands = [
            f"Z{zone}POW?",
            f"Z{zone}VOL?",
            f"Z{zone}MUT?",
            f"Z{zone}INP?",
            f"Z{zone}AIF?",  # Audio format
            f"Z{zone}AIC?",  # Audio channels
            f"Z{zone}VIR?",  # Video resolution
            f"Z{zone}ALM?",  # Listening mode
            f"Z{zone}AIR?",  # Sample rate info
        ]
        for cmd in commands:
            await self._send_command(cmd)
            await asyncio.sleep(0.05)
        return True

    async def query_audio_info(self, zone: int = 1) -> bool:
        """Query audio format information."""
        commands = [
            f"Z{zone}AIF?",
            f"Z{zone}AIC?",
            f"Z{zone}SRT?",
            f"Z{zone}BDP?",
            f"Z{zone}AIN?",
            f"Z{zone}AIR?",
        ]
        for cmd in commands:
            await self._send_command(cmd)
            await asyncio.sleep(0.05)
        return True

    async def query_video_info(self, zone: int = 1) -> bool:
        """Query video format information."""
        commands = [f"Z{zone}VIR?", f"Z{zone}IRH?", f"Z{zone}IRV?"]
        for cmd in commands:
            await self._send_command(cmd)
            await asyncio.sleep(0.05)
        return True

    def get_input_list(self) -> list[str]:
        if self._device_config.discovered_inputs:
            _LOG.debug(
                "[%s] Using discovered inputs from config (%d sources)",
                self.log_id,
                len(self._device_config.discovered_inputs),
            )
            return self._device_config.discovered_inputs

        if self._input_names and self._input_count > 0:
            _LOG.debug(
                "[%s] Using runtime discovered inputs (%d sources)",
                self.log_id,
                self._input_count,
            )
            return [
                self._input_names.get(i, f"Input {i}")
                for i in range(1, self._input_count + 1)
            ]

        _LOG.debug("[%s] Using default input list (discovery incomplete)", self.log_id)
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

    def get_zone_state(self, zone: int) -> dict[str, Any]:
        """Get current state for a zone."""
        return self._zone_states.get(zone, {})
