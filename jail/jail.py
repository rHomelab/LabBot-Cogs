"""discord red-bot jail"""
import asyncio
import random
import string
from datetime import datetime as dt
from typing import Optional, Dict, Union, List

import discord
from redbot.core import Config, checks, commands


class JailCog(commands.Cog):
    """Jail Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1249812384)

        default_guild_settings = {
            "jails": [],  # [{id: str, channel_id: int, user: {id: int, name: str (abcd#1234), avatar: str}, created_at: float, deleted_at: float}]
            "history": {},  # {$jail_id: [{author: {id: int, avatar: str, name: str (abcd#1234)}, id: int, content: str, edits[str], created_at: float}]}
            "role_id": None,  # int (ID of the role to add to jailed member)
            "template": {
                "category_id": None,  # int
                "permissions": {},  # {$object_id: {type: Literal[member, role], overwrite: {allow: int, deny: int}}}
                "topic": None,  # The channel topic
                "welcome_msg": None,  # The message to be sent by the bot as the first message in the jail
            },
        }

        self.config.register_guild(**default_guild_settings)

    # Events

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        jail = await self.get_jail(message.channel)
        if not jail:
            # Not a jail channel
            return

        async with self.config.guild(message.guild).history() as history:
            if jail["id"] not in history:
                # Initiate jail history if it doesn't already exist
                history.update({jail["id"]: []})

            history[jail["id"]].append(
                {
                    "author": {
                        "id": message.author.id,
                        "avatar": message.author.avatar_url,
                        "name": f"{message.author.name}#{message.author.discriminator}",
                    },
                    "id": message.id,
                    "content": message.clean_content,
                    "created_at": dt.utcnow().timestamp(),
                }
            )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not isinstance(before.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        if before.clean_content == after.clean_content:
            # Clean content has not changed
            return

        jail = await self.get_jail(before.channel)
        if not jail:
            # Not a jail channel
            return

        # If clean content has changed, add change to settings[history]
        async with self.config.guild(before.guild).history() as history:
            (message,) = filter(lambda m: m["id"], history[jail["id"]])
            if "edits" not in message:
                # Initialise edits column
                message.update({"edits": []})

            message["edits"].append(after.clean_content)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.TextChannel):
            # It's not a textchannel (could be voice channel, etc)
            return

        # Check if it's a jail channel
        jail_info = await self.get_jail(channel.guild, channel_id=channel.id)
        if not jail_info:
            return

        async with self.config.guild(channel.guild).jails() as jails:
            (jail,) = filter(lambda j: j["id"] == jail_info["id"], jails)
            jail.update({"deleted_at": dt.utcnow().timestamp()})
            jail.pop("channel_id")

    # Command groups

    @commands.group("jails")
    @checks.mod()
    @commands.guild_only()
    async def _jails(self, ctx: commands.Context):
        if ctx.invoked_subcommand:
            return

        async with self.config.guild(ctx.guild).jails() as jails:
            # Most recent first
            all_jails = sorted(jails, key=lambda j: j["created_at"], reverse=True)

        humanise_timestamp = lambda t: dt.utcfromtimestamp(t).strftime("%Y-%m-%d %H:%M:%SZ")

        async with self.config.guild(ctx.guild).history() as history:
            embeds = []
            for i, jail in enumerate(all_jails):
                embed = discord.Embed(colour=await ctx.embed_colour())
                embed.set_author(name=f"Jails - page {i + 1} of {len(all_jails)}", icon_url=jail["user"]["avatar"])
                member = (
                    getattr(ctx.guild.get_member(jail["user"]["id"]), "mention", None)
                    or f"""{jail["user"]["name"]} ({jail["user"]["name"]})"""
                )
                embed.add_field(name="Member", value=member)
                embed.add_field(name="Created At", value=humanise_timestamp(jail["created_at"]))
                if jail.get("deleted_at"):
                    embed.add_field(name="Deleted At", value=humanise_timestamp(jail["deleted_at"]))
                else:
                    embed.add_field(name="Active", value="​")
                embed.add_field(name="Messages", value=len(history[jail["id"]]))
                embed.add_field(name="UUID", value=f"""`{jail["id"]}`""")
                embeds.append(embed)

    @_jails.group(name="configure")
    async def _jails_configure(self, ctx: commands.Context, channel: discord.CategoryChannel):
        pass

    @_jails_configure.command("role")
    async def jails_configure_role(self, ctx, role: discord.Role):
        """Configure the base role to be used for jailing people.
        This role should ideally disable send message perms in all other channels.
        Send messages perms for the automatically created jail channels will be set by the bot.
        """
        if not role.position:
            return await ctx.send("Invalid role.")
        if role.position >= ctx.guild.me.roles[-1]:
            return await ctx.send("Role is too high in the role list; I can not apply it to users.")

        await self.config.guild(ctx.guild).role_id.set(role.id)
        await ctx.send(
            f"Set jail role to {role.mention}",
            allowed_mentions=discord.AllowedMentions(roles=False),
        )

    # Commands

    @_jails_configure.command("channel")
    async def jails_configure_channel(self, ctx, channel: discord.TextChannel):
        """This is the channel that the bot will use as a template for creating jails.
        Permissions will be copied, and the automatically created jail channels will be in the same category as this channel.
        
        **Note:** It is important that you do *not* set read messages/view channel perms in this channel\
        for the role that you have configured as the base role with `[p]jails configure role`, as this will allow all jailed members to see all jail channels
        **Note:** This channel must be in a channel category
        **Note:** This bot must be able to read/send messages in the channel
        """
        if not channel.category:
            return await ctx.send("This channel must be in a category.")

        if not channel.permissions_for(ctx.guild.me).read_messages:
            return await ctx.send("I cannot read messages in that channel.")

        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send("I cannot send messages in that channel.")

        # Check channel permissions for the jail base role
        role_id = await self.config.guild(ctx.guild).role_id()
        if role_id:
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send("The configured role no longer exists.")
            role_perms = channel.permissions_for(role)
            if role_perms.view_channel or role_perms.read_messages:
                return await ctx.send(
                    "The configured role can view this channel. Please adjust the channel permissions before proceeding."
                )

        async with self.config.guild(ctx.guild).template() as template:
            welcome_msg = template["welcome_msg"]
            template = {
                "category_id": channel.category_id,
                "permissions": self.store_overwrites(channel),
                "topic": channel.topic,
                "welcome_msg": welcome_msg,
            }
        await ctx.send("Channel template configured.")

    @commands.command(name="jail")
    @commands.guild_only()
    @checks.mod()
    async def jail(self, ctx: commands.Context, user: discord.Member, time: Optional[int] = None, *, reason: str = None):
        """Jail a user until they are bailed or for a set time"""
        role_id = await self.config.guild(ctx.guild).role_id()
        if not role_id:
            return await ctx.send("Base role not configured.")
        base_role = ctx.guild.get_role(role_id)
        if not base_role:
            return await ctx.send("Configured base role no longer exists.")
        try:
            await user.add_roles(base_role)
        except discord.Forbidden:
            return await ctx.send("I do not have permission to add roles to this user.")

        # Generate a 4 character string for uniqueness
        uuid = await self.generate_uid(ctx.guild)
        channel_template = await self.config.guild(ctx.guild).template()

        if not channel_template["category_id"]:
            return await ctx.send("Jail is not configured.")
        category_channel = ctx.guild.get_channel(channel_template["category_id"])
        if not category_channel:
            return await ctx.send("Configured jail area could not be found.")

        overwrites = self.make_overwrites(channel_template["permissions"])
        overwrites.update({user: discord.PermissionOverwrite(view_channel=True, send_messages=True)})

        try:
            jail_channel = await category_channel.create_text_channel(
                f"jail-{uuid}",
                overwrites=overwrites,
                reason=f"Jail for {user.name}#{user.discriminator}",
            )
        except discord.Forbidden:
            return await ctx.send("I do not have permission to create the jail channel.")

        # Log channel creation
        async with self.config.guild(ctx.guild).jails() as jails:
            jails.append(
                {
                    "channel_id": jail_channel.id,
                    "created_at": dt.utcnow().timestamp(),
                    "id": uuid,
                    "user": {
                        "id": user.id,
                        "name": user.display_name or f"{user.name}#{user.discriminator}",
                        "avatar": user.avatar_url,
                    },
                }
            )

        welcome_msg = channel_template["welcome_msg"]
        if welcome_msg:
            await jail_channel.send(welcome_msg)

        await ctx.send(f"User jailed {jail_channel.mention}")

        if time:
            await asyncio.sleep(time * 60)
            await jail_channel.delete(
                reason=f"Jail channel for {user.name}#{user.discriminator} deleted after {time * 60} minutes"
            )

    @commands.command(name="bail")
    @commands.guild_only()
    @checks.mod()
    async def bail(self, ctx: commands.Context, user: discord.Member):
        """Bail a user out of jail.
        The bot will remove a user's jailed role and delete the associated channel
        """
        # TODO clean stuff up with this function
        async with self.config.guild(ctx.guild).jails() as jails:
            # Filter by open jails corresponding to the mentioned user
            user_jails = [i for i in jails if i["id"] == user.id and (i.get("channel_id") and not i.get("deleted_at"))]
            if not user_jails:
                # No open jails exist for this user
                return await ctx.send("This user is not jailed.")

            (user_jail,) = user_jails
            channel = ctx.guild.get_channel(user_jail["channel_id"])
            await channel.delete(reason=f"Jailed user {user.name}#{user.discriminator} bailed")

        role_id = await self.config.guild(ctx.guild).role_id()
        role = ctx.guild.get_role(role_id)
        reason = f"Bailed out of jail at the request of {ctx.author.name}#{ctx.author.discriminator}"
        await user.remove_roles(role, reason=reason)
        await ctx.send(
            f"Bailed {user.mention} out of jail.",
            allowed_mentions=discord.AllowedMentions(users=False),
        )

    @_jails.command(name="status")
    async def jails_status(self, ctx: commands.Context, channel: discord.CategoryChannel):
        """Show status of the jails
        Example:
        - `[p]jails status`
        """
        not_configured = "*Not configured*"
        # Get values for embed
        role_id = await self.config.guild(ctx.guild).role_id()
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send("The configured role no longer exists. Please re-configure this setting before proceeding.")

        async with self.config.guild(ctx.guild).jails() as jails:
            jails_list = jails

        async with self.config.guild(ctx.guild).template() as template:
            template_dict = template

        if not template_dict["permissions"]:
            return await ctx.send("The template channel has not been configured yet. Please configure this before proceeding")

        category = ctx.guild.get_channel(template["category_id"])
        if not category:
            return await ctx.send("The configured channel category")

        description = f"""**Channel Topic**\n{template_dict["topic"] or not_configured}\n\n**Welcome Message**\n{template_dict["welcome_msg"] or not_configured}"""

        # Create embed
        data = (
            discord.Embed(
                description=(description[:1996] + "...") if len(description) > 2000 else description,
                colour=await ctx.embed_colour(),
            )
            .add_field(name="Jailed", value=f"{len(jails_list)} users")
            .add_field(name="Role", value=role.mention)
            .add_field(name="Channel Category", value=category.mention)
        )

        # Send embed
        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send the cog status.")

    @_jails.command("replay")
    async def jails_replay(self, ctx, jail_uuid: str):
        """Replay the message history of a deleted jail"""
        jail = await self.get_jail(jail_uuid)
        if not jail:
            return await ctx.send("Jail does not exist.")
        elif not jail.get("deleted_at"):
            return await ctx.send("Jail still active.")

        async with self.config.guild(ctx.guild).history() as history:
            messages = sorted(
                history[jail["id"]],
                key=lambda m: m["created_at"],
            )

        embeds = []
        for i, message in enumerate(messages):
            embed = (
                discord.Embed(
                    title=f"Messages for jail {jail_uuid} - Page {i} of {len(messages)}",
                    colour=await ctx.embed_colour(),
                    description=message["content"],
                )
                .set_author(name=message["author"]["name"], icon_url=message["author"]["avatar"])
                .set_footer(text=f"Messages for jail {jail_uuid} - {i} of {len(messages)}")
            )
            if message.get("edits"):
                embed.add_field("Edits", value=len(message["edits"]))
            embeds.append(embed)
        # TODO create menu system

    # Helper functions

    async def generate_uid(self, guild: discord.Guild, length: int = 4):
        """Generates a historically unique ID for the jail channel"""
        letters = string.ascii_lowercase
        async with self.config.guild(guild).jails() as jails:
            new_id = "".join(random.choice(letters) for _ in range(length))
            while new_id in [i["id"] for i in jails]:
                new_id = "".join(random.choice(letters) for _ in range(length))
            return new_id

    def store_overwrites(self, channel: discord.TextChannel) -> Dict[int, Dict[str, Union[str, List[int]]]]:
        """Translates a group of permission overwrites into storable types"""
        o_type = (
            lambda o: "member" if isinstance(o, discord.Member) else "role"
        )  # Overwrites can only be applied to members or roles
        data = {k.id: {"type": o_type(k), "overwrites": [i.value for i in v.pair()]} for k, v in channel.overwrites.items()}
        return data

    def make_overwrites(
        self, ctx: commands.Context, data: dict
    ) -> Dict[Union[discord.Role, discord.Member], discord.PermissionOverwrite]:
        """Translates a group of storable permission overwrites into discord models"""
        guild = ctx.guild
        get_obj = lambda id, ty: guild.get_member(id) if ty == "member" else guild.get_role(id)
        d = {}
        for o_id, o_details in data.items():
            for_object = get_obj(o_id, o_details["type"])
            pair = [discord.Permissions(i) for i in o_details["overwrites"]]
            overwrites = discord.PermissionOverwrite.from_pair(*pair)
            d.update({for_object: overwrites})
        return d

    async def is_jail_channel(self, channel: discord.TextChannel) -> bool:
        async with self.config.guild(channel.guild).jails() as jails:
            valid_jails = [j for j in jails if j.get("channel_id") == channel.id]
            return bool(len(valid_jails))

    async def get_jail(
        self,
        channel: discord.TextChannel,
        *,
        uuid: str = None,
    ) -> Union[dict, None]:
        """Fetch a jail dict by uuid or channel ID"""
        if channel:
            # If you pass the channel you don't need to check existence before calling this method
            # But you will need to check after calling this method
            check = await self.is_jail_channel(channel)
            if not check:
                return None
        async with self.config.guild(channel.guild).jails() as jails:
            (jail,) = filter(lambda j: j["id"] == uuid or j["channel_id"] == channel.id, jails)
            return jail