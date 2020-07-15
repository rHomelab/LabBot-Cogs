"""discord red-bot enforcer"""
import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, prev_page, close_menu, next_page
from datetime import datetime

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
            KEY_ENABLED: {
                "type": "bool"
            },
            KEY_MINCHARS: {
                "type": "number"
            },
            KEY_NOTEXT: {
                "type": "bool"
            },
            KEY_NOMEDIA: {
                "type": "bool"
            },
            KEY_REQUIREMEDIA: {
                "type": "bool"
            },
            KEY_MINDISCORDAGE: {
                "type": "number"
            },
            KEY_MINGUILDAGE: {
                "type": "number"
            }
        }

        default_guild_settings = {
            "channels": [],
            "logchannel": None
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="enforcer")
    @commands.guild_only()
    @checks.admin()
    async def _enforcer(self, ctx: commands.Context):
        pass

    @_enforcer.command("logchannel")
    async def enforcer_logchannel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
    ):
        """Sets the channel to post the enforcer logs.

        Example:
        - `[p]enforcer logchannel <channel>`
        - `[p]enforcer logchannel #admin-log`
        """
        await self.settings.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Enforcer log message channel set to `{channel.name}`")

    async def _validate_attribute_value(self, attribute: str, value: str):
        attribute_type = self.attributes[attribute]["type"]

        if attribute_type == "bool":
            if value in [
                "true",
                "1",
                "yes",
                "y"
            ]:
                return True
            elif value in [
                "false",
                "0",
                "no",
                "n"
            ]:
                return False
            else:
                raise ValueError()
        elif attribute_type == "number":
            value = int(value)

            return value

        return None

    async def _reset_attribute(self, channel: discord.TextChannel, attribute):
        async with self.settings.guild(channel.guild).channels() as li:
            for ch in li:
                if ch["id"] == channel.id:
                    del ch[attribute]

    async def _set_attribute(
        self,
        channel: discord.TextChannel,
        attribute,
        value
    ):
        added = False
        async with self.settings.guild(channel.guild).channels() as li:
            # Check if attribute already exists
            for ch in li:
                if ch["id"] == channel.id:
                    ch[attribute] = value
                    added = True
                    break

            if added is False:
                # Attribute does not exist for channel
                li.append({
                    "id": channel.id,
                    attribute: value
                })

    @_enforcer.command("configure")
    async def enforcer_configure(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        attribute: str,
        *,
        value: str = None
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
            value = await self._validate_attribute_value(attribute, value)
        except ValueError:
            await ctx.send("The given value is invalid for that attribute.")
            return

        await self._set_attribute(channel, attribute, value)
        await ctx.send(
            f"Channel has now configured the {attribute} attribute."
        )

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

        async with self.settings.guild(message.guild).channels() as li:
            for ch in li:
                if not ch["id"] == message.channel.id:
                    # Not relating to this channel
                    continue

                if KEY_ENABLED not in ch or not ch[KEY_ENABLED]:
                    # Enforcing not enabled here
                    continue

                if KEY_MINCHARS in ch:
                    if len(message.content) < ch[KEY_MINCHARS]:
                        # They breached minchars attribute
                        delete = "Not enough characters"
                        break

                if KEY_NOMEDIA in ch and ch[KEY_NOMEDIA] is True:
                    if len(message.attachments) > 0:
                        # They breached nomedia attribute
                        delete = "No media attached"
                        break

                if KEY_REQUIREMEDIA in ch and ch[KEY_REQUIREMEDIA] is True:
                    if len(message.attachments) == 0:
                        # They breached requiremedia attribute
                        delete = "Requires media attached"
                        break

                if KEY_NOTEXT in ch and ch[KEY_NOTEXT] is True:
                    if len(message.content) > 0:
                        # They breached notext attribute
                        delete = "Message had no text"
                        break

                if KEY_MINDISCORDAGE in ch:
                    if author.created_at is None:
                        # They didn't have a created_at date?
                        break

                    delta = datetime.utcnow() - author.created_at
                    if ch[KEY_MINDISCORDAGE] > delta.seconds:
                        # They breached minimum discord age
                        delete = "User not in server long enough"
                        break

                if KEY_MINGUILDAGE in ch:
                    if author.joined_at is None:
                        # They didn't have a joined_at date?
                        break

                    delta = datetime.utcnow() - author.joined_at
                    if ch[KEY_MINGUILDAGE] > delta.seconds:
                        # They breached minimum guild age
                        delete = "User account not old enough"
                        break

        if delete:
            await message.delete()

            log_id = await self.settings.guild(message.guild).logchannel()
            if log_id is not None:
                log = message.guild.get_channel(log_id)
                data = discord.Embed(color=discord.Color.orange())
                data.set_author(
                    name=f"Message Enforced - {author}",
                    icon_url=author.avatar_url
                )
                data.add_field(name="Enforced Reason", value=f"{delete}")
                if log is not None:
                    try:
                        await log.send(embed=data)
                    except discord.Forbidden:
                        await log.send(
                            "**Message Enforced** - " +
                            f"{author.id} - {author} - Reason: {delete}"
                        )

    @_enforcer.command("status")
    async def enforcer_status(
        self,
        ctx: commands.Context
    ):
        """Prints the status of the enforcement cog

        Example:
        - `[p]enforcer status`
        """
        messages = []
        async with self.settings.guild(ctx.guild).channels() as li:
            for channel_obj in li:
                channel = ctx.guild.get_channel(channel_obj["id"])

                conf_str = ""
                for key in self.attributes.keys():
                    if key in channel_obj:
                        conf_str = conf_str + f"{key} - {channel_obj[key]}\n"

                messages.append(
                    f"📝{channel.mention} - " +
                    f"Configuration\n " +
                    conf_str
                )

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = [page for page in pagify("\n\n".join(messages), shorten_by=58)]
        embeds = []
        i = 0
        for page in pages:
            i = i+1

            data = discord.Embed(colour=(await ctx.embed_colour()))
            data.title = f"Enforcement Configuration - Page {i}/{len(pages)}"
            data.description = page

            embeds.append(data)

        await menu(
            ctx,
            pages=embeds,
            controls=CUSTOM_CONTROLS,
            message=None,
            page=0,
            timeout=30,
        )
