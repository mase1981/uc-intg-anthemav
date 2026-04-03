"""Constants for Anthem A/V Receiver integration."""

# General formatting
CMD_TERMINATOR = ";"  # Anthem protocol uses semicolon for both commands and responses
CMD_ZONE_PREFIX = "Z"

# Global System Commands
CMD_ECHO_OFF = "ECH0"
CMD_ECHO_ON = "ECH1"
CMD_STANDBY_IP_CONTROL_ON = "SIP1"  # x20 series
CMD_TX_STATUS_IP = "GCTXS1"  # x40 series: enable IP status reporting
CMD_CONNECTED_STANDBY_ON = "GCCSTBY1"  # x40 series: enable connected standby
CMD_MODEL_QUERY = "IDM?"
CMD_INPUT_COUNT_QUERY = "ICN?"

# Global Control Commands (GC prefix)
CMD_FRONT_PANEL_BRIGHTNESS = "GCFPB"  # + 0-3 (or 0-100 on some models)
CMD_FRONT_PANEL_DISPLAY_INFO = "GCFPDI"  # + 0 (All) / 1 (Volume only)
CMD_HDMI_STANDBY_BYPASS = "GCSHDMIB"  # + 0-8
CMD_CEC_CONTROL = "GCCECC"  # + 0/1
CMD_ZONE2_MAX_VOL = "GCZ2MMV"  # + -40 to 10
CMD_ZONE2_POWER_ON_VOL = "GCZ2POV"  # + -90 to 10
CMD_ZONE2_POWER_ON_INPUT = "GCZ2POI"  # + Input ID
CMD_OSD_INFO = "GCOSID"  # + 0 (Off) / 1 (16:9) / 2 (2.4:1)

# Input Settings (IS prefix)
CMD_INPUT_SETTING_PREFIX = "IS"
CMD_INPUT_NAME_QUERY_SUFFIX = "IN?"
CMD_ARC_SETTING_SUFFIX = "ARC"

# Input Name Query Commands - model-specific formats
# MRX x20 series (720, 520, 1120) and AVM 60 use ISN/ILN format
CMD_INPUT_SHORT_NAME_PREFIX = "ISN"  # ISNyy? format (yy=01-30, zero-padded)
CMD_INPUT_LONG_NAME_PREFIX = "ILN"   # ILNyy? format (yy=01-30, zero-padded)

# Zone Commands (Z prefix) - these usually follow Z{zone}
CMD_POWER = "POW"
CMD_VOLUME = "VOL"
CMD_VOLUME_UP = "VUP"
CMD_VOLUME_DOWN = "VDN"
CMD_MUTE = "MUT"
CMD_INPUT = "INP"
CMD_VOLUME_PERCENT = "PVOL"
CMD_VOLUME_PERCENT_UP = "PVUP"
CMD_VOLUME_PERCENT_DOWN = "PVDN"
CMD_LEVEL_UP = "LUP"
CMD_LEVEL_DOWN = "LDN"

# Queries (Suffix with ?)
QUERY_SUFFIX = "?"
CMD_POWER_QUERY = CMD_POWER + QUERY_SUFFIX
CMD_VOLUME_QUERY = CMD_VOLUME + QUERY_SUFFIX
CMD_MUTE_QUERY = CMD_MUTE + QUERY_SUFFIX
CMD_VOLUME_PERCENT_QUERY = CMD_VOLUME_PERCENT + QUERY_SUFFIX
CMD_INPUT_QUERY = CMD_INPUT + QUERY_SUFFIX

# Status Queries (Zone Context)
CMD_AUDIO_FORMAT_QUERY = "AIF?"
CMD_AUDIO_CHANNELS_QUERY = "AIC?"
CMD_VIDEO_RESOLUTION_QUERY = "VIR?"
CMD_LISTENING_MODE_QUERY = "ALM?"
CMD_AUDIO_SAMPLE_RATE_QUERY = "AIR?"
CMD_AUDIO_SAMPLE_RATE_KHZ_QUERY = "SRT?"
CMD_AUDIO_BIT_DEPTH_QUERY = "BDP?"
CMD_AUDIO_INPUT_NAME_QUERY = "AIN?"
CMD_VIDEO_HORIZ_RES_QUERY = "IRH?"
CMD_VIDEO_VERT_RES_QUERY = "IRV?"

