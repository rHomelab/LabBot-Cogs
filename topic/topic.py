import discord
from redbot.core import app_commands, commands


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
            await ctx.send(f"{ctx.channel.mention}: {topic}")
        else:
            await ctx.send("This channel does not have a topic.")

    @app_commands.command(name="topic")
    @app_commands.guild_only()
    async def app_topic(self, interaction: discord.Interaction):
        """Repeats the current channel's topic as a message in the channel."""

        topic = interaction.channel.topic
        if topic:
            await interaction.response.send_message(f"{interaction.channel.mention}: {topic}")
        else:
            await interaction.response.send_message("This channel does not have a topic.")
