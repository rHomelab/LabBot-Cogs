import discord
import logging
import random
import re

from redbot.core import checks, Config, commands, bot

log = logging.getLogger("red.cbd-cogs.markov")

__all__ = ["UNIQUE_ID", "Markov"]

UNIQUE_ID = 0x6D61726B6F76
WORD_TOKENIZER = re.compile(r'(\W+)')
CONTROL = f"{UNIQUE_ID}"

class Markov(commands.Cog):
    """ A markov-chain-based text generator cog """
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.conf.register_user(chains={}, chain_depth=1, mode="word", enabled=False)
        self.conf.register_guild(channels=[])

    @commands.Cog.listener()
    async def on_message(self, message):
        """ Process messages from enabled channels for enabled users """
        # Attempt to load guild channel restrictions
        try:
            channels = await self.conf.guild(message.guild).channels()
            if message.channel.id not in channels:
                log.debug("Ignoring message from disabled channel")
                return
        except AttributeError:  # Not in a guild
            pass
        # Ignore messages from the bot itself
        if message.author.id == self.bot.user.id:
            return
        # Ignore messages that start with non-alphanumeric characters
        if message.content and not message.content[0].isalnum():
            return
        # Load the user's markov chain and settings
        enabled, chains, depth, mode = await self.get_user_config(message.author)
        # Check whether the user has enabled markov modeling
        if enabled is not True:
            return
        # Create a token cleaner
        cleaner = lambda x: x
        # Choose a tokenizer mode
        if mode == "word":
            tokenizer = WORD_TOKENIZER
            cleaner = lambda x: x.strip()
        elif mode.startswith("chunk"):
            chunk_length = 3 if len(mode) == 5 else mode[5:]
            tokenizer = re.compile(fr'(.{{{chunk_length}}})')
        # Get or create chain for tokenizer settings
        model = chains.get(f"{mode}-{depth}", {})
        # Begin all state chains with the control marker
        state = CONTROL
        # Remove code block formatting and outer whitespace
        content = message.content.replace('`', '').strip()
        # Split message into cleaned tokens
        tokens = [t for x in tokenizer.split(content) if (t := cleaner(x))]
        # Add control character transition to end of token chain
        tokens.append(CONTROL)
        # Iterate over the tokens in the message
        for i, token in enumerate(tokens):
            # Ensure dict key for vector distribution is created
            model[state] = model.get(state, {})
            # Increment the weight for this state vector or initialize it to 1
            model[state][token] = model[state].get(token, 0) + 1
            # Produce sliding state window (ngram)
            j = 1 + i - depth if i >= depth else 0
            state = "".join(cleaner(x) for x in tokens[j:i+1])
        # Store the model
        chains[f"{mode}-{depth}"] = model
        await self.conf.user(message.author).chains.set(chains)

    @commands.group()
    async def markov(self, ctx: commands.Context):
        """ New users must `enable` and say some words before using `generate` """
        pass

    @markov.command()
    async def generate(self, ctx: commands.Context, user: discord.abc.User = None):
        """ Generate text based on user language models """
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
            if i > 3:
                await ctx.send(f"I tried to generate text 3 times, now I'm giving up.")
                return
            i += 1
        await ctx.send(text[:2000])

    @markov.command()
    async def enable(self, ctx: commands.Context):
        """ Allow the bot to model your messages and generate text based on that """
        await self.conf.user(ctx.author).enabled.set(True)
        await ctx.send("Markov modeling enabled!")

    @markov.command()
    async def disable(self, ctx: commands.Context):
        """ Disallow the bot from modeling your message or generating text based on your models """
        await self.conf.user(ctx.author).enabled.set(False)
        await ctx.send("Markov text generation is now disabled for your user.\n"
                       "I will stop updating your language models, but they are still stored.\n"
                       "You may want to use `[p]markov` reset to delete them.\n")

    @markov.command()
    async def mode(self, ctx: commands.Context, mode: str):
        """ Set the tokenization mode for model building
        
        Available modes are:
         - `word`: Tokenize input based on words and punctuation using the regular expression (\W+)
         - `chunk`: Tokenize input into chunks of a certain length. You can specify the chunk size, e.g. "chunk5"
        
        Separate models will be stored for each combination of mode and depth that you choose.
        """
        await self.conf.user(ctx.author).mode.set(mode)
        await ctx.send(f"Token mode set to '{mode}'.")

    @markov.command()
    async def depth(self, ctx: commands.Context, depth: int):
        """ Set the modeling depth (the "n" in "ngrams") """
        await self.conf.user(ctx.author).chain_depth.set(depth)
        await ctx.send(f"Ngram modeling depth set to {depth}.")

    @markov.command()
    async def show(self, ctx: commands.Context, user: discord.abc.User = None):
        """ Show your current settings and models, or those of another user """
        if not isinstance(user, discord.abc.User):
            user = ctx.message.author
        enabled, chains, depth, mode = await self.get_user_config(user, lazy=False)
        models = '\n'.join(chains.keys())
        await ctx.send(f"**Enabled:** {enabled}\n"
                       f"**Chain Depth:** {depth}\n"
                       f"**Token Mode:** {mode}\n"
                       f"**Stored Models:**\n{models}")

    @markov.command()
    async def delete(self, ctx: commands.Context, model: str):
        """ Delete a specific model from your profile """
        chains = await self.conf.user(ctx.message.author).chains()
        if model in chains.keys():
            del chains[model]
            await self.conf.user(ctx.message.author).chains.set(chains)
            await ctx.send(f"Deleted model")
        else:
            await ctx.send(f"Model not found")

    @markov.command()
    async def reset(self, ctx: commands.Context):
        """ Remove all language models from your profile """
        await self.conf.user(ctx.author).chains.set({})

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @markov.command()
    async def channelenable(self, ctx: commands.Context, channel: str = None):
        """ Enable modeling of messages in a channel for enabled users """
        await self.channels_update(channel or ctx.channel.id, ctx.guild, True)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @markov.command()
    async def channeldisable(self, ctx: commands.Context, channel: str = None):
        """ Disable modeling of messages in a channel """
        await self.channels_update(channel or ctx.channel.id, ctx.guild, False)

    async def channels_update(self, channel, guild, add: bool = True):
        """ Update list of channels in which modeling is allowed """
        channels = await self.conf.guild(guild).channels()
        if add:
            channels.append(int(channel))
        else:
            channels.remove(int(channel))
        await self.conf.guild(guild).channels.set(channels)

    async def get_user_config(self, user: discord.abc.User, lazy: bool = True):
        """ Get a user config, optionally short circuiting if not enabled """
        user_config = self.conf.user(user)
        enabled = await user_config.enabled()
        if lazy and not enabled:
            return (False, )*4
        chains = await user_config.chains() or {}
        depth = await user_config.chain_depth() or 1
        mode = (await user_config.mode() or "word").lower()
        return enabled, chains, depth, mode

    async def generate_text(self, chains: dict, depth: int, mode: str):
        """ Generate text based on the appropriate model for user settings """
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
        """ Generate text for word-mode vectorization """
        # Remove word boundaries from ngram; whitespace is added back later
        state = state.replace(" ", "")
        # Choose the next word taking into account recorded vector weights
        gram = await self.choose_gram(model, state)
        # Don't worry about it ;)
        prepend_space = all((state != CONTROL,
                             gram[-1].isalnum() or gram in "\"([{|",
                             state[-1] not in "\"([{'/-_"))
        # Format gram
        return f"{' ' if prepend_space else ''}{gram}"

    async def generate_chunk_gram(self, *args):
        """ Generate text for chunk-mode vectorization """
        return await self.choose_gram(*args)

    async def choose_gram(self, model: dict, state: str):
        """ Here lies the secret sauce """
        gram, = random.choices(population=list(model[state].keys()),
                               weights=list(model[state].values()),
                               k=1)  # Caution: basically magic
        return gram
