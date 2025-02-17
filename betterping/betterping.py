import contextlib
from time import monotonic

from redbot.core import commands
from redbot.core.bot import Red


class BetterPing(commands.Cog):
    """Upgraded version of the built-in ping command"""

    def __init__(self, bot: Red, old_ping: commands.Command | None):
        self.bot = bot
        self.old_ping = old_ping

    async def cog_unload(self) -> None:
        if self.old_ping:
            with contextlib.suppress(Exception):
                self.bot.remove_command("ping")
                self.bot.add_command(self.old_ping)

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context):
        """Ping command with latency information"""
        # Thanks Vexed01 https://github.com/Vexed01/Vex-Cogs/blob/9d6dbca/anotherpingcog/anotherpingcog.py#L95-L102
        try:
            ws_latency = round(self.bot.latency * 1000)
        except OverflowError:  # ping float is infinity, ie last ping to discord failed
            await ctx.send(
                "I'm alive and working normally, but I've had connection issues in the last few "
                "seconds so precise ping times are unavailable. Try again in a minute.",
            )
            return

        msg = f"**Pong!** \N{TABLE TENNIS PADDLE AND BALL}\nDiscord WS latency: {ws_latency} ms"

        start = monotonic()
        message = await ctx.send(msg)
        end = monotonic()

        m_latency = round((end - start) * 1000)

        new_msg = f"{msg}\nMessage latency: {m_latency} ms"
        await message.edit(content=new_msg)
