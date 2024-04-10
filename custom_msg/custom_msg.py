import asyncio
from typing import Optional

import discord
from redbot.core import checks, commands

from .interactive_session import InteractiveSession, SessionCancelled, make_session


class CustomMsgCog(commands.Cog):
    @checks.mod()
    @commands.guild_only()
    @commands.group(name="msg")
    async def msg_cmd(self, ctx: commands.Context):
        pass

    @msg_cmd.command(name="create", aliases=["send"])
    async def msg_create(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        if channel is None:
            channel = ctx.channel

        try:
            payload = await make_session(ctx)
        except asyncio.TimeoutError:
            return await ctx.send("Took too long to respond - exiting...")
        except SessionCancelled:
            return await ctx.send("Exiting...")

        message = await channel.send(**payload)
        await ctx.send("Message sent. " +
                       "For future reference, the message is here: " +
                       f"https://discord.com/channels/{ctx.guild.id}/{message.channel.id}/{message.id} (ID: {message.id})")

    @msg_cmd.command(name="edit")
    async def msg_edit(self, ctx: commands.Context, message: discord.Message):
        if message.author != ctx.me:
            return await ctx.send("You must specify a message that was sent by the bot.")

        try:
            payload = await make_session(ctx)
        except asyncio.TimeoutError:
            return await ctx.send("Took too long to respond - exiting...")
        except SessionCancelled:
            return await ctx.send("Exiting...")

        payload = {key: val for key, val in payload.items() if val is not None}

        if not payload.get("content") and message.content:
            if not await InteractiveSession(ctx).get_boolean_answer(
                "The original message has message content, but you have not specified any. " +
                "Would you like to keep the original content?"
            ):
                payload.update({"content": ""})

        if not payload.get("embed") and message.embeds:
            if not await InteractiveSession(ctx).get_boolean_answer(
                "The original message has an embed, but you have not specified one. " +
                "Would you like to keep the original embed?"
            ):
                payload.update({"embed": None})

        await message.edit(**payload)
        await ctx.send("Message edited.")
