"""
Anthem A/V Receiver device implementation using PersistentConnectionDevice.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from functools import singledispatchmethod
from collections import defaultdict

from ucapi_framework import PersistentConnectionDevice

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav import const
from uc_intg_anthemav.models import (
    ParsedMessage,
    SystemModel,
    InputCount,
    InputName,
    ZonePower,
    ZoneVolume,
    ZoneVolumePercent,
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
from uc_intg_anthemav.parser import parse_message

_LOG = logging.getLogger(__name__)


_VOLUME_DISPLAY_OFFSET = 55


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
        self._sensor_poll_tasks: dict[int, asyncio.Task] = {}

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

        if self._device_config.is_x20_series:
            await self._send_command(const.CMD_ECHO_ON)
            await asyncio.sleep(0.05)
            await self._send_command(const.CMD_STANDBY_IP_CONTROL_ON)
        elif self._device_config.is_x40_series:
            await self._send_command(const.CMD_TX_STATUS_IP)
            await asyncio.sleep(0.05)
            await self._send_command(const.CMD_CONNECTED_STANDBY_ON)
        else:
            _LOG.warning(
                "[%s] Unknown series for model '%s' - trying x40 commands",
                self.log_id,
                self._device_config.discovered_model,
            )
            await self._send_command(const.CMD_TX_STATUS_IP)
            await asyncio.sleep(0.05)
            await self._send_command(const.CMD_CONNECTED_STANDBY_ON)
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
                await self._send_command(
                    self._get_zone_command(zone.zone_number, const.CMD_LISTENING_MODE_QUERY)
                )
                await asyncio.sleep(0.05)

        await self._read_initial_responses(timeout=2.0)
        _LOG.info("[%s] Connection established and initialized", self.log_id)
        return (self._reader, self._writer)

    async def _read_initial_responses(self, timeout: float = 2.0) -> None:
        """Read and process initial responses to bootstrap device state."""
        if not self._reader:
            return

        buffer = ""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout

        while loop.time() < deadline:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                data = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=min(remaining, 0.5),
                )
                if not data:
                    break
                buffer += data.decode("ascii", errors="ignore")
                while const.CMD_TERMINATOR in buffer:
                    line, buffer = buffer.split(const.CMD_TERMINATOR, 1)
                    line = line.strip()
                    if line:
                        await self._process_response(line)
            except asyncio.TimeoutError:
                break

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

        if response.startswith("!R"):
            _LOG.warning("[%s] Out-of-range parameter: %s", self.log_id, response)
            return

        if response.startswith("!Z"):
            _LOG.warning("[%s] Zone is off: %s", self.log_id, response)
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
        self._device_config.discovered_model = message.model
        _LOG.info("[%s] Model: %s", self.log_id, message.model)
        if not self._is_model_x20(message.model) and not self._is_model_x40(message.model):
            _LOG.warning(
                "[%s] Unrecognized model '%s' - defaulting to x40 protocol. "
                "Commands may not work correctly.",
                self.log_id,
                message.model,
            )
        self.push_update()

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
                "[%s] All %d inputs discovered",
                self.log_id,
                self._input_count,
            )
            self.push_update()

    @_handle_message.register
    def _(self, message: ZonePower) -> None:
        zone = self._zone_states[message.zone]
        if zone.power is not None and message.is_on == zone.power:
            return
        zone.power = message.is_on
        self.push_update()

        if message.is_on:
            asyncio.create_task(self._query_zone_on_power_on(message.zone))
        else:
            # Cancel sensor polling when zone powers off
            task = self._sensor_poll_tasks.pop(message.zone, None)
            if task:
                task.cancel()

    async def _query_zone_on_power_on(self, zone: int) -> None:
        await asyncio.sleep(2.0)
        _LOG.debug("[%s] Querying zone %d state after power on", self.log_id, zone)
        await self.query_status(zone)
        # Start sensor polling - receiver doesn't push AIF/AIC/VIR updates
        self._start_sensor_poll(zone)

    async def _query_after_input_change(self, zone: int) -> None:
        await asyncio.sleep(2.0)
        _LOG.debug("[%s] Querying zone %d audio/video after input change", self.log_id, zone)
        await self.query_audio_info(zone)
        await self.query_video_info(zone)

    def _start_sensor_poll(self, zone: int) -> None:
        """Start periodic polling for audio/video sensor data."""
        old_task = self._sensor_poll_tasks.pop(zone, None)
        if old_task:
            old_task.cancel()
        self._sensor_poll_tasks[zone] = asyncio.create_task(
            self._poll_sensor_data(zone)
        )

    async def _poll_sensor_data(self, zone: int) -> None:
        """Poll audio/video sensors periodically while zone is on.

        The receiver does not push AIF/AIC/VIR updates unsolicited.
        Confirmed by Anthem technical support.
        Only polls AIF, AIC, VIR — avoids IRH/IRV which can trigger OSD.
        """
        poll_queries = [
            const.CMD_AUDIO_FORMAT_QUERY,
            const.CMD_AUDIO_CHANNELS_QUERY,
            const.CMD_VIDEO_RESOLUTION_QUERY,
        ]
        while True:
            state = self._zone_states[zone]
            if not state.power:
                _LOG.debug("[%s] Zone %d powered off, stopping sensor poll", self.log_id, zone)
                return
            await asyncio.sleep(5)
            state = self._zone_states[zone]
            if not state.power:
                return
            for q in poll_queries:
                await self._send_command(self._get_zone_command(zone, q))
                await asyncio.sleep(0.05)

    @_handle_message.register
    def _(self, message: ZoneVolume) -> None:
        volume_db = message.volume_db

        if volume_db > 0 and self._has_volume_display_offset:
            volume_db = volume_db - _VOLUME_DISPLAY_OFFSET

        if volume_db < -90 or volume_db > 10:
            _LOG.warning(
                "[%s] Invalid volume value: %d, ignoring",
                self.log_id,
                message.volume_db,
            )
            return

        zone = self._zone_states[message.zone]
        if zone.volume_db is not None and volume_db == zone.volume_db:
            return
        zone.volume_db = volume_db
        _LOG.debug(
            "[%s] Zone %d: Volume update %ddB",
            self.log_id,
            message.zone,
            volume_db,
        )
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneVolumePercent) -> None:
        zone = self._zone_states[message.zone]
        pct = max(0, min(100, message.volume_pct))
        if zone.volume_pct is not None and pct == zone.volume_pct:
            return
        zone.volume_pct = pct
        _LOG.debug(
            "[%s] Zone %d: Volume percent update %d%%",
            self.log_id, message.zone, pct,
        )
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneMute) -> None:
        zone = self._zone_states[message.zone]
        if zone.muted is not None and message.is_muted == zone.muted:
            return
        zone.muted = message.is_muted
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneInput) -> None:
        zone = self._zone_states[message.zone]
        if zone.input_number is not None and message.input_number == zone.input_number:
            return
        zone.input_number = message.input_number
        zone.input_name = self._input_names.get(
            message.input_number, f"Input {message.input_number}"
        )
        self.push_update()
        if zone.power:
            asyncio.create_task(self._query_after_input_change(message.zone))

    @_handle_message.register
    def _(self, message: ZoneAudioFormat) -> None:
        zone = self._zone_states[message.zone]
        fmt_map = const.AUDIO_FORMAT_NAMES if self.is_x20_series else const.AUDIO_FORMAT_NAMES_X40
        decoded = fmt_map.get(message.format, message.format)
        if decoded == zone.audio_format:
            return
        zone.audio_format = decoded
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneAudioChannels) -> None:
        zone = self._zone_states[message.zone]
        ch_map = const.AUDIO_CHANNELS_NAMES if self.is_x20_series else const.AUDIO_CHANNELS_NAMES_X40
        decoded = ch_map.get(message.channels, message.channels)
        if decoded == zone.audio_channels:
            return
        zone.audio_channels = decoded
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneVideoResolution) -> None:
        zone = self._zone_states[message.zone]
        res_map = const.VIDEO_RESOLUTION_NAMES if self.is_x20_series else const.VIDEO_RESOLUTION_NAMES_X40
        decoded = res_map.get(message.resolution, message.resolution)
        if decoded == zone.video_resolution:
            return
        zone.video_resolution = decoded
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneListeningMode) -> None:
        zone = self._zone_states[message.zone]
        if self.is_x20_series:
            mode_map = const.LISTENING_MODES_X20
        else:
            mode_map = const.LISTENING_MODES_X40
        mode_name = mode_map.get(
            message.mode_number, f"Mode {message.mode_number}"
        )
        if mode_name == zone.listening_mode:
            return
        zone.listening_mode = mode_name
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneSampleRateInfo) -> None:
        zone = self._zone_states[message.zone]
        if message.info == zone.sample_rate:
            return
        zone.sample_rate = message.info
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneSampleRate) -> None:
        zone = self._zone_states[message.zone]
        new_rate = f"{message.rate_khz} kHz"
        if new_rate == zone.sample_rate:
            return
        zone.sample_rate = new_rate
        self.push_update()

    @_handle_message.register
    def _(self, message: ZoneBitDepth) -> None:
        zone = self._zone_states[message.zone]
        current_rate = zone.sample_rate if zone.sample_rate != "Unknown" else ""
        new_rate = f"{current_rate} / {message.depth}-bit".strip(" /")
        if new_rate == zone.sample_rate:
            return
        zone.sample_rate = new_rate
        self.push_update()

    @property
    def _has_volume_display_offset(self) -> bool:
        if not self._model:
            return False
        model_upper = self._model.upper()
        return "MRX" in model_upper and "540" in model_upper

    @property
    def is_x20_series(self) -> bool:
        if self._model:
            return self._is_model_x20(self._model)
        return self._device_config.is_x20_series

    @property
    def is_x40_series(self) -> bool:
        if self._model:
            return self._is_model_x40(self._model)
        return self._device_config.is_x40_series

    @staticmethod
    def _is_model_x20(model: str) -> bool:
        # TODO: Fragile substring matching — should match exact IDM? model strings.
        # Known x20 models: MRX 520, MRX 720, MRX 1120, AVM 60
        model_upper = model.upper()
        if "AVM 60" in model_upper or "AVM60" in model_upper:
            return True
        if "MRX" in model_upper:
            for suffix in ["520", "720", "1120"]:
                if suffix in model_upper:
                    return True
        return False

    @staticmethod
    def _is_model_x40(model: str) -> bool:
        # TODO: Fragile substring matching — should match exact IDM? model strings.
        # Known x40 models: MRX 540, MRX 740, MRX 1140, AVM 70, AVM 90
        model_upper = model.upper()
        if any(s in model_upper for s in ["AVM 70", "AVM70", "AVM 90", "AVM90"]):
            return True
        if "MRX" in model_upper:
            for suffix in ["540", "740", "1140"]:
                if suffix in model_upper:
                    return True
        return False

    async def _discover_input_names(self) -> None:
        """Query custom/virtual input names from receiver."""
        use_isn = self.is_x20_series
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

    def get_sensor_value(self, key: str) -> str | None:
        """Get sensor value by key from Zone 1 state."""
        if key == "model":
            return self._model
        zone = self._zone_states[1]
        mapping = {
            "volume": str(zone.volume_db) if zone.volume_db is not None else None,
            "audio_format": zone.audio_format if zone.audio_format != "Unknown" else None,
            "audio_channels": zone.audio_channels if zone.audio_channels != "Unknown" else None,
            "video_resolution": zone.video_resolution if zone.video_resolution != "Unknown" else None,
            "listening_mode": zone.listening_mode if zone.listening_mode != "Unknown" else None,
            "sample_rate": zone.sample_rate if zone.sample_rate != "Unknown" else None,
        }
        return mapping.get(key)

    async def power_on(self, zone: int = 1) -> bool:
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_POWER, const.VAL_ON)
        )

    async def power_off(self, zone: int = 1) -> bool:
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_POWER, const.VAL_OFF)
        )

    async def set_volume(self, volume_db: int, zone: int = 1) -> bool:
        volume_db = max(-90, min(10, volume_db))
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME, volume_db)
        )

    async def volume_up(self, zone: int = 1) -> bool:
        suffix = "01" if self._requires_volume_suffix() else ""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_UP, suffix)
        )

    async def volume_down(self, zone: int = 1) -> bool:
        suffix = "01" if self._requires_volume_suffix() else ""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_DOWN, suffix)
        )

    async def set_volume_percent(self, percent: int, zone: int = 1) -> bool:
        """Set volume as percentage (x40 series only)."""
        percent = max(0, min(100, percent))
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_PERCENT, percent)
        )

    async def volume_up_percent(self, zone: int = 1) -> bool:
        """Volume up by 1% (x40 series only)."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_PERCENT_UP)
        )

    async def volume_down_percent(self, zone: int = 1) -> bool:
        """Volume down by 1% (x40 series only)."""
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_VOLUME_PERCENT_DOWN)
        )

    async def set_mute(self, muted: bool, zone: int = 1) -> bool:
        return await self._send_command(
            self._get_zone_command(
                zone, const.CMD_MUTE, const.VAL_ON if muted else const.VAL_OFF
            )
        )

    async def mute_toggle(self, zone: int = 1) -> bool:
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_MUTE, const.VAL_TOGGLE)
        )

    async def select_input(self, input_num: int, zone: int = 1) -> bool:
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_INPUT, input_num)
        )

    async def set_arc(self, enabled: bool, input_num: int = 1) -> bool:
        val = const.VAL_ON if enabled else const.VAL_OFF
        if self.is_x20_series:
            return await self._send_command(f"{const.CMD_ARC_X20}{val}")
        return await self._send_command(
            f"{const.CMD_INPUT_SETTING_PREFIX}{input_num}{const.CMD_ARC_SETTING_SUFFIX}{val}"
        )

    async def set_front_panel_brightness(self, brightness: int) -> bool:
        if self.is_x20_series:
            brightness = max(0, min(3, brightness))
            return await self._send_command(
                f"{const.CMD_FRONT_PANEL_BRIGHTNESS_X20}{brightness}"
            )
        brightness = max(0, min(100, brightness))
        return await self._send_command(f"{const.CMD_FRONT_PANEL_BRIGHTNESS}{brightness}")

    async def set_front_panel_display(self, mode: int) -> bool:
        if self.is_x20_series:
            _LOG.debug("[%s] Display mode not supported on x20 series", self.log_id)
            return False
        mode = max(0, min(1, mode))
        return await self._send_command(f"{const.CMD_FRONT_PANEL_DISPLAY_INFO}{mode}")

    async def set_hdmi_standby_bypass(self, mode: int) -> bool:
        mode = max(0, min(8, mode))
        return await self._send_command(f"{const.CMD_HDMI_STANDBY_BYPASS}{mode}")

    async def set_cec_control(self, enabled: bool) -> bool:
        return await self._send_command(
            f"{const.CMD_CEC_CONTROL}{const.VAL_ON if enabled else const.VAL_OFF}"
        )

    async def set_zone2_max_volume(self, volume_db: int) -> bool:
        volume_db = max(-40, min(10, volume_db))
        return await self._send_command(f"{const.CMD_ZONE2_MAX_VOL}{volume_db}")

    async def set_zone2_power_on_volume(self, volume_db: int | None) -> bool:
        if volume_db is None or volume_db == 0:
            return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_VOL}0")
        volume_db = max(-90, min(10, volume_db))
        return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_VOL}{volume_db}")

    async def set_zone2_power_on_input(self, input_num: int) -> bool:
        return await self._send_command(f"{const.CMD_ZONE2_POWER_ON_INPUT}{input_num}")

    async def speaker_level_up(self, channel: int, zone: int = 1, step: int = 1) -> bool:
        if self.is_x20_series:
            return await self._send_command(
                self._get_zone_command(
                    zone, const.CMD_LEVEL_UP, f"{channel}{step:02d}"
                )
            )
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_LEVEL_UP, channel_hex)
        )

    async def speaker_level_down(self, channel: int, zone: int = 1, step: int = 1) -> bool:
        if self.is_x20_series:
            return await self._send_command(
                self._get_zone_command(
                    zone, const.CMD_LEVEL_DOWN, f"{channel}{step:02d}"
                )
            )
        channel_hex = hex(channel)[2:].upper()
        return await self._send_command(
            self._get_zone_command(zone, const.CMD_LEVEL_DOWN, channel_hex)
        )

    async def set_osd_info(self, mode: int) -> bool:
        if self.is_x20_series:
            _LOG.debug("[%s] OSD info not supported on x20 series", self.log_id)
            return False
        mode = max(0, min(2, mode))
        return await self._send_command(f"{const.CMD_OSD_INFO}{mode}")

    async def query_volume(self, zone: int = 1) -> bool:
        await asyncio.sleep(0.1)
        await self._send_command(self._get_zone_command(zone, const.CMD_VOLUME_QUERY))
        await asyncio.sleep(0.05)
        if not self.is_x20_series:
            await self._send_command(self._get_zone_command(zone, const.CMD_VOLUME_PERCENT_QUERY))
            await asyncio.sleep(0.05)
        await self._send_command(self._get_zone_command(zone, const.CMD_MUTE_QUERY))
        return True

    async def query_status(self, zone: int = 1) -> bool:
        queries = [
            const.CMD_POWER_QUERY,
            const.CMD_VOLUME_QUERY,
            const.CMD_MUTE_QUERY,
            const.CMD_INPUT_QUERY,
            const.CMD_LISTENING_MODE_QUERY,
            const.CMD_AUDIO_FORMAT_QUERY,
            const.CMD_AUDIO_CHANNELS_QUERY,
            const.CMD_VIDEO_RESOLUTION_QUERY,
            const.CMD_AUDIO_SAMPLE_RATE_QUERY,
        ]
        if not self.is_x20_series:
            queries.insert(2, const.CMD_VOLUME_PERCENT_QUERY)
        for q in queries:
            await self._send_command(self._get_zone_command(zone, q))
            await asyncio.sleep(0.05)
        return True

    async def query_audio_info(self, zone: int = 1) -> bool:
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
            return self._device_config.discovered_inputs

        if self._input_names and self._input_count > 0:
            return [
                self._input_names.get(i, f"Input {i}")
                for i in range(1, self._input_count + 1)
            ]

        return const.DEFAULT_INPUT_LIST

    def get_input_number_by_name(self, name: str) -> int | None:
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
        return self._zone_states[zone]

    def _get_zone_command(self, zone: int, command: str, value: Any = "") -> str:
        return f"{const.CMD_ZONE_PREFIX}{zone}{command}{value}"

    def _requires_volume_suffix(self) -> bool:
        return False
