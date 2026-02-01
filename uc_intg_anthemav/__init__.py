"""
Anthem A/V Receivers Integration for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os

from ucapi import DeviceStates
from ucapi_framework import get_config_path, BaseConfigManager

from uc_intg_anthemav.driver import AnthemDriver
from uc_intg_anthemav.setup_flow import AnthemSetupFlow
from uc_intg_anthemav.config import AnthemDeviceConfig

__version__ = "1.4.16"

_LOG = logging.getLogger(__name__)


async def main():
    """Main entry point for the Anthem A/V integration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Suppress websocket handshake errors (normal noise from port probing)
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    _LOG.info("Starting Anthem A/V Integration v%s", __version__)

    try:
        # Create driver
        driver = AnthemDriver()
        config_path = get_config_path(driver.api.config_dir_path or "")
        config_manager = BaseConfigManager(
            config_path,
            add_handler=driver.on_device_added,
            remove_handler=driver.on_device_removed,
            config_class=AnthemDeviceConfig,
        )
        driver.config_manager = config_manager

        # Create setup handler using framework (will use form from driver.json)
        setup_handler = AnthemSetupFlow.create_handler(driver)

        # Initialize API with driver.json and setup handler
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        await driver.api.init(os.path.abspath(driver_path), setup_handler)

        # Register all configured devices
        await driver.register_all_configured_devices(connect=False)

        # Set initial state
        device_count = len(list(config_manager.all()))
        if device_count > 0:
            _LOG.info("Configured with %d device(s)", device_count)
            await driver.api.set_device_state(DeviceStates.CONNECTED)
        else:
            _LOG.info("No devices configured, waiting for setup")
            await driver.api.set_device_state(DeviceStates.DISCONNECTED)

        _LOG.info("=" * 70)
        _LOG.info("✅ Anthem integration started successfully")
        _LOG.info("=" * 70)
        _LOG.info("Integration is running and listening on port 9090")
        _LOG.info("Ready to connect simulator or configure devices")
        _LOG.info("Press Ctrl+C to stop")
        _LOG.info("=" * 70)

        # Keep running indefinitely
        await asyncio.Future()

    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user")
    except asyncio.CancelledError:
        _LOG.info("Integration task cancelled")
    except Exception as err:
        _LOG.critical("Fatal error: %s", err, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
