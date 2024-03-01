import random

from redbot.core import commands, Config, checks
from redbot.core.bot import Red


class BanCountCog(commands.Cog):
    """BanCount cog"""

    REPLACER = "$ban"

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        default_guild_config = {
            "messages": [
                "Total users banned: $ban!"
            ]
        }

        self.config = Config.get_conf(self, identifier=1289862744207523842001)
        self.config.register_guild(**default_guild_config)

    @commands.guild_only()
    @commands.group(name="bancount", pass_context=True, invoke_without_command=True)
    async def _bancount(self, ctx: commands.Context):
        """Displays the total number of users banned."""
        async with self.config.guild(ctx.guild).messages() as messages:
            if len(messages) < 1:
                await ctx.send("Error: guild has no configured messages. Use `[p]bancount add <message>`.")
                return
            message = random.choice(messages)
            message = message.replace(self.REPLACER, int(len([entry async for entry in ctx.guild.bans()])))
            await ctx.send(message)

    @checks.mod()
    @_bancount.command(name="add")
    async def _bancount_add(self, ctx: commands.Context, message: str):
        """Add a message to the message list."""
        if self.REPLACER not in message:
            await ctx.send(
                f"You need to include `{self.REPLACER}` in your message so I know where to insert the count!")
            return
        async with self.config.guild(ctx.guild).messages() as messages:
            messages.append(message)
        await ctx.send("Message added!")

    @checks.mod()
    @_bancount.command(name="list")
    async def _bancount_list(self, ctx: commands.Context):
        """Lists the message list."""
        async with self.config.guild(ctx.guild).messages() as messages:
            message_list = [f"`{i}) {message}`" for i, message in messages]
        await ctx.send("\n".join(message_list))

    @checks.mod()
    @_bancount.command(name="remove")
    async def _bancount_remove(self, ctx: commands.Context, index: int):
        """Removes the specified message from the message list."""
        async with self.config.guild(ctx.guild).messages() as messages:
            if index >= len(messages):
                await ctx.send("Sorry, there isn't a message with that index. Use `[p]bancount list`.")
            else:
                del messages[index]
                await ctx.send("Message deleted!")