"""discord red-bot reactrole cog"""
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class ReactRoleCog(commands.Cog):
    """ReactRole Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=124123498)

        default_guild_settings = {"roles": [], "enabled": True}

        self.settings.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Member adds reaction to a message
        """

        if not payload.member:
            # TODO Log error
            return

        if payload.member.bot:
            # Go no further if member is a bot
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Guild shouldn't be none
            return

        if not await self.settings.guild(guild).enabled():
            # Go no further if disabled
            return

        async with self.settings.guild(guild).roles() as roles:
            for item in roles:
                if item["message"] == payload.message_id and item["reaction"] == str(
                    payload.emoji
                ):
                    role = guild.get_role(item["role"])
                    await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        Member removes reaction from a message
        """
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            # Guild shouldn't be none
            return

        member = guild.get_member(payload.user_id)

        if member.bot:
            # Go no further if member is a bot
            return

        if not await self.settings.guild(guild).enabled():
            # Go no further if disabled
            return

        async with self.settings.guild(guild).roles() as roles:
            for item in roles:
                if item["message"] == payload.message_id and item["reaction"] == str(
                    payload.emoji
                ):
                    role = guild.get_role(item["role"])
                    await member.remove_roles(role)

    @commands.group(name="reactrole")
    @commands.guild_only()
    @checks.mod()
    async def _reactrole(self, ctx: commands.Context):
        pass

    @_reactrole.command("add")
    @checks.admin()
    async def add_reactrole(
        self,
        ctx: commands.Context,
        message: discord.Message,
        reaction: str,
        role: discord.Role,
    ):
        """Creates a new react role

        Example:
        - `[p]reactrole add <message id> <reaction> <role>`
        """
        async with self.settings.guild(ctx.guild).roles() as roles:
            added = False

            for item in roles:
                # Check if a result already exists
                if (
                    item["message"] == message.id
                    and item["reaction"] == str(reaction)
                    and item["role"] == role.id
                    and item["channel"] == message.channel.id
                ):
                    added = True

            if added:
                await ctx.send("React Role already exists.")
            else:
                try:
                    await message.add_reaction(str(reaction))

                    roles.append(
                        {
                            "message": message.id,
                            "reaction": str(reaction),
                            "role": role.id,
                            "channel": message.channel.id,
                        }
                    )
                    await ctx.send("Configured React Role.")
                except Exception:
                    await ctx.send("Unable to add emoji message to message")

    @_reactrole.command("remove")
    async def remove_reactrole(
        self,
        ctx: commands.Context,
        message: discord.Message,
        reaction: str,
        role: discord.Role,
    ):
        """Removes a configured react role

        Example:
        - `[p]reactrole remove <message id> <reaction> <role>`
        """
        async with self.settings.guild(ctx.guild).roles() as roles:
            exists = False

            for item in roles:
                # Check if a result already exists
                if (
                    item["message"] == message.id
                    and item["reaction"] == str(reaction)
                    and item["role"] == role.id
                    and item["channel"] == message.channel.id
                ):
                    exists = item

            roles.remove(exists)

            if exists:
                await ctx.send("React Role removed.")
            else:
                await ctx.send("React Role didn't exist.")

    @_reactrole.command("list")
    async def reactrole_list(self, ctx: commands.Context):
        """Shows a list of react roles configured

        Example:
        - `[p]reactrole list`
        """
        messages = []
        enabled = await self.settings.guild(ctx.guild).enabled()
        messages.append(f"Enabled: {enabled}")

        async with self.settings.guild(ctx.guild).roles() as roles:
            for item in roles:
                try:
                    role = ctx.guild.get_role(item["role"])
                    channel = ctx.guild.get_channel(item["channel"])
                    message = await channel.fetch_message(item["message"])
                    messages.append(
                        f"📝 {message.jump_url} " f'- {role.name} - {item["reaction"]}\n'
                    )
                except Exception as exc:
                    print(exc)
                    messages.append("Failed to retrieve 1 result.")

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = pagify("\n\n".join(messages), shorten_by=58)
        embeds = []
        for index, page in enumerate(pages):
            embed = discord.Embed(
                title=f"React Roles - Page {index + 1}/{len(list(pages))}",
                description=page,
                colour=(await ctx.embed_colour()),
            )
            embeds.append(embed)

        await menu(
            ctx,
            pages=embeds,
            controls=CUSTOM_CONTROLS,
            timeout=30.0,
        )

    @_reactrole.command("enable")
    async def reactrole_enable(self, ctx):
        """Enables the ReactRole's functionality

        Example:
        - `[p]reactrole enable`
        """
        await self.settings.guild(ctx.guild).enabled.set(True)
        await ctx.send("Enabled ReactRole.")

    @_reactrole.command("disable")
    async def reactrole_disable(self, ctx):
        """Disables the ReactRole's functionality

        Example:
        - `[p]reactrole disable`
        """
        await self.settings.guild(ctx.guild).enabled.set(False)
        await ctx.send("Disabled ReactRole.")
