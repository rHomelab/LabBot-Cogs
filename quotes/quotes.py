"""discord red-bot quotes"""
import discord
from redbot.core import checks, commands, Config


class QuotesCog(commands.Cog):
    """Quotes Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633002)

        default_guild_config = {
            "quote_channel": None,
        }

        self.config.register_guild(**default_guild_config)

    @commands.group(name='quote')
    async def _quotes(self, ctx):
        pass

    @commands.guild_only()
    @checks.mod()
    @_quotes.command(name='setchannel')
    async def set_quotes_channel(self, ctx, channel: discord.TextChannel):
        """Set the quotes channel for this server

        Usage:
        - `[p]quote setchannel <channel>`
        """
        await self.config.guild(ctx.guild).quote_channel.set(channel.id)
        check_value = await self.config.guild(ctx.guild).quote_channel()
        success_embed = discord.Embed(title='Quotes channel set', description=f'Quotes channel set to <#{check_value}>', colour=ctx.guild.me.colour)
        await ctx.send(embed=success_embed)

    @commands.guild_only()
    @_quotes.command(name='add')
    async def add_quote(self, ctx, channel:discord.TextChannel, *message_ids):
        """Add a message or set of messages to the quotes channel

        Usage:
        - `[p]quote add <channel> <message_id>`

        For multiple messages in a single quote:
        - `[p]quote add <channel> <message_id1> <message_id2> <message_id3>`
        """
        messages = []
        # Collect the messages
        for message_id in message_ids:
            try:
                m = await channel.fetch_message(int(message_id))
                # Stops people from putting messages that aren't in this guild
                if m.channel.guild != ctx.guild:
                    raise BaseException
                messages.append(m)
            # Could be ValueError if the ID isn't int convertible or NotFound if it's not a valid ID
            except Exception:
                error_embed = await self.make_error_embed(ctx, custom_msg=f'Could not find message with ID `{message_id}`')
                await ctx.send(embed=error_embed)
                return

        authors = []
        for i in messages:
            if i.author in authors:
                continue
            authors.append(i.author)

        if len(set(authors)) > 1:
            formatted_quote = '\n'.join([f'**{i.author.nick if i.author.nick else i.author.name}:** {i.content}' for i in messages])
        else:
            formatted_quote = '\n'.join([i.content for i in messages])

        quote_embed = await self.make_quote_embed(ctx, formatted_quote, messages, authors)
        quote_channel = await self.config.guild(ctx.guild).quote_channel()

        if not quote_channel:
            error_embed = await self.make_error_embed(ctx, error_type='NoChannelSet')
            await ctx.send(embed=error_embed)
            return

        try:
            quote_channel = await self.bot.fetch_channel(quote_channel)
        except Exception:
            error_embed = await self.make_error_embed(ctx, error_type='ChannelNotFound')
            await ctx.send(embed=error_embed)
            return

        try:
            await quote_channel.send(embed=quote_embed)
            success_embed = discord.Embed(description='Your quote has been sent', colour=ctx.guild.me.colour)
            await ctx.send(embed=success_embed)
        # If sending the quote failed for any reason. For example, quote exceeded the character limit
        except Exception as err:
            error_embed = await self.make_error_embed(ctx, custom_msg=err)
            await ctx.send(embed=error_embed)

# Helper functions

    async def make_quote_embed(self, ctx, formatted_quote, messages, authors):
        """Generate the quote embed to be sent"""
        author_list = ' '.join([i.mention for i in authors])
        quote_embed = discord.Embed(description=formatted_quote, colour=ctx.guild.me.colour, timestamp=messages[0].created_at)
        quote_embed.add_field(name='Authors', value=author_list, inline=False)
        quote_embed.add_field(name='Submitted by', value=ctx.author.mention, inline=True)
        quote_embed.add_field(name='Channel', value=f'<#{messages[0].channel.id}>', inline=True)
        quote_embed.add_field(name='Link', value=f'[Jump to quote]({messages[0].jump_url})', inline=True)
        return quote_embed

    async def make_error_embed(self, ctx, error_type: str = '', custom_msg: str = None):
        """Generate error message embeds"""
        error_msgs = {
            'NoChannelSet': f"""There is no quotes channel configured for this server.
        A moderator must set a quotes channel for this server using the command `{ctx.prefix}quote set_quotes_channel <channel>`""",
            'ChannelNotFound': f"""Unable to find the quotes channel for this server. This could be due to a permissions issue or because the channel no longer exists.

        A moderator must set a valid quotes channel for this server using the command `{ctx.prefix}quote set_quotes_channel <channel>`"""
        }

        if error_type:
            error_msg = error_msgs[error_type]
        elif custom_msg:
            error_msg = custom_msg

        return discord.Embed(title='Error', description=error_msg, colour=ctx.guild.me.colour)
