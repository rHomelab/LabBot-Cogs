"""discord red-bot phishing link detection"""

import re
from typing import Callable, List, Literal, Optional, Set, TypedDict

import aiohttp
import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red


def api_endpoint(endpoint: str) -> str:
    return f"https://phish.sinking.yachts/v2{endpoint}"


def generate_predicate_from_urls(urls: Set[str]) -> Callable[[str], bool]:
    urls_section = "|".join(re.escape(url) for url in urls)
    pattern = re.compile(f"(^| )(http[s]?://)?(www\\.)?({urls_section})(/|/[^ \n]+)?($| )")

    def predicate(content: str) -> bool:
        return bool(pattern.search(content))

    return predicate


class DomainUpdate(TypedDict):
    type: Literal["add", "delete"]
    domains: List[str]


async def get_all_urls(session: aiohttp.ClientSession) -> Set[str]:
    async with session.get(api_endpoint("/all")) as response:
        urls: List[str] = await response.json()
        if not isinstance(urls, list) or not all([isinstance(i, str) for i in urls]):
            raise TypeError
        return set(urls)


async def get_updates_from_timeframe(session: aiohttp.ClientSession, num_seconds: int) -> List[DomainUpdate]:
    async with session.get(api_endpoint(f"/recent/{num_seconds}")) as response:
        updates: List[DomainUpdate] = await response.json()
        if not isinstance(updates, list):
            raise TypeError
        return updates


class PhishingDetectionCog(commands.Cog):
    """Phishing link detection cog"""

    bot: Red
    predicate: Optional[Callable[[str], bool]] = None
    urls: Set[str]
    session: aiohttp.ClientSession

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={
                "X-Identity": "A Red-DiscordBot instance using the phishingdetection cog from https://github.com/rhomelab/labbot-cogs"
            }
        )
        self.initialise_url_set.start()

    def cog_unload(self):
        self.initialise_url_set.cancel()
        self.update_urls.cancel()
        self.bot.loop.run_until_complete(self.session.close())

    @tasks.loop(hours=1.0)
    async def initialise_url_set(self):
        """Fetch the initial list of URLs and set the regex pattern"""
        try:
            urls = await get_all_urls(self.session)
        except TypeError:
            return

        self.urls = urls
        self.predicate = generate_predicate_from_urls(self.urls)

        self.update_urls.start()
        self.initialise_url_set.cancel()

    @tasks.loop(hours=1.0)
    async def update_urls(self):
        """Fetch the list of phishing URLs and update the regex pattern"""
        # TODO: Use the websocket API to get live updates
        # Using 3660 (1 hour + 1 minute) instead of 3600 (1 hour) to prevent missing updates
        # This is fine, as we store the URLs in a set, so duplicate add/remove operations do not result in missing/duplicate data
        updates = await get_updates_from_timeframe(self.session, 3600)
        for update in updates:
            if update["type"] == "add":
                for domain in update["domains"]:
                    self.urls.add(domain)
            elif update["type"] == "delete":
                for domain in update["domains"]:
                    try:
                        self.urls.remove(domain)
                    except KeyError:
                        pass

        self.predicate = generate_predicate_from_urls(self.urls)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.predicate is None:
            # It's possible that the initialisation task has not completed yet
            return

        if not self.predicate(message.content):
            # No phishing links detected
            return

        # TODO: Maybe log this somewhere?
        await message.delete()
