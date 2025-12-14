"""
Anthem A/V Receivers Integration for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import os

from ucapi_framework import BaseConfigManager

from uc_intg_anthemav.config import AnthemDeviceConfig
from uc_intg_anthemav.device import AnthemDevice
from uc_intg_anthemav.driver import AnthemDriver
from uc_intg_anthemav.setup_flow import AnthemSetupFlow

_LOG = logging.getLogger(__name__)


def _get_version():
    """Get version from driver.json."""
    try:
        driver_path = os.path.join(os.path.dirname(__file__), "driver.json")
        if not os.path.exists(driver_path):
            driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        
        with open(driver_path, 'r', encoding='utf-8') as f:
            driver_data = json.load(f)
            return driver_data.get('version', '0.3.2')
    except Exception as e:
        _LOG.warning(f"Could not read version from driver.json: {e}")
        return "0.3.2"


__version__ = _get_version()


async def main():
    """Main entry point for Anthem integration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    _LOG.info("Starting Anthem A/V Integration v%s", __version__)
    
    loop = asyncio.get_running_loop()
    config_dir = os.getenv("UC_CONFIG_HOME", "./config")
    
    config_manager = BaseConfigManager[AnthemDeviceConfig](
        data_path=config_dir
    )
    
    driver = AnthemDriver(loop)
    
    driver.register_setup_handler(AnthemSetupFlow, config_manager)
    
    await driver.run()


def run():
    """Run the integration."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user")
    except Exception as e:
        _LOG.error(f"Integration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()