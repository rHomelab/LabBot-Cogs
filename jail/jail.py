import uuid
from datetime import datetime
from io import BytesIO
from os import path
from typing import Optional

import discord
from discord import CategoryChannel
from redbot.core import checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

from jail.utils import JailConfigHelper


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
    async def _jail_free(self, ctx: commands.Context, user: discord.User):
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
        await ctx.send("User has been freed!")

    @_jail.group("archives", pass_context=True, invoke_without_command=True)
    async def _jail_archives(self, ctx: commands.Context, user: discord.User):
        """Lists all archives for a given user."""
        # Code from the Notes cog, with applicable modifications
        jailset = await self.config.get_jailset_by_user(ctx, user)
        if not jailset:
            return await ctx.send("No jails found for that user.")
        jails = jailset.jails
        if not jails:
            return await ctx.send("Jail Set for user found, but no jails within.")
        num_jails = len(jails)
        pages = list(pagify("\n\n".join(str(j) for j in jails)))

        # Create embeds from pagified data
        jails_target: Optional[str] = getattr(user, "display_name", str(user.id)) if user is not None else None
        base_embed_options = {
            "title": ((f"Jail archives for {jails_target}" if jails_target else "All jails") + f" - ({num_jails} jails)"),
            "colour": await ctx.embed_colour(),
        }
        embeds = [
            discord.Embed(**base_embed_options, description=page).set_footer(text=f"Page {index} of {len(pages)}")
            for index, page in enumerate(pages, start=1)
        ]

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            ctx.bot.loop.create_task(
                menu(ctx=ctx, pages=embeds, controls={"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}, timeout=180.0)
            )

    @_jail_archives.command("fetch")
    async def _jail_archives_fetch(self, ctx: commands.Context, archive_id: uuid.UUID):
        """Fetches and sends the specified archive."""
        data_path = data_manager.cog_data_path(self.config)
        archive_file = f"{archive_id}.html"
        archive_path = path.join(data_path, archive_file)

        async with ctx.typing():
            try:
                with open(archive_path, "r") as file:
                    data = file.read()
                    transmit = discord.File(BytesIO(initial_bytes=data.encode()), filename=archive_file)
                    await ctx.send(file=transmit)
            except Exception as e:
                await ctx.send(
                    "Error fetching archive. Likely file not found, maybe a permissions issue. "
                    "Check the console for details."
                )
                print(e)
