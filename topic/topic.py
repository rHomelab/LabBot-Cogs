from redbot.core import commands

class Topic(commands.Cog):
    """Thus beginith the topic command"""

    def __init__(self):
        pass

    @commands.command()
    @commands.guild_only()
    async def topic(self, ctx: commands.Context):
        """Repeats the current channel's topic as a message in the channel."""

        topic = ctx.channel.topic
        if topic:
            await ctx.send(f'{ctx.channel.mention}: {topic}')
        else:
            await ctx.send('This channel does not have a topic.')
