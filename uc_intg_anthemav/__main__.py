"""
Entry point for running the integration as a module.

This allows running: python -m uc_intg_anthemav

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
from . import main

if __name__ == "__main__":
    asyncio.run(main())