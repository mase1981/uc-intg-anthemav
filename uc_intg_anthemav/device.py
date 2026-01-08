# In device.py, update the get_input_list() method:

def get_input_list(self) -> list[str]:
    """
    Get list of available input sources with priority order:
    1. Stored discovered inputs from config (from setup)
    2. Runtime discovered inputs (from ICN/ISN responses)
    3. Default fallback list
    """
    # PRIORITY 1: Use stored discovered inputs from config
    if self._device_config.discovered_inputs:
        _LOG.debug(
            "[%s] Using discovered inputs from config (%d sources)",
            self.log_id,
            len(self._device_config.discovered_inputs),
        )
        return self._device_config.discovered_inputs
    
    # PRIORITY 2: Use runtime discovered inputs
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
    
    # PRIORITY 3: Default fallback
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