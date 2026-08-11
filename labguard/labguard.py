from typing import Literal

import discord
from discord import app_commands
from redbot.core import commands, Config
from redbot.core.bot import Red


# Replace with your Discord user ID. This user always passes the permission check.
# Only used in the event that an emergency change is needed.
OWNER_OVERRIDE_ID = 313542301022552074


class LabGuardGroup(app_commands.Group):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_OVERRIDE_ID:
            return True
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message(
            "You do not have permission to use this command.", ephemeral=True
        )
        return False


labguard_group = LabGuardGroup(
    name="labguard",
    description="Configure LabGuard",
    default_permissions=discord.Permissions(manage_guild=True),
    guild_only=True,
)
exempt_group = app_commands.Group(
    name="exempt",
    description="Manage roles exempt from the channel trigger",
    parent=labguard_group,
)


class LabGuard(commands.Cog):
    """Kicks users for acquiring a restricted role; bans (with message purge) for posting in a restricted channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0x4C414247, force_registration=True)
        self.config.register_guild(
            trigger_channel=None,
            log_channel=None,
            trigger_role=None,
            exempt_roles=[],
            ban_purge_seconds=86400,
        )

    async def _log(self, guild: discord.Guild, description: str, color: discord.Color):
        log_channel_id = await self.config.guild(guild).log_channel()
        if not log_channel_id:
            return
        log_channel = guild.get_channel(log_channel_id)
        if isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            try:
                await log_channel.send(embed=discord.Embed(description=description, color=color))
            except discord.HTTPException:
                pass

    async def _kick(self, member: discord.Member, reason: str):
        try:
            await member.kick(reason=reason)
            result = f"Kicked {member} (`{member.id}`) — {reason}"
            color = discord.Color.red()
        except discord.Forbidden:
            result = f"Failed to kick {member} (`{member.id}`) — missing permissions"
            color = discord.Color.orange()
        except discord.HTTPException as e:
            result = f"Failed to kick {member} (`{member.id}`) — {e}"
            color = discord.Color.orange()
        await self._log(member.guild, result, color)

    async def _ban(self, member: discord.Member, reason: str, purge_seconds: int):
        try:
            await member.ban(reason=reason, delete_message_seconds=purge_seconds)
            result = f"Banned {member} (`{member.id}`) — {reason} (purged last {purge_seconds // 3600}h of messages)"
            color = discord.Color.dark_red()
        except discord.Forbidden:
            result = f"Failed to ban {member} (`{member.id}`) — missing permissions"
            color = discord.Color.orange()
        except discord.HTTPException as e:
            result = f"Failed to ban {member} (`{member.id}`) — {e}"
            color = discord.Color.orange()
        await self._log(member.guild, result, color)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return
        guild_conf = self.config.guild(message.guild)
        trigger_channel = await guild_conf.trigger_channel()
        if not trigger_channel or message.channel.id != trigger_channel:
            return
        exempt_roles = await guild_conf.exempt_roles()
        author_role_ids = {r.id for r in message.author.roles}
        if author_role_ids.intersection(exempt_roles):
            return
        purge_seconds = await guild_conf.ban_purge_seconds()
        await self._ban(
            message.author,
            f"Posted in restricted channel <#{message.channel.id}>",
            purge_seconds,
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        trigger_role = await self.config.guild(after.guild).trigger_role()
        if not trigger_role:
            return
        before_ids = {r.id for r in before.roles}
        after_ids = {r.id for r in after.roles}
        if trigger_role in after_ids and trigger_role not in before_ids:
            await self._kick(after, f"Acquired restricted role <@&{trigger_role}>")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        trigger_role = await self.config.guild(member.guild).trigger_role()
        if trigger_role and trigger_role in {r.id for r in member.roles}:
            await self._kick(member, f"Joined already possessing restricted role <@&{trigger_role}>")

    @labguard_group.command(name="settings", description="View current LabGuard configuration")
    async def settings_cmd(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        conf = await self.config.guild(interaction.guild).all()
        trigger_channel = interaction.guild.get_channel(conf["trigger_channel"]) if conf["trigger_channel"] else None
        log_channel = interaction.guild.get_channel(conf["log_channel"]) if conf["log_channel"] else None
        trigger_role = interaction.guild.get_role(conf["trigger_role"]) if conf["trigger_role"] else None
        exempt_roles = [interaction.guild.get_role(r) for r in conf["exempt_roles"]]
        exempt_roles = [r.mention for r in exempt_roles if r]

        embed = discord.Embed(title="LabGuard Settings", color=discord.Color.blurple())
        embed.add_field(name="Trigger Channel", value=trigger_channel.mention if trigger_channel else "Not set", inline=False)
        embed.add_field(name="Trigger Role", value=trigger_role.mention if trigger_role else "Not set", inline=False)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "Not set", inline=False)
        embed.add_field(name="Exempt Roles", value=", ".join(exempt_roles) if exempt_roles else "None", inline=False)
        embed.add_field(name="Ban Purge Window", value=f"{conf['ban_purge_seconds'] // 3600}h", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @labguard_group.command(name="channel", description="Set the channel that triggers a ban on any message")
    @app_commands.describe(channel="Channel to monitor")
    async def channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        assert interaction.guild is not None
        await self.config.guild(interaction.guild).trigger_channel.set(channel.id)
        await interaction.response.send_message(f"Trigger channel set to {channel.mention}", ephemeral=True)

    @labguard_group.command(name="role", description="Set the role that triggers a kick when acquired")
    @app_commands.describe(role="Role to monitor")
    async def role_cmd(self, interaction: discord.Interaction, role: discord.Role):
        assert interaction.guild is not None
        await self.config.guild(interaction.guild).trigger_role.set(role.id)
        await interaction.response.send_message(f"Trigger role set to {role.mention}", ephemeral=True)

    @labguard_group.command(name="logchannel", description="Set the channel where kick logs are posted")
    @app_commands.describe(channel="Channel to post kick logs in")
    async def logchannel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        assert interaction.guild is not None
        await self.config.guild(interaction.guild).log_channel.set(channel.id)
        await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)

    @labguard_group.command(name="purgewindow", description="Set how many hours of messages to purge on channel-trigger bans")
    @app_commands.describe(hours="Hours of message history to delete (1-168, Discord's cap)")
    async def purgewindow_cmd(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168]):
        assert interaction.guild is not None
        await self.config.guild(interaction.guild).ban_purge_seconds.set(hours * 3600)
        await interaction.response.send_message(f"Ban purge window set to {hours}h", ephemeral=True)

    @labguard_group.command(name="disable", description="Clear the trigger channel or trigger role")
    @app_commands.describe(target="Which trigger to disable")
    async def disable_cmd(self, interaction: discord.Interaction, target: Literal["channel", "role"]):
        assert interaction.guild is not None
        if target == "channel":
            await self.config.guild(interaction.guild).trigger_channel.set(None)
        else:
            await self.config.guild(interaction.guild).trigger_role.set(None)
        await interaction.response.send_message(f"Trigger {target} cleared", ephemeral=True)

    @exempt_group.command(name="add", description="Exempt a role from the channel trigger")
    @app_commands.describe(role="Role to exempt")
    async def exempt_add(self, interaction: discord.Interaction, role: discord.Role):
        assert interaction.guild is not None
        async with self.config.guild(interaction.guild).exempt_roles() as roles:
            if role.id not in roles:
                roles.append(role.id)
        await interaction.response.send_message(f"{role.mention} is now exempt", ephemeral=True)

    @exempt_group.command(name="remove", description="Remove a role's exemption from the channel trigger")
    @app_commands.describe(role="Role to remove exemption from")
    async def exempt_remove(self, interaction: discord.Interaction, role: discord.Role):
        assert interaction.guild is not None
        async with self.config.guild(interaction.guild).exempt_roles() as roles:
            if role.id in roles:
                roles.remove(role.id)
        await interaction.response.send_message(f"{role.mention} is no longer exempt", ephemeral=True)