# Response Prefixes
RESP_MODEL = "IDM"
RESP_INPUT_COUNT = "ICN"
RESP_INPUT_SETTING = "IS"
RESP_ZONE_PREFIX = "Z"
RESP_POWER = "POW"
RESP_VOLUME = "VOL"
RESP_VOLUME_PERCENT = "PVOL"
RESP_MUTE = "MUT"
RESP_INPUT = "INP"
RESP_INPUT_NAME = "IN"  # For input name responses (IS01INname), different from RESP_INPUT
RESP_INPUT_SHORT_NAME = "ISN"  # For ISNyyname responses (MRX x20/AVM 60)
RESP_INPUT_LONG_NAME = "ILN"   # For ILNyyname responses (MRX x20/AVM 60)
RESP_AUDIO_FORMAT = "AIF"
RESP_AUDIO_CHANNELS = "AIC"
RESP_VIDEO_RESOLUTION = "VIR"
RESP_LISTENING_MODE = "ALM"
RESP_AUDIO_INPUT_RATE = "AIR"
RESP_AUDIO_SAMPLE_RATE = "SRT"
RESP_AUDIO_BIT_DEPTH = "BDP"

# Error Responses
RESP_ERROR_INVALID_COMMAND = "!I"
RESP_ERROR_EXECUTION_FAILED = "!E"

# Values / Parameters
VAL_ON = "1"
VAL_OFF = "0"
VAL_TOGGLE = "t"

# Audio Listening Modes - x40 series (MRX 540/740/1140, AVM 70/90)
# Verified empirically on MRX 540 and matches python-anthemav library
LISTENING_MODES_X40 = {
    0: "None",
    1: "AnthemLogic Cinema",
    2: "AnthemLogic Music",
    3: "Dolby Surround",
    4: "DTS Neural:X",
    5: "DTS Virtual:X",
    6: "All Channel Stereo",
    7: "Mono",
    8: "All Channel Mono",
}

# Audio Listening Modes - x20 series (MRX 520/720/1120, AVM 60)
LISTENING_MODES_X20 = {
    0: "None",
    1: "AnthemLogic Cinema",
    2: "AnthemLogic Music",
    3: "PLII Movie",
    4: "PLII Music",
    5: "Neo:6 Cinema",
    6: "Neo:6 Music",
    7: "All Channel Stereo",
    8: "All Channel Mono",
    9: "Mono",
    10: "Mono-Academy",
    11: "Mono (L)",
    12: "Mono (R)",
    13: "High Blend",
    14: "Dolby Surround",
    15: "Stereo",
}

# Sensor decode tables - x20 series (MRX 520/720/1120, AVM 60)
AUDIO_FORMAT_NAMES = {
    "0": "No Audio",
    "1": "Analog",
    "2": "PCM",
    "3": "Dolby",
    "4": "DSD",
    "5": "DTS",
    "6": "Atmos",
}

# Sensor decode tables - x40 series (MRX 540/740/1140, AVM 70/90)
# Verified empirically on MRX 540
AUDIO_FORMAT_NAMES_X40 = {
    "0": "No Audio",
    "1": "Analog",
    "2": "PCM",
    "3": "Dolby",
    "4": "DSD",
    "5": "DTS",
    "6": "Atmos",
    "7": "DTS-X",
}

AUDIO_CHANNELS_NAMES = {
    "0": "No Audio",
    "1": "Other",
    "2": "Mono",
    "3": "2 Channel",
    "4": "5.1 Channel",
    "5": "6.1 Channel",
    "6": "7.1 Channel",
    "7": "Atmos",
}

AUDIO_CHANNELS_NAMES_X40 = {
    "0": "No Audio",
    "1": "Other",
    "2": "Mono",
    "3": "2 Channel",
    "4": "5.1 Channel",
    "5": "7.1 Channel",
    "6": "Atmos",
    "7": "DTS-X",
}

# Video resolution - indices 9-13 fixed per both x20 and x40 API docs
VIDEO_RESOLUTION_NAMES = {
    "0": "No Input",
    "1": "Other",
    "2": "1080p60",
    "3": "1080p50",
    "4": "1080p24",
    "5": "1080i60",
    "6": "1080i50",
    "7": "720p60",
    "8": "720p50",
    "9": "576p50",
    "10": "576i50",
    "11": "480p60",
    "12": "480i60",
    "13": "3D",
    "14": "4K",
}

VIDEO_RESOLUTION_NAMES_X40 = {
    **VIDEO_RESOLUTION_NAMES,
    "14": "4K 60Hz",
    "15": "4K 50Hz",
    "16": "4K 24Hz",
}

# x20 Front Panel Brightness (uses FPB command, not GCFPB)
CMD_FRONT_PANEL_BRIGHTNESS_X20 = "FPB"

# x20 ARC command (global Z1ARC, not per-input ISxARC)
CMD_ARC_X20 = "Z1ARC"

# Speaker channel mapping - x20 series
SPEAKER_CH_X20_SUBS = 0
SPEAKER_CH_X20_FRONTS = 1
SPEAKER_CH_X20_CENTER = 2
SPEAKER_CH_X20_SURROUNDS = 3
SPEAKER_CH_X20_BACKS = 4
SPEAKER_CH_X20_HEIGHTS = 6

# Default Input Map (Fallback)
DEFAULT_INPUT_MAP = {
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

# Default input names list for fallback
DEFAULT_INPUT_LIST = list(DEFAULT_INPUT_MAP.keys())
