import asyncio
import atexit
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientSession


class RatesAPI:
    def __init__(self, url: str) -> None:
        self.url = url
        self.session: Optional[ClientSession] = None
        atexit.register(self._shutdown)

    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get new aiohttp session
        :return: session
        """
        if not self.session:
            connector = aiohttp.TCPConnector(limit=0)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    def _shutdown(self) -> None:
        """
        Shutdown session
        :return: None
        """
        if self.session:
            asyncio.run(self.session.close())

    @property
    async def rates(self) -> Dict[str, Any]:
        """
        Get response from API with rates
        :return:
        """
        session = await self.get_session()
        async with session.get(self.url) as response:
            return await response.json()
