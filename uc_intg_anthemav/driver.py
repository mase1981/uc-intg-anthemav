"""
Anthem A/V integration driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import Dict, List

import ucapi
from ucapi import DeviceStates, Events, StatusCodes

from uc_intg_anthemav.client import AnthemClient
from uc_intg_anthemav.config import AnthemConfig, DeviceConfig
from uc_intg_anthemav.media_player import AnthemMediaPlayer
from uc_intg_anthemav.setup import AnthemSetup

api: ucapi.IntegrationAPI | None = None
config: AnthemConfig | None = None
clients: Dict[str, AnthemClient] = {}
media_players: Dict[str, AnthemMediaPlayer] = {}
entities_ready: bool = False
initialization_lock: asyncio.Lock = asyncio.Lock()
setup_manager: AnthemSetup | None = None

_LOG = logging.getLogger(__name__)


async def _initialize_integration():
    global clients, api, config, media_players, entities_ready
    
    async with initialization_lock:
        if entities_ready:
            _LOG.debug("Entities already initialized, skipping")
            return True
        
        if not config or not config.is_configured():
            _LOG.error("Configuration not found or invalid.")
            if api:
                await api.set_device_state(DeviceStates.ERROR)
            return False
        
        _LOG.info(f"Initializing Anthem integration for {len(config.get_all_devices())} devices...")
        if api:
            await api.set_device_state(DeviceStates.CONNECTING)
        
        connected_devices = 0
        
        api.available_entities.clear()
        clients.clear()
        media_players.clear()
        
        for device_config in config.get_enabled_devices():
            try:
                _LOG.info(f"Connecting to Anthem device: {device_config.name} at {device_config.ip_address}")
                
                client = AnthemClient(device_config)
                
                connection_success = await client.connect()
                if not connection_success:
                    _LOG.warning(f"Failed to connect to device: {device_config.name}")
                    await client.close()
                    continue
                
                _LOG.info(f"Connected to Anthem device: {device_config.name} ({device_config.model})")
                
                clients[device_config.device_id] = client
                
                await asyncio.sleep(0.5)
                
                for zone_config in device_config.zones:
                    if not zone_config.enabled:
                        continue
                    
                    media_player_entity = AnthemMediaPlayer(client, device_config, zone_config, api)
                    
                    api.available_entities.add(media_player_entity)
                    
                    media_players[media_player_entity.id] = media_player_entity
                    
                    _LOG.info(f"Created media player entity: {media_player_entity.id}")
                    
                    await asyncio.sleep(0.3)
                    await media_player_entity.push_update()
                
                await asyncio.sleep(0.5)
                
                connected_devices += 1
                _LOG.info(f"Successfully setup device: {device_config.name} with {len(device_config.zones)} zones")
                
            except Exception as e:
                _LOG.error(f"Failed to setup device {device_config.name}: {e}", exc_info=True)
                continue
        
        if connected_devices > 0:
            entities_ready = True
            await api.set_device_state(DeviceStates.CONNECTED)
            _LOG.info(f"Anthem integration initialization completed successfully - {connected_devices}/{len(config.get_all_devices())} devices connected.")
            return True
        else:
            entities_ready = False
            if api:
                await api.set_device_state(DeviceStates.ERROR)
            _LOG.error("No devices could be connected during initialization")
            return False


async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    global config, entities_ready, setup_manager
    
    if isinstance(msg, ucapi.DriverSetupRequest):
        return await setup_manager.handle_setup_request(msg.setup_data)
    
    elif isinstance(msg, ucapi.UserDataResponse):
        action = await setup_manager.handle_user_data(msg.input_values)
        
        if isinstance(action, ucapi.SetupComplete):
            _LOG.info("Setup confirmed. Initializing integration components...")
            await _initialize_integration()
        
        return action
    
    return ucapi.SetupError(ucapi.IntegrationSetupError.OTHER)


async def on_subscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Entities subscribed: {entity_ids}")
    
    if not entities_ready:
        _LOG.error("RACE CONDITION: Subscription before entities ready!")
        success = await _initialize_integration()
        if not success:
            _LOG.error("Failed to initialize during subscription attempt")
            return
    
    for entity_id in entity_ids:
        if entity_id in media_players:
            await media_players[entity_id].push_update()


async def on_connect():
    global entities_ready
    
    _LOG.info("Remote Two connected")
    
    if config:
        config.reload_from_disk()
    
    if config and config.is_configured():
        if not entities_ready:
            _LOG.warning("Entities not ready on connect - initializing now")
            await _initialize_integration()
        else:
            _LOG.info("Entities already ready, confirming connection")
            if api:
                await api.set_device_state(DeviceStates.CONNECTED)
    else:
        _LOG.info("Not configured, waiting for setup")
        if api:
            await api.set_device_state(DeviceStates.DISCONNECTED)


async def on_disconnect():
    _LOG.info("Remote Two disconnected")


async def on_unsubscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Entities unsubscribed: {entity_ids}")


async def main():
    global api, config, setup_manager
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    _LOG.info("Starting Anthem A/V Integration Driver")
    
    try:
        loop = asyncio.get_running_loop()
        
        config_dir = os.getenv("UC_CONFIG_HOME", "./")
        config_file_path = os.path.join(config_dir, "config.json")
        config = AnthemConfig(config_file_path)
        
        setup_manager = AnthemSetup(config)
        
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        api = ucapi.IntegrationAPI(loop)
        
        if config.is_configured():
            _LOG.info("Pre-configuring entities before UC Remote connection")
            _LOG.info(f"Configuration summary: {config.get_summary()}")
            await _initialize_integration()
        
        await api.init(os.path.abspath(driver_path), setup_handler)
        
        api.add_listener(Events.SUBSCRIBE_ENTITIES, on_subscribe_entities)
        api.add_listener(Events.UNSUBSCRIBE_ENTITIES, on_unsubscribe_entities)
        api.add_listener(Events.CONNECT, on_connect)
        api.add_listener(Events.DISCONNECT, on_disconnect)
        
        if not config.is_configured():
            _LOG.info("Device not configured, waiting for setup...")
            await api.set_device_state(DeviceStates.DISCONNECTED)
        
        _LOG.info("Anthem integration driver started successfully")
        await asyncio.Future()
        
    except Exception as e:
        _LOG.critical(f"Fatal error in main: {e}", exc_info=True)
    finally:
        _LOG.info("Shutting down Anthem integration")
        
        for client in clients.values():
            try:
                await client.close()
            except Exception as e:
                _LOG.error(f"Error closing client: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user")
    except Exception as e:
        _LOG.error(f"Integration failed: {e}")
        raise