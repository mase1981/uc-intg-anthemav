"""
Anthem A/V message parser.

Centralized parsing of protocol responses into typed message objects.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import re
from typing import Optional

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
)
from . import const


def parse_message(response: str) -> Optional[ParsedMessage]:
    """Parse a raw response string from the Anthem receiver."""
    if not response:
        return None

    # Error responses (ignored for state updates)
    if response.startswith(const.RESP_ERROR_INVALID_COMMAND) or response.startswith(
        const.RESP_ERROR_EXECUTION_FAILED
    ):
        return None

    # System Messages
    if response.startswith(const.RESP_MODEL):
        return SystemModel(model=response[len(const.RESP_MODEL) :].strip())

    icn_match = re.match(rf"{const.RESP_INPUT_COUNT}(\d+)", response)
    if icn_match:
        return InputCount(count=int(icn_match.group(1)))

    # Input name responses - ISNyyname format (MRX x20/AVM 60 models)
    isn_match = re.match(rf"{const.RESP_INPUT_SHORT_NAME}(\d{{2}})(.+)", response)
    if isn_match:
        return InputName(
            input_number=int(isn_match.group(1)), name=isn_match.group(2).strip()
        )

    # Input name responses - ISiINname format (older models)
    is_match = re.match(
        rf"{const.RESP_INPUT_SETTING}(\d{{1,2}}){const.RESP_INPUT_NAME}(.+)", response
    )
    if is_match:
        return InputName(
            input_number=int(is_match.group(1)), name=is_match.group(2).strip()
        )

    # Zone Messages - Matches Z<zone><command>
    zone_match = re.match(rf"{const.RESP_ZONE_PREFIX}(\d+)(.+)", response)
    if zone_match:
        zone_num = int(zone_match.group(1))
        payload = zone_match.group(2)

        if const.RESP_POWER in payload:
            return ZonePower(zone=zone_num, is_on=const.VAL_ON in payload)

        if const.RESP_VOLUME in payload:
            vol_match = re.search(rf"{const.RESP_VOLUME}(-?\d+)", payload)
            if vol_match:
                return ZoneVolume(zone=zone_num, volume_db=int(vol_match.group(1)))

        if const.RESP_MUTE in payload:
            return ZoneMute(zone=zone_num, is_muted=const.VAL_ON in payload)

        if const.RESP_INPUT in payload:
            inp_match = re.search(rf"{const.RESP_INPUT}(\d+)", payload)
            if inp_match:
                return ZoneInput(zone=zone_num, input_number=int(inp_match.group(1)))

        # Sensor data
        if const.RESP_AUDIO_FORMAT in payload:
            format_match = re.search(rf"{const.RESP_AUDIO_FORMAT}(.+)", payload)
            if format_match:
                return ZoneAudioFormat(
                    zone=zone_num, format=format_match.group(1).strip()
                )

        if const.RESP_AUDIO_CHANNELS in payload:
            channels_match = re.search(rf"{const.RESP_AUDIO_CHANNELS}(.+)", payload)
            if channels_match:
                return ZoneAudioChannels(
                    zone=zone_num, channels=channels_match.group(1).strip()
                )

        if const.RESP_VIDEO_RESOLUTION in payload:
            res_match = re.search(rf"{const.RESP_VIDEO_RESOLUTION}(.+)", payload)
            if res_match:
                return ZoneVideoResolution(
                    zone=zone_num, resolution=res_match.group(1).strip()
                )

        if const.RESP_LISTENING_MODE in payload and "?" not in payload:
            mode_match = re.search(rf"{const.RESP_LISTENING_MODE}(\d+)", payload)
            if mode_match:
                mode_num = int(mode_match.group(1))
                return ZoneListeningMode(
                    zone=zone_num,
                    mode_number=mode_num,
                    mode_name=const.LISTENING_MODES.get(mode_num, f"Mode {mode_num}"),
                )

        if const.RESP_AUDIO_INPUT_RATE in payload:
            rate_match = re.search(rf"{const.RESP_AUDIO_INPUT_RATE}(.+)", payload)
            if rate_match:
                return ZoneSampleRateInfo(
                    zone=zone_num, info=rate_match.group(1).strip()
                )

        if const.RESP_AUDIO_SAMPLE_RATE in payload:
            rate_match = re.search(rf"{const.RESP_AUDIO_SAMPLE_RATE}(\d+)", payload)
            if rate_match:
                return ZoneSampleRate(
                    zone=zone_num, rate_khz=int(rate_match.group(1))
                )

        if const.RESP_AUDIO_BIT_DEPTH in payload:
            depth_match = re.search(rf"{const.RESP_AUDIO_BIT_DEPTH}(\d+)", payload)
            if depth_match:
                return ZoneBitDepth(zone=zone_num, depth=int(depth_match.group(1)))

    return None
