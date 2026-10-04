"""
Anthem A/V setup flow with dynamic input discovery.

Setup connects to the receiver once to prove it is reachable and to read its
model and input names. Every problem is shown on the form with what to do next,
and the form keeps what the user typed, instead of ending the setup with a bare
"not found".

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_anthemav.config import AnthemDeviceConfig, ZoneConfig
from uc_intg_anthemav.device import AnthemDevice

_LOG = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 15.0
_DISCOVERY_TIMEOUT = 5.0
_DEFAULT_PORT = 14999

_DEFAULT_INPUTS = [
    "HDMI 1", "HDMI 2", "HDMI 3", "HDMI 4",
    "HDMI 5", "HDMI 6", "HDMI 7", "HDMI 8",
    "Analog 1", "Analog 2",
    "Digital 1", "Digital 2",
    "USB", "Network", "ARC",
]


class AnthemSetupFlow(BaseSetupFlow[AnthemDeviceConfig]):
    """Setup flow that discovers device capabilities BEFORE creating entities."""

    def get_manual_entry_form(self, error: str = "", values: dict | None = None) -> RequestUserInput:
        """Get manual entry form for Anthem receiver configuration.

        :param error: problem to show at the top of the form
        :param values: values to show in the fields (what the user typed, or the saved device on Update)
        """
        if values is None:
            values = {}
            saved = self.selected_config_entry
            if saved:
                values = {
                    "name": saved.name,
                    "host": saved.host,
                    "port": str(saved.port),
                    "zones": str(len(saved.zones) or 1),
                }

        fields = []
        if error:
            fields.append({
                "id": "error",
                "label": {"en": "Problem"},
                "field": {"label": {"value": {"en": error}}},
            })
        fields += [
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
                "field": {"text": {"value": values.get("name", "Anthem")}},
            },
            {
                "id": "host",
                "label": {"en": "IP Address"},
                "field": {"text": {"value": values.get("host", "192.168.1.100")}},
            },
            {
                "id": "port",
                "label": {"en": "Port"},
                "field": {"text": {"value": values.get("port", str(_DEFAULT_PORT))}},
            },
            {
                "id": "zones",
                "label": {"en": "Number of Zones"},
                "field": {
                    "dropdown": {
                        "value": values.get("zones", "1"),
                        "items": [
                            {"id": "1", "label": {"en": "1 Zone"}},
                            {"id": "2", "label": {"en": "2 Zones"}},
                            {"id": "3", "label": {"en": "3 Zones"}},
                        ],
                    }
                },
            },
        ]
        return RequestUserInput({"en": "Anthem A/V Receiver Setup"}, fields)

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> RequestUserInput | AnthemDeviceConfig:
        """
        Query device and STORE discovered capabilities in config.

        CRITICAL: Discovers inputs during setup so entities have complete SOURCE_LIST!
        """
        host = str(input_values.get("host") or "").strip()
        port_text = str(input_values.get("port") or _DEFAULT_PORT).strip()
        zones_text = str(input_values.get("zones") or "1").strip()
        name = str(input_values.get("name") or "").strip() or f"Anthem ({host})"
        values = {
            "name": str(input_values.get("name") or "").strip(),
            "host": host,
            "port": port_text,
            "zones": zones_text,
        }

        if not host:
            return self.get_manual_entry_form("Enter the receiver's IP address.", values)
        try:
            port = int(port_text)
            if not 0 < port < 65536:
                raise ValueError
        except ValueError:
            return self.get_manual_entry_form(
                f"The port '{port_text}' is not valid. Anthem receivers use port {_DEFAULT_PORT}.", values
            )
        zones_count = int(zones_text) if zones_text in ("1", "2", "3") else 1

        # Keep the identifier on Update so the entity IDs (and the activities using them) stay the same.
        saved = self.selected_config_entry
        identifier = saved.identifier if saved else f"anthem_{host.replace('.', '_')}_{port}"
        zones = [ZoneConfig(zone_number=i) for i in range(1, zones_count + 1)]

        temp_config = AnthemDeviceConfig(
            identifier=identifier,
            name=name,
            host=host,
            port=port,
            zones=zones,
        )

        _LOG.info("SETUP: Connecting to %s:%d for discovery...", host, port)
        discovery_device = AnthemDevice(temp_config)
        try:
            # connect() only starts the background connection, so wait until it is really connected.
            await discovery_device.connect()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + _CONNECT_TIMEOUT
            while not discovery_device.is_connected and loop.time() < deadline:
                await asyncio.sleep(0.2)

            if not discovery_device.is_connected:
                _LOG.error("SETUP: No connection to %s:%d", host, port)
                return self.get_manual_entry_form(
                    f"No connection to {host} on port {port}. Check that the receiver is powered on, "
                    "the IP address is correct, and that the Remote and the receiver are on the same network.",
                    values,
                )

            _LOG.info("SETUP: Connected, waiting for input discovery...")
            deadline = loop.time() + _DISCOVERY_TIMEOUT
            while loop.time() < deadline:
                await asyncio.sleep(0.2)
                if discovery_device._input_count > 0:
                    _LOG.info("SETUP: Input count discovered: %d", discovery_device._input_count)
                    # Wait a bit more for all input names to be discovered
                    await asyncio.sleep(1.0)
                    break

            input_count = discovery_device._input_count
            input_names_dict = discovery_device._input_names.copy()
            discovered_model = discovery_device._model or "Unknown"
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("SETUP: Error - %s", err, exc_info=True)
            return self.get_manual_entry_form(f"Setup failed: {err}", values)
        finally:
            await discovery_device.disconnect()
            _LOG.info("SETUP: Discovery connection closed")

        _LOG.info("SETUP: Model detected: %s", discovered_model)
        if input_names_dict and input_count > 0:
            discovered_inputs = [
                input_names_dict.get(i, f"Input {i}")
                for i in range(1, input_count + 1)
            ]
        else:
            _LOG.warning("SETUP: Input discovery incomplete, using defaults")
            discovered_inputs = list(_DEFAULT_INPUTS)

        _LOG.info(
            "SETUP: Discovery complete - %d inputs %s, %d zone(s)",
            len(discovered_inputs),
            discovered_inputs,
            zones_count,
        )

        return AnthemDeviceConfig(
            identifier=identifier,
            name=name,
            host=host,
            model="AVM",
            port=port,
            zones=zones,
            discovered_inputs=discovered_inputs,
            discovered_model=discovered_model,
        )
