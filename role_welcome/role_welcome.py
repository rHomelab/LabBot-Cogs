"""discord red-bot role_welcome"""
import logging

import discord
from redbot.core import Config, checks, commands

log = logging.getLogger("red.rhomelab.welcome")

class RoleWelcomeCog(commands.Cog):
    """RoleWelcome Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95810282645)
        self.default_welcome_message = "Welcome to {role}, {user}!"

        default_guild_settings = {
            "channel": None,
            "role": None,
            "message": self.default_welcome_message,
            "welcomed_users": [],
            "always_welcome": True,
            "reset_on_leave": True,
        }

        self.config.register_guild(**default_guild_settings)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Role addition event"""
        if after.bot:
            # Member is a bot
            return

        guild = after.guild

        always_welcome = await self.config.guild(guild).always_welcome()

        async with self.config.guild(guild).welcomed_users() as welcomed_users:
            if after.id in welcomed_users and not always_welcome:
                return
            welcomed_users.append(after.id)

        role = await self.config.guild(guild).role()

        if not role:
            # Welcome role is not set for this guild
            return

        if before.roles == after.roles:
            # Roles haven't changed
            return

        if role in [role.id for role in before.roles] or role not in [role.id for role in after.roles]:
            # Member already had role or does not have role
            return

        welcome_channel_id = await self.config.guild(guild).channel()
        if not welcome_channel_id:
            # Welcome channel is not set for this guild
            return

        welcome_channel = guild.get_channel(welcome_channel_id)
        if not welcome_channel or not isinstance(welcome_channel, discord.TextChannel):
            # Welcome channel doesn't exist or is not a text channel
            log.error("Welcome channel doesn't exist or is not a text channel")
            return

        await self.send_welcome_message(guild, welcome_channel, after)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, event: discord.RawMemberRemoveEvent):
        """Remove member from list of welcomed members"""
        guild = self.bot.get_guild(event.guild_id)
        if await self.config.guild(guild).reset_on_leave() is False:
            return
        user_id = event.user.id
        async with self.config.guild(guild).welcomed_users() as welcomed_users:
            if user_id in welcomed_users:
                welcomed_users.remove(user_id)

    # Command groups

    @commands.group(name="rolewelcome")
    @commands.guild_only()
    @checks.mod()
    async def welcome(self, ctx: commands.Context):
        pass

    # Commands

    @welcome.command("status")
    async def send_welcome_status(self, ctx: commands.Context):
        """Status of the cog."""
        guild_role = "Unset"
        channel = "Unset"

        message = await self.config.guild(ctx.guild).message()
        message = message.replace("`", "")

        role_id = await self.config.guild(ctx.guild).role()
        channel_id = await self.config.guild(ctx.guild).channel()

        always_welcome = await self.config.guild(ctx.guild).always_welcome()
        reset_on_leave = await self.config.guild(ctx.guild).reset_on_leave()

        embed = discord.Embed(colour=(await ctx.embed_colour()))

        if role_id:
            guild_role = ctx.guild.get_role(role_id)
            if guild_role:
                guild_role = guild_role.name
            else:
                guild_role = f"Set to role with ID `{role_id}`, but could not find role!"

        if channel_id:
            guild_channel = ctx.guild.get_channel(channel_id)
            if guild_channel:
                channel = guild_channel.mention
            else:
                channel = f"Set to channel with ID `{channel_id}`, but could not find channel!"

        embed.add_field(name="Trigger Role", value=guild_role)
        embed.add_field(name="Welcome Channel", value=channel)
        embed.add_field(name="Welcome Message", value=f"`{message}`")
        embed.add_field(name="Always Welcome", value=always_welcome)
        embed.add_field(name="Reset on Leave", value=reset_on_leave)

        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send status.")

    @welcome.command("role")
    async def set_welcome_role(self, ctx: commands.Context, role: discord.Role):
        """Set the role to be watched for new users.

        Example:
        - `[p]rolewelcome role <role>`
        - `[p]rolewelcome role @members`
        """
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.tick()

    @welcome.command("channel")
    async def set_welcome_channel(self, ctx: commands.Context, channel: discord.abc.GuildChannel):
        """Set the channel to send welcome messages to.

        Example:
        - `[p]rolewelcome channel <channel>`
        - `[p]rolewelcome channel #welcome`
        """
        if not isinstance(channel, discord.TextChannel):
            await ctx.send("Welcome channel must be a text channel.")
            return
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"I need the `Send messages` permission before I can send messages in {channel.mention}.")
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.tick()

    @welcome.command("message")
    async def set_welcome_message(
        self,
        ctx: commands.Context,
        message: str,
    ):
        """Set the welcome message.

        Format placeholders:
        - `{user}`: User mention (`@user`)
        - `{role}`: Role name
        - `{guild}`: Guild name

        Example:
        - `[p]rolewelcome message Welcome to {role} in {guild}, {user}!`
        - `[p]rolewelcome message default` to reset to default
        """
        if message == "default":
            message = self.default_welcome_message
        await self.config.guild(ctx.guild).message.set(message)
        await ctx.tick()

    @welcome.command("test")
    async def test_welcome_message(self, ctx: commands.Context):
        """Test the welcome message in the current channel."""
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("Test channel (current) must be a text channel.")
            return
        await self.send_welcome_message(ctx.guild, ctx.channel, ctx.author)

    @welcome.command("always_welcome")
    async def set_always_welcome(self, ctx: commands.Context, value: str):
        """Set whether to welcome users to a role always or only on first join.

        If set to `true`, users will only be welcomed to the role the first time they join it.
        If set to `false`, users will be welcomed to the role every time they join it.

        Example:
        - `[p]rolewelcome always_welcome true`
        - `[p]rolewelcome always_welcome false`
        """
        try:
            value_bool = await self.str_to_bool(value)
        except ValueError:
            await ctx.send("Invalid value. Use `true` or `false`.")
            return
        await self.config.guild(ctx.guild).always_welcome.set(value_bool)
        await ctx.tick()

    @welcome.command("reset_on_leave")
    async def set_reset_on_leave(self, ctx: commands.Context, value: str):
        """Set whether to reset a user's welcomed status on leave.

        This setting affects the specific behaviour of the `always_welcome` setting when it is set to **`false`**.

        With that in mind, the following information assumes that `always_welcome` is `false`.

        If set to `true` and a user has already been welcomed once, then they leave the server, re-joins, and is given the role again, they **will** be welcomed.
        If set to `false`: a user will not be removed from the welcomed users list on leave and will not be welcomed again if they re-join and join the trigger role.

        Example:
        - `[p]rolewelcome reset_on_leave true`
        - `[p]rolewelcome reset_on_leave false`
        """
        try:
            value_bool = await self.str_to_bool(value)
        except ValueError:
            await ctx.send("Invalid value. Use `true` or `false`.")
            return
        await self.config.guild(ctx.guild).reset_on_leave.set(value_bool)
        await ctx.tick()

    # Helpers

    async def send_welcome_message(self, guild: discord.Guild, channel: discord.TextChannel, member: discord.abc.User):
        """Send welcome message"""
        if not channel.permissions_for(guild.me).send_messages:
            log.error(f"Missing send messages permission for {channel.name} ({channel.id})")
            return
        role_name = "role_unset"
        welcome_role_id = await self.config.guild(guild).role()
        if welcome_role_id:
            role_name = "role_unknown"
            welcome_role = guild.get_role(welcome_role_id)
            if welcome_role:
                role_name = welcome_role.name

        welcome_message = await self.config.guild(guild).message()
        welcome_message = welcome_message.format(user=member.mention, role=role_name, guild=guild.name)
        await channel.send(welcome_message)

    async def str_to_bool(self, value: str | bool) -> bool | None:
        """Strict boolean conversion
        
        Returns `True` (bool) if value is `True` (bool) or one of "true", "yes", or "y" (case-insensitive str).
        Returns `False` (bool) if value is `False` (bool) or one of "false", "no", or "n" (case-insensitive str).
        Otherwise raises `ValueError`.        
        """
        if isinstance(value, bool):
            return value
        if value.lower() in ["true", "yes", "y"]:
            return True
        if value.lower() in ["false", "no", "n"]:
            return False
        raise ValueError
