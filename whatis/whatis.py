from typing import Any

import discord
from redbot.core import commands
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page
from redbot.core.utils.mod import is_mod_or_superior

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class WhatIsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command("whatis")
    async def what_is(self, ctx, arg: str):
        converters = (
            commands.MemberConverter,
            commands.UserConverter,
            commands.MessageConverter,
            commands.PartialMessageConverter,
            commands.TextChannelConverter,
            commands.VoiceChannelConverter,
            commands.StageChannelConverter,
            commands.StoreChannelConverter,
            commands.CategoryChannelConverter,
            commands.InviteConverter,
            commands.GuildConverter,
            commands.RoleConverter,
            commands.GameConverter,
            commands.ColourConverter,
            commands.EmojiConverter,
            commands.PartialEmojiConverter,
        )
        is_mod = await is_mod_or_superior(self.bot, ctx.author)

        objects = []
        for converter in converters:
            try:
                object = await converter().convert(ctx, arg)
                objects.append(object)
            except discord.DiscordException:
                pass

        embeds = [await self.make_embed(object=o, is_mod=is_mod) for o in objects]
        if embeds:
            await menu(
                ctx,
                pages=embeds,
                controls=CUSTOM_CONTROLS,
                message=None,
                page=0,
                timeout=30,
            )
        else:
            await ctx.send("No objects found.")

    async def make_embed(self, object: Any, is_mod: bool) -> discord.Embed:
        """Generate embed from Discord object"""
