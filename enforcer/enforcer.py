"""discord red-bot enforcer"""

import asyncio
import logging
from typing import ClassVar, Optional, Union, cast

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

KEY_ENABLED = "enabled"
KEY_MINCHARS = "minchars"
KEY_MAXCHARS = "maxchars"
KEY_NOTEXT = "notext"
KEY_NOMEDIA = "nomedia"
KEY_REQUIREMEDIA = "requiremedia"
KEY_MINDISCORDAGE = "minimumdiscordage"
KEY_MINGUILDAGE = "minimumguildage"

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}

log = logging.getLogger("red.rhomelab.enforcer")


class EnforcerCog(commands.Cog):
    """Enforcer Cog"""

    ATTRIBUTES: ClassVar = {
        KEY_ENABLED: {"type": "bool"},
        KEY_MINCHARS: {"type": "number"},
        KEY_MAXCHARS: {"type": "number"},
        KEY_NOTEXT: {"type": "bool"},
        KEY_NOMEDIA: {"type": "bool"},
        KEY_REQUIREMEDIA: {"type": "bool"},
        KEY_MINDISCORDAGE: {"type": "number"},
        KEY_MINGUILDAGE: {"type": "number"},
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987342593)

        default_guild_settings = {
            "channels": [],
            "logchannel": None,
            "userchannel": None,
        }

        self.config.register_guild(**default_guild_settings, force_registration=True)

    def _is_valid_channel(self, channel: "discord.guild.GuildChannel | None"):
        if channel is not None and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            return channel
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return
        if not self.is_valid_message(message):
            return

        # Get channel entry from config
        channels = list(filter(lambda c: c["id"] == message.channel.id, await self.config.guild(message.guild).channels()))
        if not list(channels):
            return

        # Check enforcer rules for channel
        (channel,) = channels
        should_enforce = await self.check_enforcer_rules(channel, message)

        if should_enforce:
            self.bot.dispatch("msg_enforce", message, should_enforce)

    @commands.Cog.listener()
    async def on_msg_enforce(self, message: discord.Message, reason: str):
        if (
            not isinstance(message.guild, discord.Guild)
            or isinstance(message.channel, discord.GroupChannel)
            or isinstance(message.channel, discord.DMChannel)
            or isinstance(message.channel, discord.PartialMessageable)
        ):
            # The user has DM'd us. Ignore.
            return

        await message.delete()

        author = message.author

        data = discord.Embed(color=discord.Color.orange(), description=message.content)
        data.set_author(name=f"Message Enforced - {author}", icon_url=author.display_avatar.url)
        data.add_field(name="Enforced Reason", value=reason, inline=True)
        data.add_field(name="Channel", value=message.channel.mention, inline=True)

        log_id = await self.config.guild(message.guild).logchannel()
        if log_id:
            log_channel = message.guild.get_channel(log_id)
            if channel := self._is_valid_channel(log_channel):
                try:
                    await channel.send(embed=data)
                except discord.Forbidden:
                    await channel.send(f"**Message Enforced** - {author.id} - {author} - Reason: {reason}")
            else:
                log.warning(
                    f"Could not find log channel for guild {message.guild.id}, message was: **Message Enforced** "
                    f"- {author.id} - {author} - Reason: {reason}"
                )

        if not author.dm_channel:
            await author.create_dm()
            dm_channel = cast(discord.DMChannel, author.dm_channel)
        else:
            dm_channel = author.dm_channel
        try:
            await dm_channel.send(embed=data)
        except discord.Forbidden:
            # User does not allow DMs
            inform_id = await self.config.guild(message.guild).userchannel()
            if inform_id:
                inform_channel = message.guild.get_channel(inform_id)
                if channel := self._is_valid_channel(inform_channel):
                    await channel.send(content=author.mention, embed=data)
                else:
                    log.warning(
                        f"Could not find inform channel for guild {message.guild.id}, message was: **Message Enforced** "
                        f"- {author.id} - {author} - Reason: {reason}"
                    )

    @commands.group(name="enforcer")  # type: ignore
    @commands.guild_only()
    @checks.admin()
    async def _enforcer(self, ctx: commands.Context):
        pass

    @_enforcer.command("logchannel")
    async def enforcer_logchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Sets the channel to post the enforcer logs.

        Example:
        - `[p]enforcer logchannel <channel>`
        - `[p]enforcer logchannel #admin-log`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Enforcer log message channel set to `{channel.name}`")

    @_enforcer.command("userchannel")
    async def enforcer_userchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Sets the channel to inform the user of deletion reason, if DMs are unavailable.

        Example:
        - `[p]enforcer userchannel <channel>`
        - `[p]enforcer userchannel #general`
        """
        await self.config.guild(ctx.guild).userchannel.set(channel.id)
        await ctx.send(f"Enforcer user information channel set to `{channel.name}`")

    @_enforcer.command("configure")
    async def enforcer_configure(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        attribute: str,
        *,
        value: Optional[str] = None,
    ):
        """Allows configuration of a channel

        Example:
        - `[p]enforcer configure <channel> <attribute> [value]`

        If `[value]` is not provided, the attribute will be reset.
        Possible attributes are:

        - `enabled` - Is this channel enabled for enforcing. Default false.
        - `minchars` - Minimum characters in a message. Default 0.
        - `maxchars` - Maximum characters in a message. Default 0 (disabled).
        - `notext` - Message must have no text. Default false.
        - `requiremedia` - Message must have an attachment. Default false.
        - `nomedia` - Message must not have an attachment. Default false.
        - `minimumdiscordage` - Account created age in seconds. Default 0.
        - `minimumguildage` - Minimum server joined age in seconds. Default 0.
        """
        attribute = attribute.lower()

        if attribute not in self.ATTRIBUTES:
            await ctx.send("That attribute is not configurable.")
            return

        # Reset the attribute for the channel
        if value is None:
            await self._reset_attribute(channel, attribute)
            await ctx.send("That attribute has been reset.")
            return

        # Validate the input from the user
        try:
            validated_value = await self._validate_attribute_value(attribute, value)
        except ValueError:
            await ctx.send("The given value is invalid for that attribute.")
            return

        await self._set_attribute(channel, attribute, validated_value)
        await ctx.send(f"Channel has now configured the {attribute} attribute.")

    @_enforcer.command("status")
    async def enforcer_status(self, ctx: commands.GuildContext):
        """Prints the status of the enforcement cog

        Example:
        - `[p]enforcer status`
        """
        messages = []
        async with self.config.guild(ctx.guild).channels() as channels:
            for channel_obj in channels:
                channel = ctx.guild.get_channel(channel_obj["id"])
                conf_str = "\n".join(f"{key} - {channel_obj[key]}" for key in self.ATTRIBUTES if key in channel_obj)
                if channel:
                    messages.append(f"📝{channel.mention} - Configuration\n{conf_str}")
                else:
                    messages.append(
                        f"📝Channel ID {channel_obj['id']} no longer exists but has config, remove it... "
                        f"- Configuration\n{conf_str}"
                    )

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = list(pagify("\n\n".join(messages), shorten_by=58))
        embeds = []

        for index, page in enumerate(pages):
            embed = discord.Embed(
                title=f"Enforcement Configuration - Page {index + 1}/{len(pages)}",
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
            await ctx.send("No configurations found")

    async def _validate_attribute_value(self, attribute: str, value: str) -> Union[str, int, bool]:
        attribute_type = self.ATTRIBUTES[attribute]["type"]

        if attribute_type == "bool":
            if value.lower() in ["true", "1", "yes", "y"]:
                return True
            if value.lower() in ["false", "0", "no", "n"]:
                return False
            raise ValueError()

        if attribute_type == "number":
            if not value.isdigit():
                raise ValueError()
            return int(value)
        return value

    async def _reset_attribute(self, channel: discord.TextChannel, attribute: str):
        async with self.config.guild(channel.guild).channels() as channels:
            for _channel in channels:
                if _channel["id"] == channel.id:
                    del _channel[attribute]

    async def _set_attribute(self, channel: discord.TextChannel, attribute, value):
        added = False
        async with self.config.guild(channel.guild).channels() as channels:
            # Check if attribute already exists
            for _channel in channels:
                if _channel["id"] == channel.id:
                    _channel[attribute] = value
                    added = True
                    break

            if added is False:
                # Attribute does not exist for channel
                channels.append({"id": channel.id, attribute: value})

    def is_valid_message(self, message: discord.Message) -> bool:
        """Determines whether a message is worth evaluating"""
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return False

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            # User is a bot. Ignore.
            return False

        return True

    async def check_enforcer_rules(self, channel: dict, message: discord.Message) -> Union[bool, str]:
        """Check message against channel enforcer rules"""
        author = message.author
        enforcer_error = ""

        if not channel.get(KEY_ENABLED):
            # Enforcing not enabled here
            return False

        elif KEY_MINDISCORDAGE in channel and author.created_at:
            delta = discord.utils.utcnow() - author.created_at
            if delta.total_seconds() < channel[KEY_MINDISCORDAGE]:
                # They breached minimum discord age
                enforcer_error = "User account not old enough"

        elif KEY_MINGUILDAGE in channel and isinstance(author, discord.Member) and author.joined_at:
            delta = discord.utils.utcnow() - author.joined_at
            if delta.total_seconds() < channel[KEY_MINGUILDAGE]:
                # They breached minimum guild age
                enforcer_error = "User not in server long enough"

        elif channel.get(KEY_NOTEXT) and not message.content:
            # They breached notext attribute
            enforcer_error = "Message had no text"

        elif (KEY_MINCHARS in channel) and (len(message.content) < channel[KEY_MINCHARS]):
            # They breached minchars attribute
            enforcer_error = "Not enough characters"

        elif (KEY_MAXCHARS in channel) and (len(message.content) > channel[KEY_MAXCHARS]):
            # They breached maxchars attribute
            enforcer_error = "Too many characters"

        elif channel.get(KEY_NOMEDIA) or channel.get(KEY_REQUIREMEDIA):
            # Check the embeds
            embeds = await self.check_embeds(message)
            if channel.get(KEY_NOMEDIA) and (embeds or message.attachments):
                # They breached nomedia attribute
                enforcer_error = "No media allowed"
            if channel.get(KEY_REQUIREMEDIA) and not (embeds or message.attachments):
                # They breached requiremedia attribute
                enforcer_error = "Requires media attached"

        if enforcer_error:
            return enforcer_error
        return False

    async def check_embeds(self, message: discord.Message) -> bool:
        """Waits for Embeds to be generated by Discord's servers"""
        if not message.content:
            # If the message has no text, there will be no embeds
            return False

        for _ in range(4):
            # Fetch the message
            message = await message.channel.fetch_message(message.id)
            if message.embeds and list(filter(lambda e: any(((e.image), (e.thumbnail))), message.embeds)):
                # If there are any embeds with a thumbnail or image property
                return True
            await asyncio.sleep(0.5)
        return False
