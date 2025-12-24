"""
Anthem A/V setup flow - HOTFIX for AttributeError.

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


<<<<<<< HEAD
class AnthemSetupFlow(BaseSetupFlow[AnthemDeviceConfig]):
    """Setup flow that discovers device capabilities BEFORE creating entities."""
    
    def get_manual_entry_form(self) -> RequestUserInput:
        """Get manual entry form for Anthem receiver configuration."""
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
                                    "\n\n✨ The integration will automatically discover available inputs!"
                                )
                            }
                        }
                    },
=======
class AnthemSetupFlow(BaseSetupFlow):
    """Setup flow for Anthem A/V receivers."""

    def get_manual_entry_form(self) -> dict:
        """Return manual entry configuration form."""
        return {
            "title": {"en": "Anthem A/V Receiver Setup"},
            "settings": [
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "description": {"en": "IP address of your Anthem receiver"},
                    "field": {"text": {"value": "192.168.1.100"}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "description": {"en": "TCP port number (default: 14999)"},
                    "field": {"text": {"value": "14999"}},
>>>>>>> main
                },
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
<<<<<<< HEAD
                    "field": {"text": {"value": "Anthem"}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": "192.168.1.100"}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "field": {"text": {"value": "14999"}},
=======
                    "description": {"en": "Friendly name for your receiver"},
                    "field": {"text": {"value": "Anthem"}},
                },
                {
                    "id": "model",
                    "label": {"en": "Model Series"},
                    "description": {"en": "Select your Anthem model series"},
                    "field": {
                        "dropdown": {
                            "items": [
                                {
                                    "id": "MRX",
                                    "label": {
                                        "en": "MRX Series (520, 720, 1120, 1140)"
                                    },
                                },
                                {
                                    "id": "AVM",
                                    "label": {"en": "AVM Series (60, 70, 90)"},
                                },
                                {"id": "STR", "label": {"en": "STR Series"}},
                            ]
                        }
                    },
>>>>>>> main
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
<<<<<<< HEAD
        )
    
    async def query_device(
        self, input_values: dict[str, Any]
    ) -> RequestUserInput | AnthemDeviceConfig:
        """
        Query device and STORE discovered capabilities in config.
        
        CRITICAL: Discovers inputs during setup so entities have complete SOURCE_LIST!
        """
        host = input_values.get("host", "").strip()
        if not host:
            _LOG.error("No host provided")
            raise ValueError("IP address is required")
        
=======
        }

    async def query_device(self, input_values: dict) -> AnthemDeviceConfig:
        """Query device and return configuration."""
        host = input_values.get("host", "").strip()
        if not host:
            return (
                self.get_manual_entry_form()
            )  # Rather than failing, give the user another chance to enter the host

        port = int(input_values.get("port", 14999))
>>>>>>> main
        name = input_values.get("name", f"Anthem ({host})").strip()
        port = int(input_values.get("port", 14999))
        zones_count = int(input_values.get("zones", "1"))

        identifier = f"anthem_{host.replace('.', '_')}_{port}"
<<<<<<< HEAD
        zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]
        
        temp_config = AnthemDeviceConfig(
=======

        zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]

        device_config = AnthemDeviceConfig(
>>>>>>> main
            identifier=identifier,
            name=name,
            host=host,
            port=port,
            zones=zones,
        )
<<<<<<< HEAD
        
        _LOG.info("=" * 60)
        _LOG.info("SETUP: Connecting to %s:%d for discovery...", host, port)
        _LOG.info("=" * 60)
        
        try:
            discovery_device = AnthemDevice(temp_config)
            
            connected = await asyncio.wait_for(
                discovery_device.connect(),
                timeout=15.0
            )
            
            if not connected:
                _LOG.error("SETUP: Connection failed")
                await discovery_device.disconnect()
                raise ValueError(f"Failed to connect to {host}:{port}")
            
            _LOG.info("SETUP: ✅ Connected! Waiting for input discovery...")
            
            # CRITICAL: Wait for input discovery to complete
            max_wait = 5.0
            wait_interval = 0.2
            total_waited = 0.0
            
            while total_waited < max_wait:
                await asyncio.sleep(wait_interval)
                total_waited += wait_interval
                
                if discovery_device._input_count > 0:
                    _LOG.info("SETUP: Input count discovered: %d", discovery_device._input_count)
                    await asyncio.sleep(1.0)
                    break
            
            # Get discovered capabilities
            input_count = discovery_device._input_count
            input_names_dict = discovery_device._input_names.copy()
            
            # Convert input names dict to list
            if input_names_dict and input_count > 0:
                discovered_inputs = [
                    input_names_dict.get(i, f"Input {i}") 
                    for i in range(1, input_count + 1)
                ]
            else:
                # Fallback to defaults
                _LOG.warning("SETUP: Input discovery incomplete, using defaults")
                discovered_inputs = [
                    "HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4",
                    "HDMI 5", "HDMI 6", "HDMI 7", "HDMI 8",
                    "Analog 1", "Analog 2",
                    "Digital 1", "Digital 2",
                    "USB", "Network", "ARC"
                ]
            
            _LOG.info("=" * 60)
            _LOG.info("SETUP: ✅ Discovery Complete!")
            _LOG.info("   Inputs: %d", len(discovered_inputs))
            _LOG.info("   Input List: %s", discovered_inputs)
            _LOG.info("   Zones: %d", zones_count)
            _LOG.info("=" * 60)
            
            # Disconnect discovery device
            await discovery_device.disconnect()
            _LOG.info("SETUP: Discovery connection closed")
            
            # Create FINAL config WITH discovered inputs
            # NOTE: Model doesn't matter - all Anthem models use same protocol
            final_config = AnthemDeviceConfig(
                identifier=identifier,
                name=name,
                host=host,
                model="AVM",  # All models supported (MRX, AVM, STR)
                port=port,
                zones=zones,
                discovered_inputs=discovered_inputs,
                discovered_model="Anthem"  # Generic - all models work the same
            )
            
            _LOG.info("SETUP: ✅ Returning config with %d discovered inputs", len(discovered_inputs))
            return final_config
        
        except asyncio.TimeoutError:
            _LOG.error("SETUP: Connection timeout to %s:%d", host, port)
            raise ValueError(
                f"Connection timeout to {host}:{port}\n"
                "Please ensure:\n"
                "• Receiver is powered on\n"
                "• IP address is correct\n"
                "• Receiver is on same network"
            ) from None
        
        except Exception as err:
            _LOG.error("SETUP: Error - %s", err, exc_info=True)
            raise ValueError(f"Setup failed: {err}") from err
=======

        _LOG.info(f"Testing connection to Anthem at {host}:{port}")

        # I'm nearly positive this won't work as you haven't implmemented the abstract methods in AnthemDevice
        # This is because you inherited from a BaseDevice Class. But now it's annoying you have to implement those methods even if you don't use them.
        # I always just duplicated the code needed to connect in setup. This isn't really the optimal solution, but it works.
        # But depending on what the device class is doing, it may not be right to call it either.
        # This is another "problem" to think about :)
        test_device = AnthemDevice(device_config)

        try:
            connection_successful = await test_device.connect()

            if not connection_successful:
                _LOG.error(f"Connection test failed for host: {host}")
                return SetupError(
                    IntegrationSetupError.CONNECTION_REFUSED
                )  # SetupError is not an exception class

            _LOG.info("Connection successful, verifying device responds...")
            await test_device.query_model()
            await asyncio.sleep(0.2)
            await test_device.query_power(1)
            await asyncio.sleep(0.5)

            response_timeout = 3.0
            start_time = asyncio.get_event_loop().time()
            received_response = False

            while (asyncio.get_event_loop().time() - start_time) < response_timeout:
                if test_device.get_cached_state("model"):
                    received_response = True
                    _LOG.info(
                        f"Received response from device: {test_device.get_cached_state('model')}"
                    )
                    break
                await asyncio.sleep(0.1)

            if not received_response:
                _LOG.warning(
                    "No response received during connection test (may still work)"
                )

            _LOG.info(f"Successfully validated Anthem receiver at {host}:{port}")
            return device_config

        except Exception as e:
            _LOG.error(f"Connection test error: {e}", exc_info=True)
            return SetupError(IntegrationSetupError.OTHER)
        finally:
            await test_device.disconnect()
>>>>>>> main
