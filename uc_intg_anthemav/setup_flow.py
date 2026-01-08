"""
Anthem A/V setup flow with dynamic input discovery.

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
                },
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
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
        Query device and STORE discovered capabilities in config.
        
        CRITICAL: Discovers inputs during setup so entities have complete SOURCE_LIST!
        """
        host = input_values.get("host", "").strip()
        if not host:
            _LOG.error("No host provided")
            raise ValueError("IP address is required")
        
        name = input_values.get("name", f"Anthem ({host})").strip()
        port = int(input_values.get("port", 14999))
        zones_count = int(input_values.get("zones", "1"))
        
        identifier = f"anthem_{host.replace('.', '_')}_{port}"
        zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]
        
        # Create temporary config for discovery
        temp_config = AnthemDeviceConfig(
            identifier=identifier,
            name=name,
            host=host,
            port=port,
            zones=zones
        )
        
        _LOG.info("=" * 60)
        _LOG.info("SETUP: Connecting to %s:%d for discovery...", host, port)
        _LOG.info("=" * 60)
        
        try:
            # Create temporary device for discovery
            discovery_device = AnthemDevice(temp_config)
            
            # Connect with timeout
            connected = await asyncio.wait_for(
                discovery_device.connect(),
                timeout=15.0
            )
            
            if not connected:
                _LOG.error("SETUP: Connection failed")
                await discovery_device.disconnect()
                raise ValueError(f"Failed to connect to {host}:{port}")
            
            _LOG.info("SETUP: ✅ Connected! Waiting for input discovery...")
            
            # The device will query ICN (input count) and ISN (input names) automatically
            max_wait = 5.0  # Wait up to 5 seconds for discovery
            wait_interval = 0.2
            total_waited = 0.0
            
            while total_waited < max_wait:
                await asyncio.sleep(wait_interval)
                total_waited += wait_interval
                
                # Check if we have input count
                if discovery_device._input_count > 0:
                    _LOG.info("SETUP: Input count discovered: %d", discovery_device._input_count)
                    # Wait a bit more for all input names to be discovered
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
                # Fallback to defaults if discovery incomplete
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