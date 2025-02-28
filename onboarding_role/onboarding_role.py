import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
log = logging.getLogger("red.rhomelab.onboarding_role")

# TODO: Check for missed events on startup.


class OnboardingRole(commands.Cog):
    """
    Apply a role to users who complete onboarding.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=251776415735873537,
            force_registration=True,
        )

        default_guild_settings = {
            "role": None,
            "log_channel": None,
            "onboarded_users": [],
        }

        self.config.register_guild(**default_guild_settings)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:  # type: ignore
        await super().red_delete_data_for_user(requester=requester, user_id=user_id)

    # Listeners

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Listen for onboarding completed event"""
        if after.bot:
            # Member is a bot
            return

        if before.flags.completed_onboarding == after.flags.completed_onboarding or not after.flags.completed_onboarding:
            # Onboarding state is not changed or onboarding is not complete
            return

        await self.handle_onboarding(after)

    # Commands

    @commands.group()  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def onboarding_role(self, ctx: commands.GuildContext):
        pass

    @onboarding_role.command("status")
    async def get_status(self, ctx: commands.GuildContext):
        """Status of the cog."""
        onboarded_role = "⚠️ Unset"
        log_channel = "⚠️ Unset"

        role_id = await self.config.guild(ctx.guild).role()
        log_channel_id = await self.config.guild(ctx.guild).log_channel()

        if role_id:
            onboarded_role = ctx.guild.get_role(role_id)
            if onboarded_role:
                onboarded_role = onboarded_role.name
            else:
                onboarded_role = f"Set to role with ID `{role_id}`, but could not find role!"

        if log_channel_id:
            log_channel = ctx.guild.get_channel(log_channel_id)
            if log_channel:
                log_channel = log_channel.mention
            else:
                log_channel = f"Set to channel with ID `{log_channel_id}`, but could not find channel!"

        num_onboarded_users = len(await self.config.guild(ctx.guild).onboarded_users())

        embed = (
            discord.Embed(colour=(await ctx.embed_colour()))
            .add_field(name="Onboarded Role", value=onboarded_role)
            .add_field(name="Log Channnel", value=log_channel)
            .add_field(name="Onboarded User Count", value=num_onboarded_users, inline=False)
        )

        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send status.")

    @onboarding_role.command("role")
    async def set_role(self, ctx: commands.GuildContext, role: discord.Role):
        """
        Set the onboarding role.

        Examples:
        - `[p]onboarding_role role Users`
        - `[p]onboarding_role role 1253932390562590999`
        """
        await self.config.guild(ctx.guild).role.set(role.id)
        log.debug(f"Onboarded role set to {role.name} (ID {role.id})")
        await ctx.tick()

    @onboarding_role.command("logchannel")
    async def set_log_channel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """
        Set the log channel for onboarding events.

        Examples:
        - `[p]onboarding_role logchannel #log`
        - `[p]onboarding_role logchannel 1262905457120583720`
        """
        if channel.permissions_for(ctx.me).send_messages and channel.permissions_for(ctx.me).embed_links:
            await self.config.guild(ctx.guild).log_channel.set(channel.id)
            log.debug(f"Log channel set to {channel.name} (ID {channel.id})")
            await ctx.tick()
        else:
            await ctx.send(f"❌ I need the `Send Messages` and `Embed Links` permissions to send logs to {channel.mention}.")

    # Helpers

    async def handle_onboarding(self, member: discord.Member):
        """Handle onboarding completed event"""
        log.debug(f"User '{member.name}' (ID {member.id}) completed onboarding")
        guild = member.guild
        role_id = await self.config.guild(guild).role()

        if not role_id:
            # Welcome role is not set for this guild
            log.warning(f"Cannot grant onboarding role to '{member.name}' (ID {member.id}): Onboarding role not set.")
            return

        role = guild.get_role(role_id)
        if not role:
            # Welcome role is not found
            log.warning(
                f"Cannot grant onboarding role to '{member.name}' (ID {member.id}): "
                + f"Onboarding role set to ID {role_id} but could not found."
            )
            return

        try:
            await member.add_roles(role)
            log.info(f"User '{member.name}' (ID {member.id}) completed onboarding and was added to the onboarding role.")
            await self.send_log_message(member)
        except discord.Forbidden:
            error_msg = f"Adding onboarding role to {member.name} (ID {member.id}) was forbidden."
            log.warning(error_msg)
            await self.send_log_message(member, error_msg)

    async def send_log_message(self, member: discord.Member, error_msg: str = ""):
        """Send success or failure message to configured log channel"""
        log_channel_id = await self.config.guild(member.guild).log_channel()
        if not log_channel_id:
            # Log channel not defined.
            # We won't log a warning here since we'll assume the user does not
            # wish for onboarding events to be logged to a channel.
            return
        log_channel = member.guild.get_channel(log_channel_id)
        if not log_channel or not isinstance(log_channel, discord.TextChannel):
            # Log channel not found or invalid
            log.warning(
                "Attempted to send log message for onboarding completion, "
                + f"but the configured log channel with ID {log_channel_id} could not be found."
            )
            return

        if member.joined_at is None:
            onboarding_time = None
            log.debug("User's 'joined_at' attribute is None; could not calculate time to onboarding completion.")
        else:
            onboarding_time = humanise_timedelta(datetime.now(tz=timezone.utc) - member.joined_at)

        embed = discord.Embed(colour=(await self.bot.get_embed_colour(log_channel)), title="User Completed Onboarding")
        embed.add_field(name="Member", value=member.mention)
        if onboarding_time:
            embed.add_field(name="Time to Completion", value=str(onboarding_time))

        if error_msg:
            embed.add_field(name="⚠️ Error", value=error_msg, inline=False)
        else:
            embed.description = "User added to onboarding role."

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            log.warning(f"Sending onboarding log to {log_channel.name} (ID {log_channel_id}) was forbidden.")


def humanise_timedelta(delta: timedelta) -> str:
    days = delta.days
    seconds = delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    # Format the output
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")

    return ", ".join(parts)
