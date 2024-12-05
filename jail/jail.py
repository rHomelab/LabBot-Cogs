from datetime import datetime

import discord
from discord import CategoryChannel
from redbot.core import commands, checks
from redbot.core.bot import Red

from jail.utils import JailConfigHelper, Message, Edit


class JailCog(commands.Cog):
    """Jail cog"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = JailConfigHelper()

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
        """Sets the jail category channel."""
        channel = ctx.guild.get_channel(cat_id)
        if not isinstance(channel, CategoryChannel):
            await ctx.send("Sorry, that's not a category channel.")
            return
        await self.config.set_category(ctx, channel)
        await ctx.send("Channel category set!")

    @_jail.command("free")
    async def _jail_setup(self, ctx: commands.Context, user: discord.User):
        """Frees the specified user from the jail."""
        jail = await self.config.get_jail_by_user(ctx, user)
        if jail is None or not jail.active:
            await ctx.send("That user isn't in jail!")
            return
        member = ctx.guild.get_member(user.id)
        if member is not None:
            await self.config.free_user(ctx, jail, member)
        else:
            await ctx.send("Error getting member! Cannot free them. I'll cleanup the jail and role though.")
        await self.config.cleanup_jail(ctx, jail)
