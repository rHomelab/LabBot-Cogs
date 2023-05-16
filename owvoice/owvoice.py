from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from redbot.core import Config, checks
from redbot.core.bot import Red
from redbot.core import commands


class OWVoiceCog(commands.Cog):
    """Overwatch Voice Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384003)
        self.alertCache = {}
        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "min_joined_hours": 8760  # Default to one year so the mods set it up :)
        }

        self.config.register_guild(**default_guild_config)

    @checks.admin()
    @commands.group("owvoice", pass_context=True)
    async def _owvoice(self, ctx: commands.Context):
        pass

    @_owvoice.command(name="time")
    async def _time(self, ctx: commands.Context, hours: int):
        """Set/update the minimum hours users must be in the server before without triggering an alert."""

        await self.config.guild(ctx.guild).min_joined_hours.set(hours)
        await ctx.send("✅ Time requirement successfully updated!")

    @_owvoice.command(name="logchannel")
    async def _time(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
        """Set/update the channel to send voice activity alerts to."""

        chanId = ctx.channel.id
        if channel:
            chanId = channel.id
        await self.config.guild(ctx.guild).logchannel.set(chanId)
        await ctx.send("✅ Alert channel successfully updated!")

    @commands.Cog.listener()
    async def _on_voice_state_update(self, ctx: commands.Context, member: discord.Member,
                                     before: discord.VoiceState, after: discord.VoiceState):

        if self.alertCache[member.id]:  # Ignore if we've already alerted on this user. Can probably find a better way.
            return

        # Check if we're missing before or after objects or the respective channels.
        # If everything is there, check if the user switched channels (we don't care about that)
        if (before is None or after is None) or (before.channel is None or after.channel is None) or\
                (before.channel is not after.channel):
            return

        allowable = datetime.now(timezone.utc) + timedelta(hours=await self.config.guild(ctx.guild).min_join_hours())
        if datetime.now(timezone.utc) < allowable:
            if after.self_stream or after.self_video:
                self.alertCache[member.id] = True  # Update the cache to indicate we've alerted on this user.
                # Credit: Taken from report Cog
                log_id = await self.config.guild(member.guild).logchannel()
                log = None
                if log_id:
                    log = member.guild.get_channel(log_id)
                if not log:
                    # Failed to get the channel
                    return

                data = self.make_alert_embed(member, after.channel)

                mod_pings = ""
                # Alert level logic added
                mod_pings = " ".join(
                    [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
                if not mod_pings:  # If no online/idle mods
                    mod_pings = " ".join([i.mention for i in log.members if not i.bot])

                await log.send(content=mod_pings, embed=data)
                # End credit

    def make_alert_embed(self, member: discord.Member, chan: discord.VoiceChannel) -> discord.Embed:
        """Construct the alert embed to be sent"""
        # Copied from the report Cog.
        return (
            discord.Embed(
                colour=discord.Colour.orange(),
                description="New user joined a voice channel and started streaming or enabled their camera."
            )
            .set_author(name="Suspicious User Activity", icon_url=member.avatar.url)
            .add_field(name="Server", value=member.guild.name)
            .add_field(name="User", value=member.mention)
            .add_field(name="Channel", value=chan.mention)
            .add_field(name="Timestamp", value=f"<t:{int(datetime.now().utcnow().timestamp())}:F>")
        )