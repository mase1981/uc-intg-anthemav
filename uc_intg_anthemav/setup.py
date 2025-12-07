"""
Anthem A/V setup flow implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Dict

from ucapi import IntegrationSetupError, RequestUserInput, SetupComplete, SetupError, UserDataResponse

from uc_intg_anthemav.client import AnthemClient
from uc_intg_anthemav.config import AnthemConfig, DeviceConfig, ZoneConfig

_LOG = logging.getLogger(__name__)


class AnthemSetup:
    
    def __init__(self, config: AnthemConfig):
        self._config = config
        self._setup_state = {}
    
    async def handle_setup_request(self, setup_data: Dict[str, Any]) -> Any:
        device_count = int(setup_data.get("device_count", 1))
        host = setup_data.get("host", "").strip()
        
        if device_count == 1 and host:
            return await self._handle_single_device_setup(setup_data)
        else:
            return await self._request_device_configurations(device_count)
    
    async def _handle_single_device_setup(self, setup_data: Dict[str, Any]) -> Any:
        host_input = setup_data.get("host")
        if not host_input:
            _LOG.error("No host provided in setup data")
            return SetupError(IntegrationSetupError.OTHER)
        
        host = host_input.strip()
        port = int(setup_data.get("port", 14999))
        name = setup_data.get("name", f"Anthem ({host})").strip()
        model = setup_data.get("model", "MRX").strip()
        zones_count = int(setup_data.get("zones", 1))
        
        _LOG.info(f"Testing connection to Anthem at {host}:{port}")
        
        try:
            zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]
            
            device_id = f"anthem_{host.replace('.', '_')}_{port}"
            
            existing_device = self._config.get_device(device_id)
            if existing_device:
                _LOG.info(f"Device {device_id} already exists, removing for reconfiguration")
                self._config.remove_device(device_id)
            
            device_config = DeviceConfig(
                device_id=device_id,
                name=name,
                ip_address=host,
                model=model,
                port=port,
                zones=zones
            )
            
            test_client = AnthemClient(device_config)
            
            try:
                _LOG.info("Testing connection...")
                connection_successful = await test_client.connect()
                
                if not connection_successful:
                    _LOG.error(f"Connection test failed for host: {host}")
                    return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
                
                _LOG.info("Connection successful, verifying device responds to commands...")
                await test_client.query_model()
                await asyncio.sleep(0.2)
                await test_client.query_power(1)
                await asyncio.sleep(0.5)
                
                _LOG.info("Waiting for device responses...")
                response_timeout = 3.0
                start_time = asyncio.get_event_loop().time()
                received_response = False
                
                while (asyncio.get_event_loop().time() - start_time) < response_timeout:
                    if test_client.get_cached_state("model"):
                        received_response = True
                        _LOG.info(f"Received response from device: {test_client.get_cached_state('model')}")
                        break
                    await asyncio.sleep(0.1)
                
                if not received_response:
                    _LOG.warning("No response received from device during connection test (may still work)")
                
            finally:
                _LOG.info("Closing test connection...")
                await test_client.close()
            
            self._config.add_device(device_config)
            _LOG.info(f"Successfully added device: {name}")
            return SetupComplete()
        
        except Exception as e:
            _LOG.error(f"Setup error: {e}", exc_info=True)
            return SetupError(IntegrationSetupError.OTHER)
    
    async def _request_device_configurations(self, device_count: int) -> RequestUserInput:
        settings = []
        
        for i in range(device_count):
            settings.extend([
                {
                    "id": f"device_{i}_ip",
                    "label": {"en": f"Device {i+1} IP Address"},
                    "description": {"en": f"IP address for Anthem device {i+1}"},
                    "field": {"text": {"value": f"192.168.1.{100+i}"}}
                },
                {
                    "id": f"device_{i}_port",
                    "label": {"en": f"Device {i+1} Port"},
                    "description": {"en": f"TCP port (default: 14999)"},
                    "field": {"text": {"value": "14999"}}
                },
                {
                    "id": f"device_{i}_name",
                    "label": {"en": f"Device {i+1} Name"},
                    "description": {"en": f"Friendly name for device {i+1}"},
                    "field": {"text": {"value": f"Anthem {i+1}"}}
                },
                {
                    "id": f"device_{i}_model",
                    "label": {"en": f"Device {i+1} Model"},
                    "description": {"en": f"Select device model"},
                    "field": {
                        "dropdown": {
                            "items": [
                                {"id": "MRX", "label": {"en": "MRX Series (MRX 520, 720, 1120, 1140)"}},
                                {"id": "AVM", "label": {"en": "AVM Series (AVM 60, 70, 90)"}},
                                {"id": "STR", "label": {"en": "STR Series"}}
                            ]
                        }
                    }
                },
                {
                    "id": f"device_{i}_zones",
                    "label": {"en": f"Device {i+1} Zones"},
                    "description": {"en": f"Number of zones to configure (1-3)"},
                    "field": {
                        "dropdown": {
                            "items": [
                                {"id": "1", "label": {"en": "1 Zone"}},
                                {"id": "2", "label": {"en": "2 Zones"}},
                                {"id": "3", "label": {"en": "3 Zones"}}
                            ]
                        }
                    }
                }
            ])
        
        return RequestUserInput(
            title={"en": f"Configure {device_count} Anthem Devices"},
            settings=settings
        )
    
    async def handle_user_data(self, input_values: Dict[str, Any]) -> Any:
        devices_to_test = []
        
        device_index = 0
        while f"device_{device_index}_ip" in input_values:
            ip_input = input_values[f"device_{device_index}_ip"]
            port = int(input_values.get(f"device_{device_index}_port", 14999))
            name = input_values[f"device_{device_index}_name"]
            model = input_values.get(f"device_{device_index}_model", "MRX")
            zones_count = int(input_values.get(f"device_{device_index}_zones", "1"))
            
            host = ip_input.strip()
            if not host:
                _LOG.error(f"Invalid IP for device {device_index + 1}")
                return SetupError(IntegrationSetupError.OTHER)
            
            devices_to_test.append({
                "host": host,
                "port": port,
                "name": name,
                "model": model,
                "zones_count": zones_count,
                "index": device_index
            })
            device_index += 1
        
        _LOG.info(f"Testing connections to {len(devices_to_test)} devices...")
        test_results = await self._test_multiple_devices(devices_to_test)
        
        successful_devices = 0
        for device_data, success in zip(devices_to_test, test_results):
            if success:
                zones = [ZoneConfig(zone_number=i) for i in range(1, device_data["zones_count"] + 1)]
                
                device_id = f"anthem_{device_data['host'].replace('.', '_')}_{device_data['port']}"
                
                existing_device = self._config.get_device(device_id)
                if existing_device:
                    _LOG.info(f"Device {device_id} already exists, removing for reconfiguration")
                    self._config.remove_device(device_id)
                
                device_config = DeviceConfig(
                    device_id=device_id,
                    name=device_data['name'],
                    ip_address=device_data['host'],
                    model=device_data['model'],
                    port=device_data['port'],
                    zones=zones
                )
                self._config.add_device(device_config)
                successful_devices += 1
                _LOG.info(f"Device {device_data['index'] + 1} ({device_data['name']}) configured successfully")
            else:
                _LOG.error(f"Device {device_data['index'] + 1} ({device_data['name']}) connection failed")
        
        if successful_devices == 0:
            _LOG.error("No devices could be connected")
            return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
        
        _LOG.info(f"Multi-device setup completed: {successful_devices}/{len(devices_to_test)} devices configured")
        return SetupComplete()
    
    async def _test_multiple_devices(self, devices: list) -> list[bool]:
        results = []
        
        for device in devices:
            zones = [ZoneConfig(zone_number=i) for i in range(1, device["zones_count"] + 1)]
            
            device_config = DeviceConfig(
                device_id=f"test_{device['index']}",
                name=device['name'],
                ip_address=device['host'],
                model=device['model'],
                port=device['port'],
                zones=zones
            )
            
            client = AnthemClient(device_config)
            
            try:
                success = await client.connect()
                if success:
                    _LOG.info(f"Testing device {device['index'] + 1} responses...")
                    await asyncio.sleep(1.0)
                results.append(success)
            except Exception as e:
                _LOG.error(f"Device {device['index'] + 1} test exception: {e}")
                results.append(False)
            finally:
                await client.close()
        
        return results