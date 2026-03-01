"""
Anthem A/V dataclass models for state management and message parsing.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ZoneState:
    """Represents the state of a single zone."""

    power: bool = False
    volume_db: int = -90
    muted: bool = False
    input_number: int = 1
    input_name: str = "Unknown"
    audio_format: str = "Unknown"
    audio_channels: str = "Unknown"
    video_resolution: str = "Unknown"
    listening_mode: str = "Unknown"
    sample_rate: str = "Unknown"

    def get(self, key: str, default: Any = None) -> Any:
        """Helper to access attributes like a dictionary."""
        return getattr(self, key, default)


@dataclass
class ParsedMessage:
    """Base class for all parsed messages."""

    pass


@dataclass
class SystemModel(ParsedMessage):
    """Device model name (IDM)."""

    model: str


@dataclass
class InputCount(ParsedMessage):
    """Number of inputs (ICN)."""

    count: int


@dataclass
class InputName(ParsedMessage):
    """Custom input name (ISiIN or ISNyy format)."""

    input_number: int
    name: str


@dataclass
class ZoneMessage(ParsedMessage):
    """Base class for zone-specific messages."""

    zone: int


@dataclass
class ZonePower(ZoneMessage):
    """Zone power state (ZxPOW)."""

    is_on: bool


@dataclass
class ZoneVolume(ZoneMessage):
    """Zone volume in dB (ZxVOL)."""

    volume_db: int


@dataclass
class ZoneMute(ZoneMessage):
    """Zone mute state (ZxMUT)."""

    is_muted: bool


@dataclass
class ZoneInput(ZoneMessage):
    """Zone input selection (ZxINP)."""

    input_number: int


@dataclass
class ZoneAudioFormat(ZoneMessage):
    """Audio input format (ZxAIF)."""

    format: str


@dataclass
class ZoneAudioChannels(ZoneMessage):
    """Audio input channels (ZxAIC)."""

    channels: str


@dataclass
class ZoneVideoResolution(ZoneMessage):
    """Video input resolution (ZxVIR)."""

    resolution: str


@dataclass
class ZoneListeningMode(ZoneMessage):
    """Listening mode (ZxALM)."""

    mode_name: str
    mode_number: int


@dataclass
class ZoneSampleRateInfo(ZoneMessage):
    """Full sample rate info string (ZxAIR)."""

    info: str


@dataclass
class ZoneSampleRate(ZoneMessage):
    """Sample rate in kHz (ZxSRT)."""

    rate_khz: int


@dataclass
class ZoneBitDepth(ZoneMessage):
    """Bit depth (ZxBDP)."""

    depth: int
