"""Constants for Anthem A/V Receiver integration."""

# General formatting
CMD_TERMINATOR = ";"  # Anthem protocol uses semicolon for both commands and responses
CMD_ZONE_PREFIX = "Z"

# Global System Commands
CMD_ECHO_OFF = "ECH0"
CMD_STANDBY_IP_CONTROL_ON = "SIP1"
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
CMD_LEVEL_UP = "LUP"
CMD_LEVEL_DOWN = "LDN"

# Queries (Suffix with ?)
QUERY_SUFFIX = "?"
CMD_POWER_QUERY = CMD_POWER + QUERY_SUFFIX
CMD_VOLUME_QUERY = CMD_VOLUME + QUERY_SUFFIX
CMD_MUTE_QUERY = CMD_MUTE + QUERY_SUFFIX
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

# Audio Listening Modes
LISTENING_MODES = {
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
