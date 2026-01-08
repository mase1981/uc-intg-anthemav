# In driver.py, update refresh_entity_state() to update SOURCE_LIST:

async def refresh_entity_state(self, entity_id: str) -> None:
    """
    Refresh entity state by querying device and updating SOURCE_LIST.
    
    CRITICAL: Updates SOURCE_LIST from discovered inputs to ensure
    entities always have current input configuration.
    """
    _LOG.info("[%s] Refreshing entity state", entity_id)
    
    # Extract device_id from entity_id
    device_id = self.device_from_entity_id(entity_id)
    if not device_id:
        _LOG.warning("[%s] Could not extract device_id", entity_id)
        return
    
    device = self._configured_devices.get(device_id)
    if not device:
        _LOG.warning("[%s] Device %s not found", entity_id, device_id)
        return
    
    configured_entity = self.api.configured_entities.get(entity_id)
    if not configured_entity:
        _LOG.debug("[%s] Entity not configured yet", entity_id)
        return
    
    if not device.is_connected:
        _LOG.debug("[%s] Device not connected, marking unavailable", entity_id)
        await super().refresh_entity_state(entity_id)
        return
    
    if configured_entity.entity_type == EntityTypes.MEDIA_PLAYER:
        source_list = device.get_input_list()
        if source_list:
            self.api.configured_entities.update_attributes(
                entity_id, {media_player.Attributes.SOURCE_LIST: source_list}
            )
            _LOG.info(
                "[%s] Updated SOURCE_LIST with %d sources", entity_id, len(source_list)
            )

    parts = entity_id.split(".")
    if len(parts) == 2:
        zone_num = 1
    elif len(parts) == 3 and parts[2].startswith("zone"):
        try:
            zone_num = int(parts[2].replace("zone", ""))
        except ValueError:
            _LOG.error("[%s] Invalid zone format: %s", entity_id, parts[2])
            return
    else:
        zone_num = 1
    
    _LOG.info("[%s] Querying device status for Zone %d", entity_id, zone_num)
    await device.query_status(zone_num)