import asyncio

import discord
from redbot.core import checks, commands

from .interactive_session import SessionCancelled, make_session


class CustomMsgCog(commands.Cog):
    @checks.mod()
    @commands.guild_only()
    @commands.group(name="msg")
    async def msg_cmd(self, ctx: commands.Context):
        pass

    @msg_cmd.command(name="create", aliases=["send"])
    async def msg_create(self, ctx: commands.Context, channel: discord.TextChannel):
        try:
            payload = await make_session(ctx)
            message = await channel.send(**payload)
            await ctx.send(f"Message sent.\nFor future reference, the message ID is {message.channel.id}-{message.id}")
        except asyncio.TimeoutError:
            await ctx.send("Took too long to respond, exiting...")
        except SessionCancelled:
            await ctx.send("Exiting...")

    @msg_cmd.command(name="edit")
    async def msg_edit(self, ctx: commands.Context, message: discord.Message):
        if message.author != ctx.me:
            return await ctx.send("You must specify a message that was sent by the bot.")

        try:
            payload = await make_session(ctx)
            message = await message.edit(**payload)
            await ctx.send("Message edited.")
        except asyncio.TimeoutError:
            await ctx.send("Took too long to respond, exiting...")
        except SessionCancelled:
            await ctx.send("Exiting...")
