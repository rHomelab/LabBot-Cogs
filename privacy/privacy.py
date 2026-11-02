"""discord red-bot privacy policy cog"""

import logging
from pathlib import Path

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.views import SimpleMenu

log = logging.getLogger("red.rhomelab.privacy")

POLICY_FILE = Path(__file__).parent / "privacy_policy.md"
EMBED_PAGE_LENGTH = 3900


class Privacy(commands.Cog):
    """Display the bot's privacy policy."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def _read_policy() -> str | None:
        try:
            text = POLICY_FILE.read_text(encoding="utf-8").strip()
        except OSError as error:
            log.error("Could not read privacy policy file at %s: %s", POLICY_FILE, error)
            return None
        return text or None

    @commands.hybrid_command(name="privacy")
    async def privacy(self, ctx: commands.Context) -> None:
        """Show the bot's privacy policy."""
        policy = self._read_policy()
        if policy is None:
            await ctx.send("Sorry, the privacy policy is currently unavailable. Please contact a moderator.")
            return

        chunks = list(pagify(policy, delims=["\n\n", "\n"], page_length=EMBED_PAGE_LENGTH))
        total = len(chunks)
        colour = await ctx.embed_colour()
        pages: list[dict[str, str | discord.Embed] | discord.Embed | str] = [
            discord.Embed(
                title="LabBot Privacy Policy",
                description=chunk,
                colour=colour,
            ).set_footer(text=f"Page {index}/{total}")
            for index, chunk in enumerate(chunks, start=1)
        ]

        await SimpleMenu(pages, timeout=180).start(ctx)
