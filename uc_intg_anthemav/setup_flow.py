"""
Anthem A/V setup flow implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi import IntegrationSetupError, RequestUserInput, SetupError

from ucapi_framework import BaseSetupFlow

from .config import AnthemDeviceConfig, ZoneConfig
from .device import AnthemDevice

_LOG = logging.getLogger(__name__)


class AnthemSetupFlow(BaseSetupFlow[AnthemDeviceConfig]):
    """
    Setup flow for Anthem A/V receivers.
    
    Matches PSN integration pattern that successfully uses ucapi-framework.
    """
    
    def get_manual_entry_form(self) -> RequestUserInput:
        """
        Get manual entry form for Anthem receiver configuration.
        
        Returns RequestUserInput directly (not list[dict]).
        This matches PSN's working implementation.
        """
        return RequestUserInput(
            {"en": "Anthem A/V Receiver Setup"},
            [
                {
                    "id": "info",
                    "label": {"en": "Setup Information"},
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "Configure your Anthem A/V receiver. "
                                    "The receiver must be powered on and connected to your network. "
                                    "\n\nPlease enter the IP address and configuration details below."
                                )
                            }
                        }
                    },
                },
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "Anthem"}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": "127.0.0.1"}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "field": {"text": {"value": "14999"}},
                },
                {
                    "id": "model",
                    "label": {"en": "Model Series"},
                    "field": {
                        "dropdown": {
                            "items": [
                                {"id": "MRX", "label": {"en": "MRX Series (MRX 520, 720, 1120, 1140)"}},
                                {"id": "AVM", "label": {"en": "AVM Series (AVM 60, 70, 90)"}},
                                {"id": "STR", "label": {"en": "STR Series"}},
                            ]
                        }
                    },
                },
                {
                    "id": "zones",
                    "label": {"en": "Number of Zones"},
                    "field": {
                        "dropdown": {
                            "items": [
                                {"id": "1", "label": {"en": "1 Zone"}},
                                {"id": "2", "label": {"en": "2 Zones"}},
                                {"id": "3", "label": {"en": "3 Zones"}},
                            ]
                        }
                    },
                },
            ],
        )
    
    async def query_device(
        self, input_values: dict[str, Any]
    ) -> RequestUserInput | AnthemDeviceConfig:
        """
        Process manual entry form, validate connection, and create config.
        
        This matches PSN's query_device pattern.
        Performs validation and returns config if successful, or raises ValueError.
        """
        host = input_values.get("host", "").strip()
        if not host:
            _LOG.error("No host provided")
            raise ValueError("IP address is required")
        
        name = input_values.get("name", f"Anthem ({host})").strip()
        port = int(input_values.get("port", 14999))
        model = input_values.get("model", "MRX").strip()
        zones_count = int(input_values.get("zones", "1"))
        
        # Create identifier from IP address
        identifier = f"anthem_{host.replace('.', '_')}_{port}"
        
        # Create zone configurations
        zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]
        
        # Create device config
        device_config = AnthemDeviceConfig(
            identifier=identifier,
            name=name,
            host=host,
            model=model,
            port=port,
            zones=zones
        )
        
        # Test connection (like PSN does authentication)
        _LOG.info("Testing connection to %s:%d", host, port)
        
        try:
            test_device = AnthemDevice(device_config)
            connected = await asyncio.wait_for(test_device.connect(), timeout=10.0)
            
            if not connected:
                _LOG.error("Connection test failed for %s", host)
                await test_device.disconnect()
                raise ValueError(f"Failed to connect to {host}:{port}")
            
            _LOG.info("Connection successful to %s", host)
            await test_device.disconnect()
            
            # Return validated configuration
            return device_config
        
        except asyncio.TimeoutError:
            _LOG.error("Connection timeout to %s:%d", host, port)
            raise ValueError(f"Connection timeout to {host}:{port}") from None
        except Exception as err:
            _LOG.error("Connection error: %s", err, exc_info=True)
            raise ValueError(f"Failed to connect to {host}:{port}: {err}") from err