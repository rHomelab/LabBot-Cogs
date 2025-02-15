"""discord red-bot role_welcome"""

import logging

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.views import ConfirmView

log = logging.getLogger("red.rhomelab.welcome")


class RoleWelcome(commands.Cog):
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
    async def on_member_update(self, before: discord.Member, after: discord.Member):  # noqa: PLR0911
        """Role addition event"""
        if after.bot:
            # Member is a bot
            return

        guild = after.guild

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
            log.error("User received role but welcome channel is not set for this guild")
            return

        welcome_channel = guild.get_channel(welcome_channel_id)
        if not welcome_channel or not isinstance(welcome_channel, discord.TextChannel):
            # Welcome channel doesn't exist or is not a text channel
            log.error("Welcome channel doesn't exist or is not a text channel")
            return

        always_welcome = await self.config.guild(guild).always_welcome()

        async with self.config.guild(guild).welcomed_users() as welcomed_users:
            if after.id in welcomed_users and not always_welcome:
                log.debug(f"User {after.id} ({after.global_name}) has already been welcomed")
                return
            if after.id not in welcomed_users:
                welcomed_users.append(after.id)

        await self.send_welcome_message(guild, welcome_channel, after)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, event: discord.RawMemberRemoveEvent):
        """Remove member from list of welcomed members"""
        guild = self.bot.get_guild(event.guild_id)
        if not await self.config.guild(guild).reset_on_leave():
            return
        user_id = event.user.id
        async with self.config.guild(guild).welcomed_users() as welcomed_users:
            if user_id in welcomed_users:
                log.debug(
                    f"User {user_id} ({event.user.global_name}) left the guild and has been removed from welcomed users list"
                )
                welcomed_users.remove(user_id)

    # Command groups

    @commands.group(name="rolewelcome")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def welcome(self, ctx: commands.Context):
        """
        Send a welcome message when a user is added to a role.

        This cog will send a configurable welcome message to a specified channel when a user
        receives a specified role.

        The specific logic used to decide when to welcome a user can be adjusted with the
        `always_welcome` and `reset_on_leave` settings.
        """
        pass

    # Commands

    @welcome.command("status")
    async def send_welcome_status(self, ctx: commands.GuildContext):
        """Status of the cog."""
        guild_role = "Unset"
        channel = "Unset"

        message = await self.config.guild(ctx.guild).message()
        message = message.replace("`", "")

        role_id = await self.config.guild(ctx.guild).role()
        channel_id = await self.config.guild(ctx.guild).channel()

        num_welcomed_users = len(await self.config.guild(ctx.guild).welcomed_users())

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
        embed.add_field(name="Welcomed Users", value=num_welcomed_users)
        embed.add_field(name="Always Welcome", value=always_welcome)
        embed.add_field(name="Reset on Leave", value=reset_on_leave)

        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send status.")

    @welcome.command("role")
    async def set_welcome_role(self, ctx: commands.GuildContext, role: discord.Role):
        """Set the role to be watched for new users.

        **Example:**
        - `[p]rolewelcome role <role>`
        - `[p]rolewelcome role @members`

        ⚠️ **NOTE**
        When changing the role, you will be prompted to reset the list of welcomed users.
        It is advisable to proceed with this to ensure all users are welcomed to the new role, however it may not be necessary
        in cases such as the recreation of a role or usage of a new role for the same purpose.
        See `[p]rolewelcome always_welcome` and `[p]rolewelcome reset_on_leave` for more information.
        """
        old_role = await self.config.guild(ctx.guild).role()
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.send(f"✅ Role set to {role.name}.")

        welcomed_users = await self.config.guild(ctx.guild).welcomed_users()
        if old_role is not None and len(welcomed_users) > 0 and old_role != role.id:
            await ctx.send(
                "\nYou will now be prompted to clear the list of welcomed users. It is advisable to"
                + " proceed with this to ensure all users are welcomed to the new role, however it may not"
                + " be necessary in cases such as the recreation of a role or usage of a new role for the same purpose."
            )
            await self.clear_welcomed_users(ctx)

    @welcome.command("channel")
    async def set_welcome_channel(self, ctx: commands.GuildContext, channel: discord.abc.GuildChannel):
        """Set the channel to send welcome messages to.

        **Example:**
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
        await ctx.tick(message=f"Welcome channel set to {channel.mention}.")

    @welcome.command("message")
    async def set_welcome_message(
        self,
        ctx: commands.GuildContext,
        *,
        message: str,
    ):
        """Set the welcome message.

        Format placeholders:
        - `{user}`: User mention (`@user`)
        - `{role}`: Role name
        - `{guild}`: Guild name

        **Example:**
        - `[p]rolewelcome message Welcome to {role} in {guild}, {user}!`
        - `[p]rolewelcome message default` to reset to default
        """
        if message == "default":
            message = self.default_welcome_message
        await self.config.guild(ctx.guild).message.set(message)
        await ctx.tick(message=f"Welcome message set to `{message}`.")

    @welcome.command("test")
    async def test_welcome_message(self, ctx: commands.GuildContext):
        """Test the welcome message in the current channel."""
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("Test channel (current) must be a text channel.")
            return
        await self.send_welcome_message(ctx.guild, ctx.channel, ctx.author)

    @welcome.command("always_welcome")
    async def set_always_welcome(self, ctx: commands.GuildContext):
        """
        Toggle whether users receive a welcome message every time they are assigned the role.

        - **If set to `true`**: Users will receive a welcome message **every time** they receive the role, even if they have
          had it before.
        - **If set to `false`**: Users will only receive a welcome message the **first time** they receive the role.

        **Default:** `true`

        **Example:**
        - `[p]rolewelcome always_welcome` - Toggles the setting.
        - `[p]rolewelcome status` - Shows the current status of this setting.

        ⚠️ **NOTE**
        This offers similar functionality to `reset_on_leave`. You should review both settings carefully to understand how they
        interact.

        - If `always_welcome` is `false`, a user will not receive another welcome message if they lose and regain the role.
        - If `always_welcome` is `false` but you still want users to be welcomed again after rejoining the guild, ensure that
          `reset_on_leave` is set to `true`.
        Run `[p]help rolewelcome reset_on_leave` for more information.
        """
        current_value = await self.config.guild(ctx.guild).always_welcome()
        new_value = not current_value
        await self.config.guild(ctx.guild).always_welcome.set(new_value)
        await ctx.send(f"✅ Always welcome is now `{new_value}`.")

    @welcome.command("reset_on_leave")
    async def set_reset_on_leave(self, ctx: commands.GuildContext):
        """
        Toggle whether a user's welcome status is reset when they leave the guild.

        - **If set to `true`**: When a user leaves the guild, their welcome status is reset, meaning they will receive a
          welcome message again if they rejoin and receive the role again.
        - **If `false`**: Their welcome status is retained, so they **will not** be welcomed again unless `always_welcome` is
          left set to the default value of `true`.

        **Default:** `true`

        **Example:**
        - `[p]rolewelcome reset_on_leave` - Toggles the setting.
        - `[p]rolewelcome status` - Shows the current status of this setting.

        ⚠️ **NOTE**
        This offers similar functionality to `always_welcome`. You should review both settings carefully to understand how they
        interact.

        - If both `reset_on_leave` and `always_welcome` are `false`, users who leave and rejoin will **not** be welcomed again.
        - If `always_welcome` is `true`, they will receive a welcome message each time they gain the role, regardless of the
          state of this setting or whether they have left and rejoined the guild.
        Run `[p]help rolewelcome always_welcome` for more information.
        """
        current_value = await self.config.guild(ctx.guild).reset_on_leave()
        new_value = not current_value
        await self.config.guild(ctx.guild).reset_on_leave.set(new_value)
        await ctx.send(f"✅ Reset on leave is now `{new_value}`.")

    @welcome.command()
    async def clear_welcomed_users(self, ctx: commands.GuildContext):
        """
        Clear the list of welcomed users.

        **Example:**
        - `[p]rolewelcome clear_welcomed_users` - Clears the list of welcomed users.
        - `[p]rolewelcome status` - Shows the current number of welcomed users.

        ⚠️ **NOTE**
        Clearing the list of welcomed users will cause all users to be welcomed again when they receive the role.
        See `[p]rolewelcome always_welcome` and `[p]rolewelcome reset_on_leave` for more information on welcome logic.
        """
        num_welcomed_users = len(await self.config.guild(ctx.guild).welcomed_users())
        if num_welcomed_users == 0:
            await ctx.send("The list of welcomed users is already empty.")
            return

        confirm_message = f"Do you wish to clear all {num_welcomed_users} users from the welcomed users list?"
        if ctx.command.name == "clear_welcomed_users":
            confirm_message += (
                "\n⚠️ Clearing the list of welcomed users will cause all users "
                "to be welcomed again if they receive the role again."
                f"\nSee `{ctx.clean_prefix}rolewelcome always_welcome` and `{ctx.clean_prefix}rolewelcome reset_on_leave`"
                "for more information on welcome logic."
            )

        view = ConfirmView(ctx.author)
        view.message = await ctx.send(confirm_message, view=view)
        await view.wait()
        if view.result:
            await self.config.guild(ctx.guild).welcomed_users.set(value=[])
            await ctx.send(f"✅ Cleared {num_welcomed_users} entries from the list of welcomed users.")
        else:
            await ctx.send("Welcomed users list was not cleared.")

    @welcome.command()
    async def backfill_welcomed_users(self, ctx: commands.Context, role: discord.Role):
        """
        Backfill the list of welcomed users with all members of a role.

        **Example:**
        - `[p]rolewelcome backfill_welcomed_users <role>`
        - `[p]rolewelcome backfill_welcomed_users @members`
        """
        guild = ctx.guild
        welcomed_users = await self.config.guild(guild).welcomed_users()
        num_added_users = 0
        async with ctx.typing():
            async with self.config.guild(guild).welcomed_users() as welcomed_users:
                for member in role.members:
                    if member.id not in welcomed_users:
                        welcomed_users.append(member.id)
                        num_added_users += 1
        await ctx.send(f"✅ Added {num_added_users} members of {role.name} to the list of welcomed users.")

    # Helpers
    # NOTE: this is a gross ugly hack for ruff false positive on line 330
    async def send_welcome_message(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,  # noqa: W293 RUF100
        member: discord.abc.User,
    ):
        """Send welcome message"""
        if not channel.permissions_for(guild.me).send_messages:
            log.error(f"Missing send messages permission for {channel.name} ({channel.id})")  # type: ignore
            return
        role_name = "role_unset"
        welcome_role_id = await self.config.guild(guild).role()  # type: ignore
        role_name = "role_unknown"
        if welcome_role_id and (welcome_role := guild.get_role(welcome_role_id)):
            role_name = welcome_role.name

        welcome_message = await self.config.guild(guild).message()
        welcome_message = welcome_message.format(user=member.mention, role=role_name, guild=guild.name)
        await channel.send(welcome_message)
