from datetime import datetime

import discord
from discord import CategoryChannel
from redbot.core import commands, checks
from redbot.core.bot import Red

from jail.utils import JailConfigHelper


class JailCog(commands.Cog):
    """Jail cog"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = JailConfigHelper()

    # @commands.Cog.listener()
    # async def on_message(self, message: discord.Message):
    #     ctx = await self.bot.get_context(message)
    #     if message.author.bot or not message.guild:
    #         return
    #     if isinstance(message.channel, discord.TextChannel):
    #         if message.channel.category_id == (await self.config.get_category(ctx)).id:
    #             jail = await self.config.get_jail_by_channel(ctx, message.channel)
    #             if jail is not None:
    #                 # TODO Log message to jail
    #                 pass

    @checks.mod()
    @commands.guild_only()
    @commands.group("jail", pass_context=True, invoke_without_command=True)
    async def _jail(self, ctx: commands.Context, member: discord.Member):
        """Jails the specified user."""
        jail = await self.config.create_jail(ctx, int(datetime.utcnow().timestamp()), member)
        if jail is None:
            await ctx.send("Sorry, there was an error with jail category. Make sure things are setup correctly!")
            return
        await self.config.jail_user(ctx, jail, member)
        await ctx.send("User has been jailed!")

    @checks.admin()
    @_jail.command("setup")
    async def _jail_setup(self, ctx: commands.Context, cat_id: int):
        """Sets the jail category and template channel."""
        channel = ctx.guild.get_channel(cat_id)
        if not isinstance(channel, CategoryChannel):
            await ctx.send("Sorry, that's not a category channel.")
            return
        await self.config.set_category(ctx, channel)
        await ctx.send("Channel category set!")
