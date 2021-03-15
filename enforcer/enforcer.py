"""discord red-bot enforcer"""
from datetime import datetime

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

KEY_ENABLED = "enabled"
KEY_MINCHARS = "minchars"
KEY_NOTEXT = "notext"
KEY_NOMEDIA = "nomedia"
KEY_REQUIREMEDIA = "requiremedia"
KEY_MINDISCORDAGE = "minimumdiscordage"
KEY_MINGUILDAGE = "minimumguildage"

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class EnforcerCog(commands.Cog):
    """Enforcer Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=987342593)
        self.attributes = {
            KEY_ENABLED: {"type": "bool"},
            KEY_MINCHARS: {"type": "number"},
            KEY_NOTEXT: {"type": "bool"},
            KEY_NOMEDIA: {"type": "bool"},
            KEY_REQUIREMEDIA: {"type": "bool"},
            KEY_MINDISCORDAGE: {"type": "number"},
            KEY_MINGUILDAGE: {"type": "number"},
        }

        default_guild_settings = {
            "channels": [],
            "logchannel": None,
            "userchannel": None,
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            # User is a bot. Ignore.
            return

        delete = None

        async with self.settings.guild(message.guild).channels() as channels:
            for channel in channels:
                if not channel["id"] == message.channel.id:
                    # Not relating to this channel
                    continue

                if KEY_ENABLED not in channel or not channel[KEY_ENABLED]:
                    # Enforcing not enabled here
                    continue

                if KEY_MINCHARS in channel:
                    if len(message.content) < channel[KEY_MINCHARS]:
                        # They breached minchars attribute
                        delete = "Not enough characters"
                        break

                if KEY_NOMEDIA in channel and channel[KEY_NOMEDIA] is True:
                    if len(message.attachments) > 0:
                        # They breached nomedia attribute
                        delete = "No media attached"
                        break

                if KEY_REQUIREMEDIA in channel and channel[KEY_REQUIREMEDIA] is True:
                    if not message.attachments and not message.embeds:
                        # They breached requiremedia attribute
                        delete = "Requires media attached"
                        break

                if KEY_NOTEXT in channel and channel[KEY_NOTEXT] is True:
                    if len(message.content) > 0:
                        # They breached notext attribute
                        delete = "Message had no text"
                        break

                if KEY_MINDISCORDAGE in channel:
                    if author.created_at is None:
                        # They didn't have a created_at date?
                        break

                    delta = datetime.utcnow() - author.created_at
                    if delta.total_seconds() < channel[KEY_MINDISCORDAGE]:
                        # They breached minimum discord age
                        delete = "User account not old enough"
                        break

                if KEY_MINGUILDAGE in channel:
                    if author.joined_at is None:
                        # They didn't have a joined_at date?
                        break

                    delta = datetime.utcnow() - author.joined_at
                    if delta.total_seconds() < channel[KEY_MINGUILDAGE]:
                        # They breached minimum guild age
                        delete = "User not in server long enough"
                        break

        if delete:
            await message.delete()

            data = discord.Embed(
                color=discord.Color.orange(), description=message.content
            )
            data.set_author(
                name=f"Message Enforced - {author}", icon_url=author.avatar_url
            )
            data.add_field(name="Enforced Reason", value=delete, inline=True)
            data.add_field(
                name="Channel", value=message.channel.mention, inline=True)

            log_id = await self.settings.guild(message.guild).logchannel()
            if log_id:
                log_channel = message.guild.get_channel(log_id)
                if log_channel:
                    try:
                        await log_channel.send(embed=data)
                    except discord.Forbidden:
                        await log.send(f"**Message Enforced** - {author.id} - {author} - Reason: {delete}")

            if not author.dm_channel:
                await author.create_dm()

            try:
                await author.dm_channel.send(embed=data)
            except discord.Forbidden:
                # User does not allow DMs
                inform_id = await self.settings.guild(message.guild).userchannel()
                if inform_id:
                    inform_channel = message.guild.get_channel(inform_id)
                    if inform_channel:
                        await inform_channel.send(content=author.mention, embed=data)

    @commands.group(name="enforcer")
    @commands.guild_only()
    @checks.admin()
    async def _enforcer(self, ctx: commands.Context):
        pass

    @_enforcer.command("logchannel")
    async def enforcer_logchannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Sets the channel to post the enforcer logs.

        Example:
        - `[p]enforcer logchannel <channel>`
        - `[p]enforcer logchannel #admin-log`
        """
        await self.settings.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Enforcer log message channel set to `{channel.name}`")

    @_enforcer.command("userchannel")
    async def enforcer_userchannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Sets the channel to inform the user of deletion reason, if DMs are unavailable.

        Example:
        - `[p]enforcer userchannel <channel>`
        - `[p]enforcer userchannel #general`
        """
        await self.settings.guild(ctx.guild).userchannel.set(channel.id)
        await ctx.send(f"Enforcer user information channel set to `{channel.name}`")

    @_enforcer.command("configure")
    async def enforcer_configure(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        attribute: str,
        *,
        value: str = None,
    ):
        """Allows configuration of a channel

        Example:
        - `[p]enforcer configure <channel> <attribute> [value]`

        If `[value]` is not provided, the attribute will be reset.
        Possible attributes are:

        - `enabled` - Is this channel enabled for enforcing. Default false.
        - `minchars` - Minimum characters in a message. Default 0.
        - `notext` - Message must have no text. Default false.
        - `requiremedia` - Message must have an attachment. Default false.
        - `nomedia` - Message must not have an attachment. Default false.
        - `minimumdiscordage` - Account created age in seconds. Default 0.
        - `minimumguildage` - Minimum server joined age in seconds. Default 0.
        """
        attribute = attribute.lower()

        if attribute not in self.attributes:
            await ctx.send("That attribute is not configurable.")
            return

        # Reset the attribute for the channel
        if value is None:
            await self._reset_attribute(channel, attribute)
            await ctx.send("That attribute has been reset.")
            return

        # Validate the input from the user
        try:
            await self._validate_attribute_value(attribute, value)
        except ValueError:
            await ctx.send("The given value is invalid for that attribute.")
            return

        await self._set_attribute(channel, attribute, value)
        await ctx.send(f"Channel has now configured the {attribute} attribute.")

    @_enforcer.command("status")
    async def enforcer_status(self, ctx: commands.Context):
        """Prints the status of the enforcement cog

        Example:
        - `[p]enforcer status`
        """
        messages = []
        async with self.settings.guild(ctx.guild).channels() as channels:
            for channel_obj in channels:
                channel = ctx.guild.get_channel(channel_obj["id"])

                conf_str = "\n".join(f"{key} - {channel_obj[key]}" for key in self.attributes if key in channel_obj)

                messages.append(f"📝{channel.mention} - Configuration\n{conf_str}")

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = pagify("\n\n".join(messages), shorten_by=58)
        embeds = []

        for index, page in enumerate(pages):
            embed = discord.Embed(
                title=f"Enforcement Configuration - Page {index + 1}/{len(list(pages))}",
                description=page,
                colour=(await ctx.embed_colour()),
            )
            embeds.append(embed)

        if embeds:
            await menu(
                ctx,
                pages=embeds,
                controls=CUSTOM_CONTROLS,
                timeout=30.0,
            )
        else:
            ctx.send("No configurations found")

    async def _validate_attribute_value(self, attribute: str, value: str):
        attribute_type = self.attributes[attribute]["type"]

        if attribute_type == "bool":
            if value in ["true", "1", "yes", "y"]:
                return True
            if value in ["false", "0", "no", "n"]:
                return False
            raise ValueError()
        if attribute_type == "number":
            value = int(value)

            return value

        return None

    async def _reset_attribute(self, channel: discord.TextChannel, attribute):
        async with self.settings.guild(channel.guild).channels() as channels:
            for _channel in channels:
                if _channel["id"] == channel.id:
                    del _channel[attribute]

    async def _set_attribute(self, channel: discord.TextChannel, attribute, value):
        added = False
        async with self.settings.guild(channel.guild).channels() as channels:
            # Check if attribute already exists
            for _channel in channels:
                if _channel["id"] == channel.id:
                    _channel[attribute] = value
                    added = True
                    break

            if added is False:
                # Attribute does not exist for channel
                channels.append({"id": channel.id, attribute: value})
