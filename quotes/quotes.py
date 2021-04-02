"""discord red-bot quotes"""
import asyncio
from typing import List, Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


class QuotesCog(commands.Cog):
    """Quotes Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633002)

        default_guild_config = {
            "quote_channel": None,
        }

        self.config.register_guild(**default_guild_config)

    @commands.group(name="quote")
    async def _quotes(self, ctx):
        pass

    @commands.guild_only()
    @checks.mod()
    @_quotes.command(name="setchannel")
    async def set_quotes_channel(self, ctx, channel: discord.TextChannel):
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

    @commands.guild_only()
    @_quotes.command(name="add")
    async def add_quote(self, ctx, *message_ids):
        """Add a message or set of messages to the quotes channel

        Usage:
        - `[p]quote add <message_id>`

        For multiple messages in a single quote:
        - `[p]quote add <message_id1> <message_id2> <message_id3>`
        """
        if not message_ids:
            error_embed = await self.make_error_embed(ctx, error_type="NoArgs")
            await ctx.send(embed=error_embed)
            return

        messages = []
        # Collect the messages
        async with ctx.channel.typing():
            for i, elem in enumerate(message_ids):
                if len(messages) != i:
                    error_embed = await self.make_error_embed(
                        ctx,
                        custom_msg=f"Could not find message with ID `{message_ids[i - 1]}`",
                    )
                    await ctx.send(embed=error_embed)
                    return
                for channel in ctx.guild.channels:
                    try:
                        message = await channel.fetch_message(int(elem))
                        messages.append(message)
                    # Could be ValueError if the ID isn't int convertible or NotFound if it's not a valid ID
                    except ValueError:
                        continue
                    except discord.NotFound:
                        continue

            authors = []
            for i in messages:
                if i.author in authors:
                    continue
                authors.append(i.author)

            if len(set(authors)) > 1:
                formatted_quote = "\n".join(
                    [f"**{i.author.nick if i.author.nick else i.author.name}:** {i.content}" for i in messages]
                )
            else:
                formatted_quote = "\n".join([i.content for i in messages])

            quote_embed = await self.make_quote_embed(ctx, formatted_quote, messages, authors)
            quote_channel = await self.config.guild(ctx.guild).quote_channel()

            if not quote_channel:
                error_embed = await self.make_error_embed(ctx, error_type="NoChannelSet")
                await ctx.send(embed=error_embed)
                return

            try:
                quote_channel = await self.bot.fetch_channel(quote_channel)
            except Exception:
                error_embed = await self.make_error_embed(ctx, error_type="ChannelNotFound")
                await ctx.send(embed=error_embed)
                return

        try:
            msg = await ctx.send(embed=quote_embed, content="Are you sure you want to send this quote?")
        # If sending the quote failed for any reason. For example, quote exceeded the character limit
        except Exception as err:
            error_embed = await self.make_error_embed(ctx, custom_msg=err)
            await ctx.send(embed=error_embed)
            return

        confirmation = await self.get_confirmation(ctx, msg)
        if confirmation:
            await quote_channel.send(embed=quote_embed)
            success_embed = discord.Embed(description="Your quote has been sent", colour=await ctx.embed_colour())
            await ctx.send(embed=success_embed)

    # Helper functions

    async def make_quote_embed(
        self,
        ctx,
        formatted_quote: str,
        messages: List[discord.Message],
        authors: List[discord.Member],
    ) -> discord.Embed:
        """Generate the quote embed to be sent"""
        author_list = " ".join([i.mention for i in authors])
        channels = []

        for channel in [i.channel for i in messages]:
            if channel.mention not in channels:
                channels.append(channel.mention)

        quote_embed = discord.Embed(
            description=formatted_quote,
            colour=await ctx.embed_colour(),
            timestamp=messages[0].created_at,
        )
        quote_embed.add_field(name="Authors", value=author_list, inline=False)
        quote_embed.add_field(name="Submitted by", value=ctx.author.mention, inline=True)
        if len(channels) > 1:
            quote_embed.add_field(name="Channels", value="\n".join(channels), inline=True)
        else:
            quote_embed.add_field(name="Channel", value=channels[0], inline=True)
        quote_embed.add_field(name="Link", value=f"[Jump to quote]({messages[0].jump_url})", inline=True)
        return quote_embed

    async def make_error_embed(self, ctx, error_type: str = "", custom_msg: str = None) -> discord.Embed:
        """Generate error message embeds"""
        error_msgs = {
            "NoChannelSet": f"""There is no quotes channel configured for this server.
        A moderator must set a quotes channel for this server using the command `{ctx.prefix}quote set_quotes_channel <channel>`""",
            "ChannelNotFound": f"""Unable to find the quotes channel for this server. This could be due to a permissions issue or because the channel no longer exists.

        A moderator must set a valid quotes channel for this server using the command `{ctx.prefix}quote set_quotes_channel <channel>`""",
            "NoArgs": "You must provide 1 or more message IDs for this command!",
        }

        if error_type:
            error_msg = error_msgs[error_type]
        elif custom_msg:
            error_msg = custom_msg

        return discord.Embed(title="Error", description=error_msg, colour=await ctx.embed_colour())

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
