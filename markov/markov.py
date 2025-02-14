import logging
import random
import re
from io import BytesIO
from typing import Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.mod import is_mod_or_superior

log = logging.getLogger("red.rhomelab.markov")

__all__ = ["UNIQUE_ID", "Markov"]

UNIQUE_ID = 0x6D61726B6F76
WORD_TOKENIZER = re.compile(r"(\W+)")
CONTROL = f"{UNIQUE_ID}"


class Markov(commands.Cog):
    """A markov-chain-based text generator cog"""

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_user(chains={}, chain_depth=1, mode="word", enabled=False)
        self.conf.register_guild(channels=[])

    # Red end user data management support

    async def red_get_data_for_user(self, *, user_id: int) -> dict[str, BytesIO]:
        """Get a user's personal data."""
        user_data = self.conf.user(await self.bot.fetch_user(user_id))
        if user_data.chains:
            data = (
                f"Stored data for user with ID {user_id}:\n"
                f"User modelling enabled: {await user_data.enabled()}\n"
                + f"User chain depth: {await user_data.chain_depth()}\n"
                + f"User mode: {await user_data.mode()}\n"
                + f"User chains: {await user_data.chains()}"
            )
        else:
            data = f"No data is stored for user with ID {user_id}.\n"
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.conf.member(await self.bot.fetch_user(user_id)).clear()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages from enabled channels for enabled users"""

        if not await self.should_process_message(message):
            return

        # Load the user's markov chain and settings
        _, chains, depth, mode = await self.get_user_config(message.author)

        model = chains.get(f"{mode}-{depth}", {})
        # Begin all state chains with the control marker
        state = CONTROL

        content = message.content.replace("`", "").strip()

        # Choose a tokenizer mode
        if mode == "word":
            tokens = [x for x in WORD_TOKENIZER.split(content) if x.strip()]
            # Add control character transition to end of token chain
            tokens.append(CONTROL)
        elif mode.startswith("chunk"):
            chunk_length = 3 if len(mode) == 5 else mode[5:]  # noqa: PLR2004
            tokenizer = re.compile(rf"(.{{{chunk_length}}})")
            tokens = [x for x in tokenizer.split(content) if x]
        else:
            # fixme: what to do if mode is set wrong
            return

        # Iterate over the tokens in the message
        for i, token in enumerate(tokens):
            # Ensure dict key for vector distribution is created
            model[state] = model.get(state, {})

            # Increment the weight for this state vector or initialize it to 1
            model[state][token] = model[state].get(token, 0) + 1

            # Produce sliding state window (ngram)
            j = 1 + i - depth if i >= depth else 0
            state = "".join(x for x in tokens[j : i + 1])

        # Store the model
        chains[f"{mode}-{depth}"] = model
        await self.conf.user(message.author).chains.set(chains)

    # Commands

    @commands.group()
    async def markov(self, ctx: commands.Context):
        """New users must `enable` and say some words before using `generate`"""

    @markov.command()
    async def generate(self, ctx: commands.Context, user: discord.abc.User = None):
        """Generate text based on user language models"""
        if not isinstance(user, discord.abc.User):
            user = ctx.message.author
        enabled, chains, depth, mode = await self.get_user_config(user)
        if not enabled:
            await ctx.send(f"Sorry, {user} won't let me model their speech")
            return
        text = None
        i = 0
        while not text:
            text = await self.generate_text(chains, depth, mode)
            if i > 3:  # noqa: PLR2004
                await ctx.send("I tried to generate text 3 times, now I'm giving up.")
                return
            i += 1
        await ctx.send(text[:2000])

    @markov.command()
    async def enable(self, ctx: commands.Context):
        """Allow the bot to model your messages and generate text based on that"""
        await self.conf.user(ctx.author).enabled.set(True)
        await ctx.send("Markov modelling enabled!")

    @markov.command()
    async def disable(self, ctx: commands.Context):
        """Disallow the bot from modelling your message or generating text based on your models"""
        await self.conf.user(ctx.author).enabled.set(False)
        await ctx.send(
            "Markov text generation is now disabled for your user.\n"
            "I will stop updating your language models, but they are still stored.\n"
            "You may use `[p]markov` reset to delete them.\n"
        )

    @markov.command()
    async def mode(self, ctx: commands.Context, mode: str):
        """Set the tokenization mode for model building

        Available modes are:
        - `word`: Tokenize input based on words and punctuation using the regular expression (\\W+)
        - `chunk`: Tokenize input into chunks of a certain length. You can specify the chunk size, e.g. "chunk5"

        Separate models will be stored for each combination of mode and depth that you choose.
        """
        # fixme: error handle mode being wrong

        await self.conf.user(ctx.author).mode.set(mode)
        await ctx.send(f"Token mode set to '{mode}'.")

    @markov.command()
    async def depth(self, ctx: commands.Context, depth: int):
        """Set the modelling depth (the "n" in "ngrams")"""
        await self.conf.user(ctx.author).chain_depth.set(depth)
        await ctx.send(f"Ngram modelling depth set to {depth}.")

    @markov.command(aliases=["user_settings"])
    async def show_user(self, ctx: commands.Context, user: discord.abc.User = None):
        """Show your current settings and models

        Moderators can also view the settings and models of another member if they specify one.

        `user`: A user mention or ID
        """
        embed = discord.Embed(title="Markov settings", colour=await ctx.embed_colour())
        # Check if user parameter was specified and valid
        user_specified = isinstance(user, discord.abc.User)

        if user_specified:
            # Warn and stop if non-mod user requests another user's data
            if not await is_mod_or_superior(self.bot, ctx.message):
                await ctx.send("Sorry, viewing other member's settings is limited to moderators.")
                return
            embed.description = f"Settings for user {user.display_name}"
        else:
            user = ctx.message.author

        # Get user configs
        enabled, chains, depth, mode = await self.get_user_config(user, lazy=False)
        models = "\n".join(chains.keys())

        # Build & send embed
        embed.add_field(name="Enabled", value=enabled, inline=True)
        embed.add_field(name="Chain Depth", value=depth, inline=True)
        embed.add_field(name="Token Mode", value=mode, inline=True)
        embed.add_field(name="Stored Models", value=models, inline=False)
        await ctx.send(embed=embed)

    @checks.mod()
    @commands.guild_only()
    @markov.command(aliases=["guild_settings"])
    async def show_guild(self, ctx: commands.Context):
        """Show current guild settings"""
        await ctx.send(embed=await self.gen_guild_settings_embed(ctx.guild))

    @checks.is_owner()
    @markov.command(aliases=["show_config"])
    async def show_global(self, ctx: commands.Context, guild_id: Optional[int] = None):
        """Show global summary info or info for `guild_id`"""
        embed = discord.Embed(title="Markov settings", colour=await ctx.embed_colour())
        enabled_channels = ""
        enabled_users = ""
        users = await self.conf.all_users()

        # If guild_id specified, get data for guild
        if guild_id:
            guild = self.bot.get_guild(guild_id)
            embed = await self.gen_guild_settings_embed(guild)
            embed.description = f"Settings for {guild.name} ({guild.id})"
            await ctx.send(embed=embed)

        else:
            # Get all guilds where Markov has been installed
            guilds = await self.conf.all_guilds()
            # Iterate over guild IDs, discard returned guild data
            for loop_guild_id, _ in guilds.items():
                # Get this guild
                guild = self.bot.get_guild(loop_guild_id)

                # Get enabled channels and add output line
                channels = await self.get_enabled_channels(guild)
                enabled_channels += f"{guild.name} ({guild.id}): {len(channels)}"

                # Get enabled users and format output line
                users = await self.get_enabled_users(loop_guild_id)
                enabled_users += f"{guild.name} ({guild.id}): {users['enabled']}\n"

            # Append output line for users with no known guild (i.e. bot has no mutual guilds with user)
            enabled_users += f"No known guild: {users['no_mutual']}"

            # Add fields & send embed
            embed.add_field(name="Enabled Channels", value=enabled_channels, inline=False)
            embed.add_field(name=f"Enabled {'Members' if guild_id else 'Users'}", value=enabled_users, inline=False)
            await ctx.send(embed=embed)

    @markov.command()
    async def delete(self, ctx: commands.Context, model: str):
        """Delete a specific model from your profile"""
        chains = await self.conf.user(ctx.message.author).chains()
        if model in chains.keys():
            del chains[model]
            await self.conf.user(ctx.message.author).chains.set(chains)
            await ctx.send("Deleted model")
        else:
            await ctx.send("Model not found")

    @markov.command()
    async def reset(self, ctx: commands.Context):
        """Remove all language models from your profile"""
        await self.conf.user(ctx.author).chains.set({})

    @checks.mod()
    @commands.guild_only()
    @markov.command()
    async def channelenable(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Enable modelling of messages in a channel for enabled users"""
        await self.channels_update(ctx, channel or ctx.channel, True)

    @checks.mod()
    @commands.guild_only()
    @markov.command()
    async def channeldisable(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Disable modelling of messages in a channel"""
        await self.channels_update(ctx, channel or ctx.channel, False)

    # Markov generation functions

    async def generate_text(self, chains: dict, depth: int, mode: str):
        """Generate text based on the appropriate model for user settings"""
        generator = None
        if mode == "word":
            generator = self.generate_word_gram
        elif mode.startswith("chunk"):
            generator = self.generate_chunk_gram
        if not generator:
            return f"Sorry, I don't have a text generator for token mode '{mode}'"
        # Get appropriate model for settings
        try:
            model = chains[f"{mode}-{depth}"]
        except KeyError:
            return "Sorry, I can't find a model to use"
        output = []
        i = 0
        gram = ""
        # Begin in a state of transitioning from message boundary
        state = CONTROL
        while gram.strip() != CONTROL:
            # Generate and store next gram
            gram = await generator(model, state)
            output.append(gram)
            # Produce sliding state window (ngram)
            i += 1
            j = i - depth if i > depth else 0
            state = "".join(output[j:i])
        if not output:
            return
        return "".join(output[:-1])

    async def generate_word_gram(self, model: dict, state: str):
        """Generate text for word-mode vectorization"""
        # Remove word boundaries from ngram; whitespace is added back later
        state = state.replace(" ", "")
        # Choose the next word taking into account recorded vector weights
        gram = await self.choose_gram(model, state)
        # Don't worry about it ;)
        prepend_space = all((state != CONTROL, gram[-1].isalnum() or gram in '"([{|', state[-1] not in "\"([{'/-_"))
        # Format gram
        return f"{' ' if prepend_space else ''}{gram}"

    async def generate_chunk_gram(self, *args):
        """Generate text for chunk-mode vectorization"""
        return await self.choose_gram(*args)

    async def choose_gram(self, model: dict, state: str):
        """Here lies the secret sauce"""
        (gram,) = random.choices(
            population=list(model[state].keys()), weights=list(model[state].values()), k=1
        )  # Caution: basically magic
        return gram

    # Helper functions

    async def channels_update(self, ctx: commands.Context, channel: discord.TextChannel, enable: bool):
        """Update list of channels in which modelling is allowed"""
        phrase = "enable" if enable else "disable"
        updated = False

        # Iterate over all configured channels for this guild
        async with self.conf.guild(ctx.guild).channels() as channels:
            # Enable channel if request is channel enable and channel isn't already enabled
            if enable and channel.id not in channels:
                channels.append(channel.id)
                updated = True
            # Disable channel if request is channel disable and channel is currently enabled
            elif not enable and channel.id in channels:
                channels.remove(channel.id)
                updated = True

        if updated:
            await ctx.send(f"Modelling {phrase}d in {channel.mention}.")
            log.debug(f"Modelling {phrase}d in {channel.name}({channel.id})")
        else:
            await ctx.send(f"Modelling already {phrase}d in {channel.mention}.")
            log.debug(
                f"{ctx.author.name}({ctx.author.id}) attempted to {phrase} "
                + f"modelling on {phrase}d channel {channel.name}({channel.id})"
            )

    async def get_user_config(self, user: discord.abc.User, lazy: bool = True):
        """Get a user config, optionally short circuiting if not enabled"""
        user_config = self.conf.user(user)
        enabled = await user_config.enabled()
        if lazy and not enabled:
            return (False,) * 4
        chains = await user_config.chains() or {}
        depth = await user_config.chain_depth() or 1
        mode = (await user_config.mode() or "word").lower()
        return enabled, chains, depth, mode

    async def should_process_message(self, message: discord.Message) -> bool:
        """Returns true if a message should be processed"""

        # Define simple function to log ignored message event
        # and return False (i.e. shouldn't process message)
        def no_process(reason: str) -> bool:
            log.debug(f"Ignoring message: {reason}")
            return False

        # Ignore messages not sent in a guild
        if not message.guild:
            return no_process("Message not sent in guild")

        # Attempt to load guild channel restrictions
        try:
            channels = await self.conf.guild(message.guild).channels()
            if message.channel.id not in channels:
                return no_process("Message sent in disabled channel")
        except AttributeError:  # Not in a guild
            pass

        # Ignore messages from the bot itself
        if message.author.id == self.bot.user.id:
            return no_process("Message sent by self")

        # Ignore messages that start with non-alphanumeric characters
        if message.content and not message.content[0].isalnum():
            return no_process("Message starts with non-alphanumeric characters")

        # Check whether the user has enabled markov modelling
        if not await self.conf.user(message.author).enabled():
            return no_process("User has not opted-in to modelling")

        # Return true (i.e. should process message) if all checks passed
        return True

    async def get_enabled_channels(self, guild: discord.Guild) -> list[discord.abc.GuildChannel]:
        """Retrieve a list of enabled channels in a given guild"""
        # Retrieve and iterate over enabled channels in specified guild,
        # appending each channel to the list of enabled channels.
        async with self.conf.guild(guild).channels() as channels:
            enabled_channels = [guild.get_channel(channel) for channel in channels]
        return enabled_channels

    async def get_enabled_users(self, guild_id: int) -> dict:
        """Retrieve a list of enabled users in a given guild"""
        enabled_users = 0
        users_no_mutual = 0
        # Get all users who've interfaced with the cog
        users = await self.conf.all_users()

        # Iterate over users, selecting only those who are enabled
        for conf_user in users:
            if users[conf_user]["enabled"]:
                # Attempt to get user object
                user = self.bot.get_user(conf_user)

                # If user can be found and shares a mutual guild(s) with the bot,
                # increase count of enabled users.
                # Else if user can be found but shares no mutual guild(s) with the bot,
                # increase count of users with no known guild.
                if user:
                    for guild in user.mutual_guilds:
                        if guild.id == guild_id:
                            enabled_users += 1
                    if not user.mutual_guilds:
                        users_no_mutual += 1
                else:
                    users_no_mutual += 1

        # Return dict of enabled users and users with no mutual guild
        return {"enabled": enabled_users, "no_mutual": users_no_mutual}

    async def gen_guild_settings_embed(self, guild: discord.Guild) -> discord.Embed:
        """Generate guild settings embed"""
        enabled_channels = ""

        # Get and iterate over enabled channels, adding an output line for each channel
        for channel in await self.get_enabled_channels(guild):
            enabled_channels += f"{channel.mention}\n"

        # Get enabled users in guild and use 'enabled' list
        users = await self.get_enabled_users(guild.id)
        enabled_users = users["enabled"]

        # Build & return embed
        embed = discord.Embed(title="Markov settings", colour=await self.bot.get_embed_colour(guild))
        embed.add_field(name="Enabled Channels", value=enabled_channels, inline=True)
        embed.add_field(name="Enabled Members", value=enabled_users, inline=True)
        return embed
