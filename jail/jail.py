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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # This is sketch, there might be a better way to do this.
        ctx: commands.Context = await self.bot.get_context(message)

        if isinstance(message.channel, discord.TextChannel):
            cat_channel = await self.config.get_category(message.guild)
            if cat_channel is None:
                return
            if message.channel.category_id == cat_channel.id:
                jailset = await self.config.get_jailset_by_channel(ctx, message.channel)
                if jailset is not None:
                    await self.config.save_message_to_jail(ctx, jailset, message, int(datetime.utcnow().timestamp()))
                    # jailset.log_message(Message.new(ctx, message.id, int(datetime.utcnow().timestamp()), message.author.id, False, 0, message.content, []))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild:
            return

        # This is sketch, there might be a better way to do this.
        ctx: commands.Context = await self.bot.get_context(after)

        if isinstance(after.channel, discord.TextChannel):
            cat_channel = await self.config.get_category(after.guild)
            if cat_channel is None:
                return
            if after.channel.category_id == cat_channel.id:
                jailset = await self.config.get_jailset_by_channel(ctx, after.channel)
                if jailset is not None:
                    jailset.log_edit(Edit.new(ctx, after.id, int(datetime.utcnow().timestamp()), after.content))
                    # await self.config.edit_message(ctx, jailset, after, int(datetime.utcnow().timestamp()))

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
