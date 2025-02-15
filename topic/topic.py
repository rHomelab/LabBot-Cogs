import discord
from redbot.core import app_commands, commands


class Topic(commands.Cog):
    """Thus beginith the topic command"""

    def __init__(self):
        pass

    def _is_valid_channel(self, channel: discord.abc.MessageableChannel | discord.interactions.InteractionChannel | None):
        if channel is not None and not isinstance(
            channel,
            (
                discord.VoiceChannel,
                discord.Thread,
                discord.DMChannel,
                discord.PartialMessageable,
                discord.GroupChannel,
                discord.VoiceChannel,
                discord.CategoryChannel,
            ),
        ):
            return channel
        return False

    @commands.command()
    @commands.guild_only()
    async def topic(self, ctx: commands.GuildContext):
        """Repeats the current channel's topic as a message in the channel."""
        if channel := self._is_valid_channel(ctx.channel):
            topic = channel.topic
            if topic:
                await ctx.send(f"{ctx.channel.mention}: {topic}")
                return
        await ctx.send("This channel does not have a topic.")

    @app_commands.command(name="topic")
    @app_commands.guild_only()
    async def app_topic(self, interaction: discord.Interaction):
        """Repeats the current channel's topic as a message in the channel."""
        if channel := self._is_valid_channel(interaction.channel):
            topic = channel.topic
            if topic:
                await interaction.response.send_message(f"{channel.mention}: {topic}")
                return
        await interaction.response.send_message("This channel does not have a topic.")
