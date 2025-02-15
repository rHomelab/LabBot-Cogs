import random

import discord.errors
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page


class BanCountCog(commands.Cog):
    """BanCount cog"""

    REPLACER = "$ban"

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        default_guild_config = {"messages": ["Total users banned: $ban!"]}

        self.config = Config.get_conf(self, identifier=1289862744207523842001)
        self.config.register_guild(**default_guild_config)

    @commands.guild_only()
    @commands.group(name="bancount", pass_context=True, invoke_without_command=True)
    async def _bancount(self, ctx: commands.GuildContext):
        """Displays the total number of users banned."""
        async with self.config.guild(ctx.guild).messages() as messages:
            if len(messages) < 1:
                await ctx.send("Error: guild has no configured messages. Use `[p]bancount add <message>`.")
                return
            message = random.choice(messages)
            try:
                async with ctx.channel.typing():
                    message = message.replace(self.REPLACER, str(len([entry async for entry in ctx.guild.bans(limit=None)])))
            except discord.errors.Forbidden:
                await ctx.send("I don't have permission to retrieve banned users.")
                return
            await ctx.send(message)

    @checks.mod()
    @_bancount.command(name="add")
    async def _bancount_add(self, ctx: commands.GuildContext, *, message: str):
        """Add a message to the message list."""
        if self.REPLACER not in message:
            await ctx.send(f"You need to include `{self.REPLACER}` in your message so I know where to insert the count!")
            return
        async with self.config.guild(ctx.guild).messages() as messages:
            messages.append(message)
        await ctx.send("Message added!")

    @checks.mod()
    @_bancount.command(name="list")
    async def _bancount_list(self, ctx: commands.GuildContext):
        """Lists the message list."""
        async with self.config.guild(ctx.guild).messages() as messages:
            # Credit to the Notes cog author(s) for this pagify structure
            pages = list(pagify("\n".join(f"`{i}) {message}`" for i, message in enumerate(messages))))
            embed_opts = {"title": "Guild's BanCount Message List", "colour": await ctx.embed_colour()}
            embeds = [
                discord.Embed(**embed_opts, description=page).set_footer(text=f"Page {index} of {len(pages)}")
                for index, page in enumerate(pages, start=1)
            ]
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                controls = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}
                ctx.bot.loop.create_task(menu(ctx=ctx, pages=embeds, controls=controls, timeout=180.0))

    @checks.mod()
    @_bancount.command(name="remove")
    async def _bancount_remove(self, ctx: commands.GuildContext, index: int):
        """Removes the specified message from the message list."""
        async with self.config.guild(ctx.guild).messages() as messages:
            if index >= len(messages):
                await ctx.send("Sorry, there isn't a message with that index. Use `[p]bancount list`.")
            else:
                del messages[index]
                await ctx.send("Message deleted!")
