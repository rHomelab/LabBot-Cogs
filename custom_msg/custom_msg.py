import asyncio
from typing import Any, Awaitable, Callable, Optional

import discord
from redbot.core import checks, commands

from .interactive_session import SessionCancelled, make_session, InteractiveSession


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

        async def callback(**kwargs):
            message = await channel.send(**kwargs)
            await ctx.send(f"Message sent.\nFor future reference, the message ID is {message.channel.id}-{message.id}")

        await self.handle_session(ctx, callback)

    @msg_cmd.command(name="edit")
    async def msg_edit(self, ctx: commands.Context, message: discord.Message):
        if message.author != ctx.me:
            return await ctx.send("You must specify a message that was sent by the bot.")

        if message.content and message.embeds:
            session = InteractiveSession(ctx)
            callbacks = {""}

        await self.handle_session(ctx, message.edit)
        await ctx.send("Message edited.")

    @staticmethod
    async def handle_session(ctx: commands.Context, callback: Callable[[Any], Awaitable[None]]):
        try:
            payload = await make_session(ctx)
            await callback(**payload)
        except asyncio.TimeoutError:
            await ctx.send("Took too long to respond, exiting...")
        except SessionCancelled:
            await ctx.send("Exiting...")
