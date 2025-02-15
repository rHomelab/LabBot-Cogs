"""discord red-bot reactrole cog"""

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class ReactRoleCog(commands.Cog):
    """ReactRole Cog"""

    bot: Red
    config: Config

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=124123498)

        default_guild_settings = {"roles": [], "enabled": True}

        self.config.register_guild(**default_guild_settings)

    def _is_valid_channel(self, channel: discord.guild.GuildChannel | None):
        if channel is not None and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            return channel
        return False

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
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

        if not await self.config.guild(guild).enabled():
            # Go no further if disabled
            return

        async with self.config.guild(guild).roles() as roles:
            for item in roles:
                if item["message"] == payload.message_id and item["reaction"] == str(payload.emoji):
                    role = guild.get_role(item["role"])
                    await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
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

        if not await self.config.guild(guild).enabled():
            # Go no further if disabled
            return

        async with self.config.guild(guild).roles() as roles:
            for item in roles:
                if item["message"] == payload.message_id and item["reaction"] == str(payload.emoji):
                    role = guild.get_role(item["role"])
                    await member.remove_roles(role)

    @commands.group(name="reactrole")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def _reactrole(self, ctx: commands.Context):
        pass

    @_reactrole.command("add")
    @checks.admin()
    async def add_reactrole(
        self,
        ctx: commands.GuildContext,
        message: discord.Message,
        reaction: str,
        role: discord.Role,
    ):
        """Creates a new react role

        Example:
        - `[p]reactrole add <message id> <reaction> <role>`
        """
        data = {"message": message.id, "reaction": reaction, "role": role.id, "channel": message.channel.id}
        async with self.config.guild(ctx.guild).roles() as roles:
            # This should only return 1 item at max because items are checked for uniqueness before adding them
            exists = [item for item in roles if item == data]
            if exists:
                return await ctx.send("React role already exists.")

            try:
                await message.add_reaction(reaction)
            except Exception:
                return await ctx.send("Unable to add emoji message to message")

            roles.append(data)
            await ctx.send("Configured react role.")

    @_reactrole.command("remove")
    async def remove_reactrole(
        self,
        ctx: commands.GuildContext,
        message: discord.Message,
        reaction: str,
        role: discord.Role,
    ):
        """Removes a configured react role

        Example:
        - `[p]reactrole remove 360678601227763712-893601663435276318 :kek: @moderator`
        """
        data = {"message": message.id, "reaction": reaction, "role": role.id, "channel": message.channel.id}
        async with self.config.guild(ctx.guild).roles() as roles:
            # This should only return 1 item at max because items are checked for uniqueness before adding them
            exists = [item for item in roles if item == data]
            if exists:
                roles.remove(data)
                try:
                    await message.clear_reaction(reaction)
                except discord.NotFound:
                    pass
                await ctx.send("React role removed.")
            else:
                return await ctx.send("React role doesn't exist.")

    @_reactrole.command("list")
    async def reactrole_list(self, ctx: commands.GuildContext):
        """Shows a list of react roles configured

        Example:
        - `[p]reactrole list`
        """
        messages = []
        enabled = await self.config.guild(ctx.guild).enabled()
        messages.append(f"Enabled: {enabled}")

        async with self.config.guild(ctx.guild).roles() as roles:
            for item in roles:
                try:
                    role = ctx.guild.get_role(item["role"])
                    _channel = ctx.guild.get_channel(item["channel"])
                    if (channel := self._is_valid_channel(_channel)) and role:
                        message = await channel.fetch_message(item["message"])
                        messages.append(f"📝 {message.jump_url} - {role.name} - {item['reaction']}\n")
                except Exception as exc:
                    print(exc)
                    messages.append("Failed to retrieve 1 result.")

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = list(pagify("\n\n".join(messages), shorten_by=58))

        embeds = [
            discord.Embed(
                title=f"React Roles - Page {index + 1}/{len(pages)}",
                description=page,
                colour=(await ctx.embed_colour()),
            )
            for index, page in enumerate(pages)
        ]

        await menu(
            ctx,
            pages=embeds,
            controls=CUSTOM_CONTROLS,
            timeout=30.0,
        )

    @_reactrole.command("enable")
    async def reactrole_enable(self, ctx: commands.GuildContext):
        """Enables the ReactRole's functionality

        Example:
        - `[p]reactrole enable`
        """
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send("Enabled ReactRole.")

    @_reactrole.command("disable")
    async def reactrole_disable(self, ctx: commands.GuildContext):
        """Disables the ReactRole's functionality

        Example:
        - `[p]reactrole disable`
        """
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.send("Disabled ReactRole.")
