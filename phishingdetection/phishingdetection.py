"""discord red-bot phishing link detection"""
import re
from typing import List, Optional, Callable, TypedDict, Literal, Set

import aiohttp
import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red


def api_endpoint(endpoint: str) -> str:
    return f"https://phish.sinking.yachts/v2{endpoint}"


def escape_url(url: str) -> str:
    return url.replace(".", "\.")


class DomainUpdate(TypedDict):
    type: Literal["add", "delete"]
    domains: List[str]


class PhishingDetectionCog(commands.Cog):
    """Phishing link detection cog"""
    bot: Red
    predicate: Optional[Callable[[str], bool]] = None
    urls: Set[str]
    session: aiohttp.ClientSession

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession(headers={
            "X-Identity": "A Red-DiscordBot instance using the phishingdetection cog from https://github.com/rhomelab/labbot-cogs"
        })
        self.initialise_url_set.start()

    def cog_unload(self):
        self.initialise_url_set.cancel()
        self.update_regex.cancel()
        self.bot.loop.run_until_complete(self.session.close())

    @tasks.loop(hours=1.0)
    async def initialise_url_set(self):
        """Fetch the initial list of URLs and set the regex pattern"""
        async with self.session.get(api_endpoint("/all")) as response:
            data: List[str] = await response.json()
            if not isinstance(data, list):
                # Could be an error message
                return

            self.urls = set(data)
            self.update_predicate()

        self.update_regex.start()
        self.initialise_url_set.cancel()

    @tasks.loop(hours=1.0)
    async def update_regex(self):
        """Fetch the list of phishing URLs and update the regex pattern"""
        async with self.session.get(api_endpoint("/recent/3660")) as response:  # TODO: Use the websocket API to get live updates
            # Using 3660 (1 hour + 1 minute) instead of 3600 (1 hour) to prevent missing updates
            # This is fine, as we store the URLs in a set, so duplicate add/remove operations do not result in missing/duplicate data
            updates: List[DomainUpdate] = await response.json()
            for update in updates:
                action: Callable[[str], None]
                if update["type"] == "add":
                    action = self.urls.add
                elif update["type"] == "delete":
                    action = self.urls.remove

                for domain in update["domains"]:
                    try:
                        action(domain)  # Add or remove from set
                    except KeyError:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.predicate is None:
            # It's possible that the initialisation task has not completed yet
            return

        if not self.predicate(message.content):
            # No phishing links detected
            return

        await message.delete()
        # TODO: Maybe log this somewhere?

    def update_predicate(self):
        pattern = re.compile("|".join(escape_url(url) for url in self.urls))

        def predicate(content: str) -> bool:
            return bool(pattern.search(content))

        self.predicate = predicate
