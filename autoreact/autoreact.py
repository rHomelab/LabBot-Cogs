"""discord red-bot autoreact"""
import asyncio

import discord
import discord.utils
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import menu, next_page, prev_page

CUSTOM_CONTROLS = {"⬅️": prev_page, "➡️": next_page}


class AutoReactCog(commands.Cog):
    """AutoReact Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633003)

        default_guild_config = {
            "reactions": {},  # Sets of phrases - phrase: [str]
            # Channels in which every message will get a specific set of reactions - str(channel.id): [str]
            "channels": {},
            # Channels in which no reactions will be processed (unless specified in channels) - [int]
            "whitelisted_channels": [],
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        reactions = await self.config.guild(message.guild).reactions()
        channels = await self.config.guild(message.guild).channels()
        whitelisted_channels = await self.config.guild(message.guild).whitelisted_channels()

        if str(message.channel.id) in channels.keys():  # process special reactions
            channel_reactions = channels[str(message.channel.id)]
            for reaction in channel_reactions:
                await message.add_reaction(reaction)

        # Do not continue if channel is whitelisted
        if message.channel.id in whitelisted_channels:
            return

        for phrase in reactions.keys():
            if phrase in message.content.lower().split():
                for emoji in reactions[phrase]:
                    await message.add_reaction(emoji)

    # Command groups

    @checks.mod()
    @commands.group(name="autoreact", pass_context=True)
    async def _autoreact(self, ctx):
        """Automagically add reactions to messages containing certain phrases"""

    @_autoreact.group(name="add", pass_context=True)
    async def _add(self, ctx):
        """Add autoreact pairs, channels, or whitelisted channels"""

    @_autoreact.group(name="remove", pass_context=True)
    async def _remove(self, ctx):
        """Remove autoreact pairs, channels, or whitelisted channels"""

    @commands.guild_only()
    @_autoreact.command(name="view", aliases=["list"])
    async def _view(self, ctx, *, object_type):
        """View the configuration for the autoreact cog

        Example:
        - `[p]autoreact view <reactions|channels|whitelisted_channels>`
        """
        object_type = object_type.lower()
        if object_type not in {
            "reactions",
            "channels",
            "whitelisted channels",
            "whitelisted_channels",
        }:
            error_embed = await self.make_error_embed(ctx, error_type="InvalidObjectType")
            await ctx.send(embed=error_embed)
            return

        items = await self.ordered_list_from_config(ctx.guild, object_type)
        embed_list = await self.make_embed_list(ctx, object_type, items)

        if len(embed_list) > 1:
            await menu(
                ctx,
                pages=embed_list,
                controls=CUSTOM_CONTROLS,
                message=None,
                page=0,
                timeout=60,
            )

        elif len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])

        else:
            error_embed = await self.make_error_embed(ctx, error_type="NoConfiguration")
            await ctx.send(embed=error_embed)

    # Add commands

    @commands.guild_only()
    @_add.command(name="reaction")
    async def _add_reaction(self, ctx, emoji, *, phrase):
        """Add an autoreact pair

        Example:
        - `[p]autoreact add reaction <emoji> <phrase>`
        """

        # If not unicode emoji (eg. 🤠)
        if len(emoji) > 1:
            # If discord emoji
            if [emoji[0], emoji[-1]] == ["<", ">"]:
                # Get the emoji id
                emoji_id = emoji[1:-1].split(":")[-1]
                # Check if the emoji is in this guild
                guild_emoji = discord.utils.get(ctx.guild.emojis, id=int(emoji_id))
                if not guild_emoji:
                    error_embed = await self.make_error_embed(ctx, error_type="EmojiNotFound")
                    await ctx.send(embed=error_embed)
                    return

        async with self.config.guild(ctx.guild).reactions() as reactions:
            if phrase.lower() not in reactions.keys():
                reactions[phrase.lower()] = []
                reactions[phrase.lower()].append(emoji)

        success_embed = discord.Embed(title="Added reaction pair", colour=await ctx.embed_colour())
        success_embed.add_field(name="Reaction", value=emoji, inline=False)
        success_embed.add_field(name="Phrase", value=phrase, inline=False)
        await ctx.send(embed=success_embed)

    @commands.guild_only()
    @_add.command(name="channel")
    async def _add_channel(self, ctx, channel: discord.TextChannel, *emojis):
        """Adds groups of reactions to every message in a channel

        Example:
        - `[p]autoreact add channel <channel> <emoji1> <emoji2> <emoji3>...`
        """
        async with self.config.guild(ctx.guild).channels() as channels:
            channels[str(channel.id)] = list(emojis)

        desc = f"I will react to every message in <#{channel.id}> with {' '.join(emojis)}"
        success_embed = discord.Embed(
            title="Autoreact channel added",
            description=desc,
            colour=await ctx.embed_colour(),
        )
        await ctx.send(embed=success_embed)

    @commands.guild_only()
    @_add.command(name="whitelisted_channel")
    async def _add_whitelisted(self, ctx, channel: discord.TextChannel):
        """Adds a channel to the reaction whitelist

        Example:
        - `[p]autoreact add whitelisted_channel <channel>`
        """
        async with self.config.guild(ctx.guild).whitelisted_channels() as whitelist:
            if channel.id in whitelist:
                error_embed = await self.make_error_embed(ctx, error_type="ChannelInWhitelist")
                await ctx.send(embed=error_embed)
                return
            whitelist.append(channel.id)
            desc = f"<#{channel.id}> added to whitelist"
            success_embed = discord.Embed(title="Success", description=desc, colour=await ctx.embed_colour())
            await ctx.send(embed=success_embed)

    # Remove commands

    @commands.guild_only()
    @_remove.command(name="reaction", aliases=["delete"])
    async def _remove_reaction(self, ctx, num: int):
        """Remove a reaction pair

        Example:
        - `[p]autoreact remove reaction <index>`
        To find the index of a reaction pair do `[p]autoreact view reactions`
        """
        items = await self.ordered_list_from_config(ctx.guild)
        to_del = items[num - 1]
        embed = discord.Embed(colour=await ctx.embed_colour())
        embed.add_field(name="Reaction", value=to_del["reaction"], inline=False)
        embed.add_field(name="Phrase", value=to_del["phrase"], inline=False)
        message_object = await ctx.send(embed=embed, content="Are you sure you want to remove this reaction pair?")

        emojis = ["✅", "❌"]
        for i in emojis:
            await message_object.add_reaction(i)

        def reaction_check(reaction, user):
            return (user == ctx.author) and (reaction.message.id == message_object.id) and (reaction.emoji in emojis)

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=180.0, check=reaction_check)
        except asyncio.TimeoutError:
            try:
                await message_object.clear_reactions()
            except Exception:
                pass
            return
        else:
            if reaction.emoji == "❌":
                await message_object.clear_reactions()
                return

            await self.remove_reaction(ctx.guild, to_del["phrase"], to_del["reaction"])
            success_embed = discord.Embed(
                title="Reaction pair removed",
                description=f"{to_del['reaction']} **-** {to_del['phrase']}",
                colour=await ctx.embed_colour(),
            )
            await ctx.send(embed=success_embed)

    @commands.guild_only()
    @_remove.command(name="channel")
    async def _remove_channel(self, ctx, channel: discord.TextChannel):
        """Remove reaction channels

        Example:
        - `[p]autoreact remove channel <channel>`
        """
        async with self.config.guild(ctx.guild).channels() as channels:

            if str(channel.id) not in channels.keys():
                error_embed = await self.make_error_embed(ctx, error_type="ChannelNotFound")
                await ctx.send(embed=error_embed)
                return

            channel_reactions = channels[str(channel.id)]
            embed = discord.Embed(colour=await ctx.embed_colour())
            embed.add_field(name="Channel", value=f"<#{channel.id}>", inline=False)
            embed.add_field(name="Reactions", value=" ".join(channel_reactions), inline=False)
            message_object = await ctx.send(
                embed=embed,
                content="Are you sure you want to remove this reaction channel?",
            )

            emojis = ["✅", "❌"]
            for emoji in emojis:
                await message_object.add_reaction(emoji)

            def reaction_check(reaction, user):
                return (user == ctx.author) and (reaction.message.id == message_object.id) and (reaction.emoji in emojis)

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=180.0, check=reaction_check)
            except asyncio.TimeoutError:
                try:
                    await message_object.clear_reactions()
                except Exception:
                    pass
                return
            else:
                if reaction.emoji == "❌":
                    await message_object.clear_reactions()
                    return

                del channels[str(channel.id)]
                success_embed = discord.Embed(
                    title="Reaction channel removed",
                    description=f"<#{channel.id}>",
                    colour=ctx.guild.me,
                )
                await ctx.send(embed=success_embed)

    @commands.guild_only()
    @_remove.command(name="whitelisted_channel")
    async def _remove_whitelisted(self, ctx, channel: discord.TextChannel):
        """Remove whitelisted channels

        Example:
        - `[p]autoreact remove whitelisted_channel <channel>`
        """
        async with self.config.guild(ctx.guild).whitelisted_channels() as channels:

            if channel.id not in channels:
                error_embed = await self.make_error_embed(ctx, error_type="ChannelNotFound")
                await ctx.send(embed=error_embed)
                return

            embed = discord.Embed(colour=await ctx.embed_colour())
            embed.add_field(name="Channel", value=f"<#{channel.id}>", inline=False)
            message_object = await ctx.send(
                embed=embed,
                content="Are you sure you want to remove this channel from the whitelist?",
            )

            emojis = ["✅", "❌"]
            for emoji in emojis:
                await message_object.add_reaction(emoji)

            def reaction_check(reaction, user):
                return (user == ctx.author) and (reaction.message.id == message_object.id) and (reaction.emoji in emojis)

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=180.0, check=reaction_check)
            except asyncio.TimeoutError:
                try:
                    await message_object.clear_reactions()
                except Exception:
                    pass
                return
            else:
                if reaction.emoji == "❌":
                    await message_object.clear_reactions()
                    return

                channels.remove(channel.id)
                success_embed = discord.Embed(
                    title="Channel removed from whitelist",
                    description=f"<#{channel.id}>",
                    colour=await ctx.embed_colour(),
                )
                await ctx.send(embed=success_embed)

    # Helper functions

    async def remove_reaction(self, guild: discord.Guild, phrase: str, reaction: str):
        async with self.config.guild(guild).reactions() as reactions:
            # Delete the whole kv pair if len 1
            if len(reactions[phrase]) == 1:
                del reactions[phrase]
            # Only remove one value from the list if len kv pair > 1
            elif len(reactions[phrase]) > 1:
                reactions[phrase].remove(reactions[reaction])

    async def ordered_list_from_config(self, guild, object_type="reactions"):
        items = []
        if object_type == "reactions":
            async with self.config.guild(guild).reactions() as reactions:
                for key in reactions.keys():
                    for item in reactions[key]:
                        items.append({"phrase": key, "reaction": item})

        elif object_type == "channels":
            async with self.config.guild(guild).channels() as channels:
                for key in channels.keys():
                    items.append({"channel": key, "reactions": ", ".join(channels[key])})

        elif object_type in ("whitelisted channels", "whitelisted_channels"):
            async with self.config.guild(guild).whitelisted_channels() as channels:
                for channel in channels:
                    items.append(channel)

        return items

    async def make_error_embed(self, ctx, error_type: str = ""):
        error_msgs = {
            "InvalidObjectType": "Invalid object. Please provide a valid object type from reactions, channels, whitelisted channels",
            "ChannelInWhitelist": "This channel is already in the whitelist",
            "ChannelNotFound": "Channel not found in config",
            "NoConfiguration": "No configuration has been set for this object",
        }
        error_embed = discord.Embed(
            title="Error",
            description=error_msgs[error_type],
            colour=await ctx.embed_colour(),
        )
        return error_embed

    async def make_embed_list(self, ctx, object_type: str, items: list):
        if not items:
            return []

        embed_list = []

        # Divide the list into parts
        def chunks(full_list: list, chunk_size: int):
            """Yield successive n-sized chunks from full_list"""
            for i in range(0, len(full_list), chunk_size):
                yield full_list[i : i + chunk_size]

        if object_type == "reactions":
            sectioned_list = list(chunks(items, 8))
            count = 1
            for section in sectioned_list:
                embed = discord.Embed(title=object_type.capitalize(), colour=await ctx.embed_colour())
                for elem in section:
                    embed.add_field(name="Index", value=count, inline=True)
                    embed.add_field(name="Phrase", value=elem["phrase"], inline=True)
                    embed.add_field(name="Reaction", value=elem["reaction"], inline=True)
                    count += 1
                embed_list.append(embed)

        elif object_type == "channels":
            sectioned_list = list(chunks(items, 8))
            for section in sectioned_list:
                embed = discord.Embed(title=object_type.capitalize(), colour=await ctx.embed_colour())
                for elem in section:
                    embed.add_field(name="Channel", value=f"<#{elem['channel']}>", inline=True)
                    embed.add_field(
                        name="Reactions",
                        value=" ".join(elem["reactions"]),
                        inline=True,
                    )
                    embed.add_field(name="​", value="​", inline=True)  # ZWJ field
                embed_list.append(embed)

        elif object_type in ("whitelisted channels", "whitelisted_channels"):
            sectioned_list = list(chunks(items, 10))
            for section in sectioned_list:
                channel_list = "\n".join([f"<#{i}>" for i in section])
                embed = discord.Embed(
                    title="Whitelisted Channels",
                    description=channel_list,
                    colour=await ctx.embed_colour(),
                )
                embed_list.append(embed)

        embed_count = 1

        for embed in embed_list:
            embed.set_footer(text=f"{embed_count} of {len(embed_list)}")
            embed_count += 1

        return embed_list
