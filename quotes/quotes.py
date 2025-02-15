"""discord red-bot quotes"""

import asyncio
from typing import List, Optional, Sequence

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


class QuotesCog(commands.Cog):
    """Quotes Cog"""

    bot: Red
    config: Config

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633002)

        default_guild_config = {
            "quote_channel": None,  # int
        }

        self.config.register_guild(**default_guild_config)

    @commands.group(name="quote")
    async def _quotes(self, ctx: commands.Context):
        pass

    @commands.guild_only()
    @checks.mod()
    @_quotes.command(name="setchannel")
    async def set_quotes_channel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Set the quotes channel for this server

        Usage:
        - `[p]quote setchannel <channel>`
        """
        await self.config.guild(ctx.guild).quote_channel.set(channel.id)
        check_value = await self.config.guild(ctx.guild).quote_channel()
        success_embed = discord.Embed(
            title="Quotes channel set",
            description=f"Quotes channel set to <#{check_value}>",
            colour=await ctx.embed_colour(),
        )
        await ctx.send(embed=success_embed)

    # fixme: too many branches, i cba to refactor this now
    @commands.guild_only()
    @_quotes.command(name="add")
    async def add_quote(self, ctx: commands.GuildContext, *message_ids: str):
        """Add a message or set of messages to the quotes channel

        Usage:
        - `[p]quote add <message_id>`

        For multiple messages in a single quote:
        - `[p]quote add <message_id1> <message_id2> <message_id3>`
        """
        if not message_ids:
            return await self.send_error(ctx, error_type="NoArgs")

        # Collect the messages
        async with ctx.channel.typing():
            messages = await self._get_messages(ctx, message_ids)

            if not messages:
                return

            quote_fragments = []
            for message in messages:
                quote_fragments.append(f"**{self._get_author_name(message)}:** {message.content}")

            formatted_quote = "\n".join(quote_fragments)

            quote_embed = await self.make_quote_embed(ctx, formatted_quote, messages)
            quote_channel = await self.config.guild(ctx.guild).quote_channel()

            if not quote_channel:
                return await self.send_error(ctx, error_type="NoChannelSet")

            try:
                quote_channel = await self.bot.fetch_channel(quote_channel)
            except Exception:
                return await self.send_error(ctx, error_type="ChannelNotFound")

        try:
            msg = await ctx.send(embed=quote_embed, content="Are you sure you want to send this quote?")
        # If sending the quote failed for any reason. For example, quote exceeded the character limit
        except Exception as err:
            return await self.send_error(ctx, custom_msg=str(err))

        confirmation = await self.get_confirmation(ctx, msg)
        if confirmation:
            await quote_channel.send(embed=quote_embed)
            success_embed = discord.Embed(description="Your quote has been sent", colour=await ctx.embed_colour())
            await ctx.send(embed=success_embed)

    # Helper functions

    async def _get_author_name(self, message: discord.Message) -> str:
        author = message.author
        if isinstance(author, discord.Member):
            return f"{author.nick if author.nick else author.name}"
        return f"{author.name}"

    async def _get_messages(self, ctx: commands.GuildContext, message_ids: Sequence[str]) -> List[discord.Message]:
        messages: list[discord.Message] = []
        errored_mids: list[str] = []
        # NOTE: is this the best wat to do this? no clue tbh ask @Tigattack
        for elem in message_ids:
            for _channel in ctx.guild.channels:
                if channel := self._is_valid_channel(_channel):
                    try:
                        message = await channel.fetch_message(int(elem))
                        messages.append(message)
                        break
                    # Could be ValueError if the ID isn't int convertible or NotFound if it's not a valid ID
                    except (ValueError, discord.NotFound):
                        pass
            else:
                # message not found in any channel
                errored_mids.append(elem)

        if errored_mids and len(errored_mids) < len(message_ids):
            error_msg = f"The following message IDs were not found: {', '.join(errored_mids)}"
            await self.send_error(ctx, custom_msg=error_msg)
        elif errored_mids and len(errored_mids) == len(message_ids):
            await self.send_error(ctx, custom_msg="None of the provided message IDs were found!")
        return messages

    async def make_quote_embed(
        self,
        ctx: commands.Context,
        formatted_quote: str,
        messages: List[discord.Message],
    ) -> discord.Embed:
        """Generate the quote embed to be sent"""
        authors = [message.author for message in messages]
        author_list = " ".join([i.mention for i in authors])
        # List of channel mentions
        channels: List[str] = []

        for _channel in [i.channel for i in messages]:
            if channel := self._is_valid_channel(_channel):
                channels.append(channel.mention)
        unique_channels = set(channels)

        return (
            discord.Embed(
                description=formatted_quote,
                colour=await ctx.embed_colour(),
            )
            .add_field(name="Authors", value=author_list, inline=False)
            .add_field(name="Submitted by", value=ctx.author.mention)
            .add_field(name="Channels", value="\n".join(unique_channels))
            .add_field(name="Link", value=f"[Jump to quote]({messages[0].jump_url})")
            .add_field(name="Timestamp", value=f"<t:{int(messages[0].created_at.timestamp())}:F>")
        )

    async def send_error(self, ctx, error_type: str = "", custom_msg: str = "") -> None:
        """Generate error message embeds"""
        error_msgs = {
            "NoChannelSet": (
                "There is no quotes channel configured for this server. "
                "A moderator must set a quotes channel for this server using the "
                f"command `{ctx.prefix}quote set_quotes_channel <channel>`"
            ),
            "ChannelNotFound": (
                "Unable to find the quotes channel for this server. This could "
                "be due to a permissions issue or because the channel no longer exists."
                "A moderator must set a valid quotes channel for this server using the command "
                f"`{ctx.prefix}quote set_quotes_channel <channel>`"
            ),
            "NoArgs": "You must provide 1 or more message IDs for this command!",
        }

        if error_type:
            error_msg = error_msgs[error_type]
        elif custom_msg:
            error_msg = custom_msg
        else:
            error_msg = "An unknown error has occurred"
        error_embed = discord.Embed(title="Error", description=error_msg, colour=await ctx.embed_colour())
        await ctx.send(embed=error_embed)

    def _is_valid_channel(self, channel: discord.guild.GuildChannel | discord.abc.MessageableChannel | None):
        if channel is not None and not isinstance(
            channel,
            (
                discord.ForumChannel,
                discord.CategoryChannel,
                discord.DMChannel,
                discord.ForumChannel,
                discord.PartialMessageable,
                discord.GroupChannel,
            ),
        ):
            return channel
        return False

    async def get_confirmation(self, ctx: commands.Context, msg: discord.Message) -> Optional[bool]:
        """Get confirmation from user with reactions"""
        emojis = ["❌", "✅"]
        start_adding_reactions(msg, emojis)

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", timeout=180.0, check=ReactionPredicate.with_emojis(emojis, msg, ctx.author)
            )
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return
        else:
            await msg.clear_reactions()
            return bool(emojis.index(reaction.emoji))
