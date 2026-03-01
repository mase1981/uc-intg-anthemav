"""
Anthem A/V Receiver device implementation using PersistentConnectionDevice.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from time import time
from functools import singledispatchmethod
from collections import defaultdict

from ucapi_framework import PersistentConnectionDevice, DeviceEvents
from ucapi.media_player import Attributes as MediaAttributes
from ucapi.sensor import Attributes as SensorAttributes, States as SensorStates

from .config import AnthemDeviceConfig
from . import const
from .models import (
    ParsedMessage,
    SystemModel,
    InputCount,
    InputName,
    ZonePower,
    ZoneVolume,
    ZoneMute,
    ZoneInput,
    ZoneAudioFormat,
    ZoneAudioChannels,
    ZoneVideoResolution,
    ZoneListeningMode,
    ZoneSampleRateInfo,
    ZoneSampleRate,
    ZoneBitDepth,
    ZoneState,
)
from .parser import parse_message

_LOG = logging.getLogger(__name__)


class AnthemDevice(PersistentConnectionDevice):
    def __init__(self, device_config: AnthemDeviceConfig, **kwargs):
        super().__init__(device_config, **kwargs)
        self._device_config = device_config
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        self._zone_states: dict[int, ZoneState] = defaultdict(ZoneState)
        self._input_names: dict[int, str] = {}
        self._input_count: int = 0
        self._model: str | None = None

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
        """Establish TCP connection to Anthem receiver."""
        _LOG.info(
            "[%s] Establishing TCP connection to %s:%d",
            self.log_id,
            self._device_config.host,
            self._device_config.port,
        )

        self._reader, self._writer = await asyncio.open_connection(
            self._device_config.host, self._device_config.port
        )

        await self._send_command(const.CMD_ECHO_OFF)
        await asyncio.sleep(0.1)
        await self._send_command(const.CMD_STANDBY_IP_CONTROL_ON)
        await asyncio.sleep(0.1)
        await self._send_command(const.CMD_MODEL_QUERY)
        await asyncio.sleep(0.1)
        await self._send_command(const.CMD_INPUT_COUNT_QUERY)
        await asyncio.sleep(0.2)

        for zone in self._device_config.zones:
            if zone.enabled:
                await self._send_command(
                    self._get_zone_command(zone.zone_number, const.CMD_POWER_QUERY)
                )
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

                while const.CMD_TERMINATOR in buffer:
                    line, buffer = buffer.split(const.CMD_TERMINATOR, 1)
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
            cmd_bytes = f"{command}{const.CMD_TERMINATOR}".encode("ascii")
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

        if response.startswith(const.RESP_ERROR_INVALID_COMMAND) or response.startswith(
            const.RESP_ERROR_EXECUTION_FAILED
        ):
            _LOG.warning("[%s] Device error: %s", self.log_id, response)
            return

        message = parse_message(response)
        if message:
            self._handle_message(message)

    @singledispatchmethod
    def _handle_message(self, message: ParsedMessage) -> None:
        """Handle parsed message."""
        _LOG.debug("[%s] Unhandled message type: %s", self.log_id, type(message))

    @_handle_message.register
    def _(self, message: SystemModel) -> None:
        self._model = message.model
        _LOG.info("[%s] Model: %s", self.log_id, message.model)
        model_sensor_id = f"sensor.{self.identifier}_model"
        self.events.emit(
            DeviceEvents.UPDATE,
            model_sensor_id,
            {
                SensorAttributes.STATE.value: SensorStates.ON.value,
                SensorAttributes.VALUE.value: message.model,
            },
        )

    @_handle_message.register
    def _(self, message: InputCount) -> None:
        self._input_count = message.count
        _LOG.info("[%s] Input count: %d", self.log_id, self._input_count)
        asyncio.create_task(self._discover_input_names())

    @_handle_message.register
    def _(self, message: InputName) -> None:
        self._input_names[message.input_number] = message.name
        _LOG.debug(
            "[%s] Input %d: %s", self.log_id, message.input_number, message.name
        )

        if len(self._input_names) == self._input_count:
            _LOG.info(
                "[%s] All %d inputs discovered, updating source lists",
                self.log_id,
                self._input_count,
            )
            source_list = self.get_input_list()

            for zone_config in self._device_config.zones:
                if zone_config.enabled:
                    entity_id = self._get_entity_id_for_zone(zone_config.zone_number)
                    if entity_id:
                        self.events.emit(
                            DeviceEvents.UPDATE,
                            entity_id,
                            {MediaAttributes.SOURCE_LIST.value: source_list},
                        )

    @_handle_message.register
    def _(self, message: ZonePower) -> None:
        zone = self._zone_states[message.zone]
        zone.power = message.is_on
        new_state = "ON" if message.is_on else "OFF"

        entity_id = self._get_entity_id_for_zone(message.zone)
        if entity_id:
            self.events.emit(
                DeviceEvents.UPDATE,
                entity_id,
                {MediaAttributes.STATE.value: new_state},
            )

    @_handle_message.register
    def _(self, message: ZoneVolume) -> None:
        if message.volume_db < -90 or message.volume_db > 0:
            _LOG.warning(
                "[%s] Invalid volume dB value: %d (must be -90 to 0), ignoring",
                self.log_id,
                message.volume_db,
            )
            return

        zone = self._zone_states[message.zone]
        zone.volume_db = message.volume_db
        volume_pct = int(((message.volume_db + 90) / 90) * 100)
        volume_pct = max(0, min(100, volume_pct))

        current_time = time()
        if message.zone in self._last_volume_update:
            last_vol, last_time = self._last_volume_update[message.zone]
            time_diff_ms = (current_time - last_time) * 1000

            if last_vol == volume_pct and time_diff_ms < self._volume_debounce_ms:
                _LOG.debug(
                    "[%s] Zone %d: Ignoring duplicate volume %d%% (within %dms)",
                    self.log_id,
                    message.zone,
                    volume_pct,
                    self._volume_debounce_ms,
                )
                return

        self._last_volume_update[message.zone] = (volume_pct, current_time)

        entity_id = self._get_entity_id_for_zone(message.zone)
        if entity_id:
            _LOG.debug(
                "[%s] Zone %d: Volume update %ddB → %d%%",
                self.log_id,
                message.zone,
                message.volume_db,
                volume_pct,
            )
            self.events.emit(
                DeviceEvents.UPDATE,
                entity_id,
                {
                    MediaAttributes.VOLUME.value: volume_pct,
                    MediaAttributes.STATE.value: "ON" if zone.power else "OFF",
                },
            )

        if self._is_sensor_zone(message.zone):
            sensor_id = f"sensor.{self.identifier}_volume"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: str(message.volume_db),
                },
            )

    @_handle_message.register
    def _(self, message: ZoneMute) -> None:
        zone = self._zone_states[message.zone]
        zone.muted = message.is_muted

        entity_id = self._get_entity_id_for_zone(message.zone)
        if entity_id:
            self.events.emit(
                DeviceEvents.UPDATE,
                entity_id,
                {
                    MediaAttributes.MUTED.value: message.is_muted,
                    MediaAttributes.STATE.value: "ON" if zone.power else "OFF",
                },
            )

    @_handle_message.register
    def _(self, message: ZoneInput) -> None:
        zone = self._zone_states[message.zone]
        zone.input_number = message.input_number
        zone.input_name = self._input_names.get(
            message.input_number, f"Input {message.input_number}"
        )

        entity_id = self._get_entity_id_for_zone(message.zone)
        if entity_id:
            self.events.emit(
                DeviceEvents.UPDATE,
                entity_id,
                {
                    MediaAttributes.SOURCE.value: zone.input_name,
                    MediaAttributes.STATE.value: "ON" if zone.power else "OFF",
                },
            )

    @_handle_message.register
    def _(self, message: ZoneAudioFormat) -> None:
        zone = self._zone_states[message.zone]
        zone.audio_format = message.format
        if self._is_sensor_zone(message.zone):
            sensor_id = f"sensor.{self.identifier}_audio_format"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: message.format,
                },
            )

    @_handle_message.register
    def _(self, message: ZoneAudioChannels) -> None:
        zone = self._zone_states[message.zone]
        zone.audio_channels = message.channels
        if self._is_sensor_zone(message.zone):
            sensor_id = f"sensor.{self.identifier}_audio_channels"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: message.channels,
                },
            )

    @_handle_message.register
    def _(self, message: ZoneVideoResolution) -> None:
        zone = self._zone_states[message.zone]
        zone.video_resolution = message.resolution
        if self._is_sensor_zone(message.zone):
            sensor_id = f"sensor.{self.identifier}_video_resolution"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: message.resolution,
                },
            )

    @_handle_message.register
    def _(self, message: ZoneListeningMode) -> None:
        zone = self._zone_states[message.zone]
        zone.listening_mode = message.mode_name
        if self._is_sensor_zone(message.zone):
            sensor_id = f"sensor.{self.identifier}_listening_mode"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: message.mode_name,
                },
            )

    @_handle_message.register
    def _(self, message: ZoneSampleRateInfo) -> None:
        zone = self._zone_states[message.zone]
        zone.sample_rate = message.info
        self._emit_sample_rate_update(message.zone, message.info)

    @_handle_message.register
    def _(self, message: ZoneSampleRate) -> None:
        zone = self._zone_states[message.zone]
        zone.sample_rate = f"{message.rate_khz} kHz"
        self._emit_sample_rate_update(message.zone, zone.sample_rate)

    @_handle_message.register
    def _(self, message: ZoneBitDepth) -> None:
        zone = self._zone_states[message.zone]
        current_rate = zone.sample_rate if zone.sample_rate != "Unknown" else ""
        zone.sample_rate = f"{current_rate} / {message.depth}-bit".strip(" /")
        self._emit_sample_rate_update(message.zone, zone.sample_rate)

    def _emit_sample_rate_update(self, zone_num: int, value: str) -> None:
        if self._is_sensor_zone(zone_num):
            sensor_id = f"sensor.{self.identifier}_sample_rate"
            self.events.emit(
                DeviceEvents.UPDATE,
                sensor_id,
                {
                    SensorAttributes.STATE.value: SensorStates.ON.value,
                    SensorAttributes.VALUE.value: value,
                },
            )

    def _is_sensor_zone(self, zone_num: int) -> bool:
        """Check if the given zone should emit sensor updates (Zone 1 only)."""
        return zone_num == 1

    def _get_entity_id_for_zone(self, zone_num: int) -> str | None:
        """Get entity ID for a zone number."""
        if zone_num == 1:
            return f"media_player.{self.identifier}"
        return f"media_player.{self.identifier}.zone{zone_num}"

    def _get_zone_command(self, zone: int, command: str, value: Any = "") -> str:
        """Construct a zone-specific command string."""
        return f"{const.CMD_ZONE_PREFIX}{zone}{command}{value}"

    def _requires_volume_suffix(self) -> bool:
        """
        Determine if this model requires '01' suffix for volume up/down commands.
        MRX-series models require Z1VUP01/Z1VDN01 format.
        """
        if not self._model:
            return False
        return "MRX" in self._model.upper()

    def _uses_isn_format(self) -> bool:
        """
        Determine if this model uses ISN/ILN format for input name queries.
        MRX x20 series (MRX 520, 720, 1120) and AVM 60 use ISNyy?/ILNyy? format.
        Older models (MRX 540, 740, 1140, AVM 70/90) use ISiIN? format.
        """
        if not self._model:
            return False

        model_upper = self._model.upper()
        if "AVM 60" in model_upper or "AVM60" in model_upper:
            return True
        if "MRX" in model_upper:
            for suffix in ["520", "720", "1120"]:
                if suffix in model_upper:
                    return True
        return False

    async def _discover_input_names(self) -> None:
        """Query custom/virtual input names from receiver."""
        use_isn = self._uses_isn_format()
        _LOG.debug(
            "[%s] Input discovery using %s format",
            self.log_id,
            "ISN" if use_isn else "ISiIN",
        )

        for input_num in range(1, self._input_count + 1):
            if use_isn:
                cmd = f"{const.CMD_INPUT_SHORT_NAME_PREFIX}{input_num:02d}?"
            else:
                cmd = f"{const.CMD_INPUT_SETTING_PREFIX}{input_num}{const.CMD_INPUT_NAME_QUERY_SUFFIX}"
            await self._send_command(cmd)
            await asyncio.sleep(0.05)

    async def power_on(self, zone: int = 1) -> bool:
        """Turn on the specified zone."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_POWER, const.VAL_ON)
        )

    async def power_off(self, zone: int = 1) -> bool:
        """Turn off the specified zone."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_POWER, const.VAL_OFF)
        )

    async def set_volume(self, volume_db: int, zone: int = 1) -> bool:
        """Set volume in dB (-90 to 0)."""
        volume_db = max(-90, min(0, volume_db))
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME, volume_db)
        )

    async def volume_up(self, zone: int = 1) -> bool:
        """Increase volume by 1dB."""
        suffix = "01" if self._requires_volume_suffix() else ""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_UP, suffix)
        )

    async def volume_down(self, zone: int = 1) -> bool:
        """Decrease volume by 1dB."""
        suffix = "01" if self._requires_volume_suffix() else ""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_DOWN, suffix)
        )

    async def set_mute(self, muted: bool, zone: int = 1) -> bool:
        """Set mute state."""
        return await self._send_command(
            self._get_zone_command(
                zone, const.CMD_MUTE, const.VAL_ON if muted else const.VAL_OFF
            )
        )

    async def mute_toggle(self, zone: int = 1) -> bool:
        """Toggle mute state using native Anthem command."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_MUTE, const.VAL_TOGGLE)
        )

    async def select_input(self, input_num: int, zone: int = 1) -> bool:
        """Select input source."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_INPUT, input_num)
        )

    async def set_arc(self, enabled: bool, input_num: int = 1) -> bool:
        """Enable/disable Anthem Room Correction for input."""
        return await self._send_command(
            f"{const.CMD_INPUT_SETTING_PREFIX}{input_num}{const.CMD_ARC_SETTING_SUFFIX}{const.VAL_ON if enabled else const.VAL_OFF}"
        )

    async def set_front_panel_brightness(self, brightness: int) -> bool:
        """Set front panel brightness (0-100%)."""
        brightness = max(0, min(100, brightness))
        return await self._send_command(f"{const.CMD_FRONT_PANEL_BRIGHTNESS}{brightness}")

    async def set_front_panel_display(self, mode: int) -> bool:
        """Set front panel display mode (0=All, 1=Volume only)."""
        mode = max(0, min(1, mode))
        return await self._send_command(f"{const.CMD_FRONT_PANEL_DISPLAY_INFO}{mode}")

    async def set_hdmi_standby_bypass(self, mode: int) -> bool:
        """Set HDMI standby bypass (0=Off, 1=Last Used, 2-8=HDMI 1-7)."""
        mode = max(0, min(8, mode))
        return await self._send_command(f"{const.CMD_HDMI_STANDBY_BYPASS}{mode}")

    async def set_cec_control(self, enabled: bool) -> bool:
        """Enable/disable CEC control."""
        return await self._send_command(
            f"{const.CMD_CEC_CONTROL}{const.VAL_ON if enabled else const.VAL_OFF}"
        )

    async def set_zone2_max_volume(self, volume_db: int) -> bool:
        """Set Zone 2 maximum volume (-40 to +10 dB)."""
        volume_db = max(-40, min(10, volume_db))
        return await self._send_command(f"{const.CMD_ZONE2_MAX_VOL}{volume_db}")

    async def set_zone2_power_on_volume(self, volume_db: int | None) -> bool:
        """Set Zone 2 power-on volume (0=Last Used, or -90 to max volume)."""
        if volume_db is None or volume_db == 0:
            return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_VOL}0")
        volume_db = max(-90, min(10, volume_db))
        return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_VOL}{volume_db}")

    async def set_zone2_power_on_input(self, input_num: int) -> bool:
        """Set Zone 2 power-on input (0=Last Used, or input number)."""
        return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_INPUT}{input_num}")

    async def speaker_level_up(self, channel: int, zone: int = 1) -> bool:
        """Increase speaker level by 0.5dB."""
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_LEVEL_UP, channel_hex)
        )

    async def speaker_level_down(self, channel: int, zone: int = 1) -> bool:
        """Decrease speaker level by 0.5dB."""
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_LEVEL_DOWN, channel_hex)
        )

    async def set_osd_info(self, mode: int) -> bool:
        """Set on-screen display info mode (0=Off, 1=16:9, 2=2.4:1)."""
        mode = max(0, min(2, mode))
        return await self._send_command(f"{const.CMD_OSD_INFO}{mode}")

    async def query_status(self, zone: int = 1) -> bool:
        """Query all status for a zone including sensor data."""
        queries = [
            const.CMD_POWER_QUERY,
            const.CMD_VOLUME_QUERY,
            const.CMD_MUTE_QUERY,
            const.CMD_INPUT_QUERY,
            const.CMD_AUDIO_FORMAT_QUERY,
            const.CMD_AUDIO_CHANNELS_QUERY,
            const.CMD_VIDEO_RESOLUTION_QUERY,
            const.CMD_LISTENING_MODE_QUERY,
            const.CMD_AUDIO_SAMPLE_RATE_QUERY,
        ]
        for q in queries:
            await self._send_command(self._get_zone_command(zone, q))
            await asyncio.sleep(0.05)
        return True

    async def query_audio_info(self, zone: int = 1) -> bool:
        """Query audio format information."""
        queries = [
            const.CMD_AUDIO_FORMAT_QUERY,
            const.CMD_AUDIO_CHANNELS_QUERY,
            const.CMD_AUDIO_SAMPLE_RATE_KHZ_QUERY,
            const.CMD_AUDIO_BIT_DEPTH_QUERY,
            const.CMD_AUDIO_INPUT_NAME_QUERY,
            const.CMD_AUDIO_SAMPLE_RATE_QUERY,
        ]
        for q in queries:
            await self._send_command(self._get_zone_command(zone, q))
            await asyncio.sleep(0.05)
        return True

    async def query_video_info(self, zone: int = 1) -> bool:
        """Query video format information."""
        queries = [
            const.CMD_VIDEO_RESOLUTION_QUERY,
            const.CMD_VIDEO_HORIZ_RES_QUERY,
            const.CMD_VIDEO_VERT_RES_QUERY,
        ]
        for q in queries:
            await self._send_command(self._get_zone_command(zone, q))
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
        return const.DEFAULT_INPUT_LIST

    def get_input_number_by_name(self, name: str) -> int | None:
        """Get input number by name."""
        for num, inp_name in self._input_names.items():
            if inp_name == name:
                return num

        if self._device_config.discovered_inputs:
            try:
                index = self._device_config.discovered_inputs.index(name)
                return index + 1
            except ValueError:
                pass

        return const.DEFAULT_INPUT_MAP.get(name)

    def get_zone_state(self, zone: int) -> ZoneState:
        """Get current state for a zone."""
        return self._zone_states[zone]
