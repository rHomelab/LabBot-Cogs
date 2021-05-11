"""discord red-bot jail"""
import asyncio
import random
import string
from datetime import datetime as dt
from typing import Optional, Dict, Union, List, Callable, Sequence, Any, Literal
import contextlib
import functools

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import close_menu, start_adding_reactions


def humanise_timestamp(t):
    return dt.utcfromtimestamp(t).strftime("%Y-%m-%d %H:%M:%SZ")


class JailCog(commands.Cog):
    """Jail Cog"""

    def __init__(self, bot):
        self.STANDARD_CONTROLS = {"⬅️": self.prev_page, "⏹️": self.close_menu, "➡️": self.next_page}
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1249812384)

        default_guild_settings = {
            # [{id: str, channel_id: int, user: {id: int, name: str (abcd#1234), avatar: str}, created_at: float, deleted_at: float, reason: Optional[str]]}]
            "jails": [],
            # {$jail_id: [{author: {id: int, avatar: str, name: str (abcd#1234)}, id: int, content: str, edits[str], created_at: float, Optional[deleted: True]}]}
            "history": {},
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
    async def on_message_delete(self, message: discord.Message):
        if not isinstance(message.guild, discord.Guild):
            # The user has DM'd us. Ignore.
            return

        if message.author.bot:
            # User is a bot. Ignore.
            return

        jail = await self.get_jail(message.channel)
        if not jail:
            # Not a jail channel
            return

        async with self.config.guild(message.guild).history() as history:
            # Find the message
            message_match = list(filter(lambda m: m["id"] == message.id, history.get(jail["id"])))
            if not message:
                # Couldn't find the message or jail history
                return

            message = message_match[0]
            message.update({"deleted": True})

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.TextChannel):
            # It's not a textchannel (could be voice channel, etc)
            return

        # Check if it's a jail channel
        jail_info = await self.get_jail(channel)
        if not jail_info:
            return

        async with self.config.guild(channel.guild).history() as history:
            has_history = jail_info["id"] in history

        async with self.config.guild(channel.guild).jails() as jails:
            (jail,) = filter(lambda j: j["id"] == jail_info["id"], jails)
            if not has_history:
                # If there's no message history, the jail's existence doesn't need to be recorded
                return jails.pop(jails.index(jail))
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

        embeds = [await self.make_embed(ctx, "jail", j, i, len(all_jails)) for i, j in enumerate(all_jails)]
        await self.menu(ctx=ctx, pages=embeds, controls=self.get_controls(level="jail"), timeout=120.0, has_top_level=True)

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
        if role.position >= ctx.me.roles[-1]:
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
        for the role that you have configured as the base role with `[p]jails configure role`,\
        as this will allow all jailed members to see all jail channels
        **Note:** This channel must be in a channel category
        **Note:** This bot must be able to read/send messages in the channel
        """
        if not channel.category:
            return await ctx.send("This channel must be in a category.")

        if not channel.permissions_for(ctx.me).read_messages:
            return await ctx.send("I cannot read messages in that channel.")

        if not channel.permissions_for(ctx.me).send_messages:
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

    @commands.command()
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

        overwrites = self.make_overwrites(ctx, channel_template["permissions"])
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
                    "reason": reason,
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

        embeds = [await self.make_embed(ctx, "message", m, i, len(messages), jail_uuid) for i, m in enumerate(messages)]
        await self.menu(
            ctx=ctx,
            pages=embeds,
            controls=self.get_controls(level="message", has_parent=False, has_edits=bool(messages[0].get("edits"))),
            timeout=120.0,
        )

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

        def get_obj(id, ty):
            return guild.get_member(id) if ty == "member" else guild.get_role(id)

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

    async def make_embed(
        self,
        ctx: commands.Context,
        embed_type: Literal["jail", "message", "edit"],
        data: dict,
        index: int,
        length: int,
        optional_arg: Any = None,
    ) -> discord.Embed:
        """Used to generate embeds for the menus
        optional_arg is used to pass the jail UUID when creating message or edit embeds"""
        if embed_type == "jail":
            member = (
                getattr(ctx.guild.get_member(data["user"]["id"]), "mention", None)
                or f"""{data["user"]["name"]} ({data["user"]["name"]})"""
            )
            async with self.config.guild(ctx.guild).history() as history:
                if data["id"] in history:
                    messages = len(history[data["id"]])
                else:
                    messages = 0
            embed = (
                discord.Embed(
                    title="Jail Info",
                    description=f"""**Reason**\n{data["reason"] if data["reason"] else None}""",
                    colour=await ctx.embed_colour(),
                )
                .add_field(name="Member", value=member)
                .add_field(name="Messages", value=messages)
                .add_field(name="UUID", value="dgou")
                .add_field(name="Created at", value="2021-05-09 17:43:28Z")
                .add_field(
                    **{"name": "Deleted At", "value": humanise_timestamp(data["deleted_at"])}
                    if data.get("deleted_at")
                    else {"name": "Active", "value": "​"}
                )
                .set_footer(text=f"{index + 1} of {length}")
            )

        elif embed_type == "message":
            edits = len(data.get("edits")) if data.get("edits") else 0
            embed = (
                discord.Embed(colour=await ctx.embed_colour(), description=data["content"])
                .set_author(
                    name=f"""{data["author"]["name"]}#{data["author"]["discriminator"]} - {data["author"]["id"]}""",
                    icon_url=data["author"]["avatar"],
                )
                .add_field(name="Jail", value=optional_arg)
                .add_field(name="ID", value=data["id"])
                .set_footer(text=f"{index + 1} of {length}")
            )
            if edits:
                embed.add_field(name="Edits", value=edits)

        elif embed_type == "edit":
            embed = (
                discord.Embed(
                    title="Viewing edit history",
                    colour=await ctx.embed_colour(),
                    description=data["edits"][index - 1] if index else data["content"],
                )
                .set_author(
                    name=f"""{data["author"]["name"]}#{data["author"]["discriminator"]} - {data["author"]["id"]}""",
                    icon_url=data["author"]["avatar"],
                )
                .add_field(name="Jail", value=optional_arg)
                .add_field(name="ID", value=data["id"])
                .set_footer(text=f"Edit {index} of {length}" if index else "Original content")
            )
            if data.get("deleted"):
                embed.add_field(name="Deleted", value="​")
        return embed

        # Menu methods

    def with_emojis(
        self,
        emojis: Sequence[Union[str, discord.Emoji, discord.PartialEmoji]],
        message: Optional[discord.Message] = None,
        user: Optional[discord.abc.User] = None,
    ) -> Callable:
        """
        Match if the reaction is one of the specified emojis.
        Parameters
        ----------
        emojis : Sequence[Union[str, discord.Emoji, discord.PartialEmoji]]
            The emojis of which one we expect to be reacted.
        message : discord.Message
            Same as ``message`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.
        Returns
        -------
        ReactionPredicate
            The event predicate.
        """

        def predicate(r: discord.Reaction, u: discord.abc.User):
            return (message == r.message) and (user == u) and (str(r.emoji) in emojis)

        return predicate

    async def enforce_controls(self, message: discord.Message, controls: dict):
        """Make sure that the reactions on a menu are up to date with the controls"""
        for i, emote in enumerate(controls):
            try:
                if str(message.reactions[i].emoji) != emote:
                    break
            except IndexError:
                break
        else:
            # All the controls are present
            return
        # Remove incorrect reactions
        for index in range(i, len(message.reactions)):
            await message.clear_reaction(str(message.reactions[index].emoji))
        # Add correct reactions
        for r in controls:
            await message.add_reaction(r)

    def is_message_embed(self, embed) -> bool:
        """Determines whether an embed is part of the "view message history" menu"""
        return all(embed.author.icon_url, embed.fields[1].name == "ID", not embed.title)

    def is_edit_embed(self, embed) -> bool:
        """Determines whether an embed is part of the "view message edit history" menu"""
        return all(embed.author.icon_url, embed.fields[1].name == "ID", embed.title == "Viewing edit history")

    def is_jail_info_embed(self, embed) -> bool:
        """Determines whether an embed is part of the "view jail info" menu"""
        return all(embed.title == "Jail Info", embed.fields[0].name == "Member")

    def get_controls(
        self, *, level: Literal["jail", "message", "edit"], has_parent: bool = False, has_edits: bool = False
    ) -> dict:
        """Fetch controls for the menu based on whether or not certain actions are allowed"""
        controls = self.STANDARD_CONTROLS.copy()
        if level == "jail":
            controls.update({"🔄": self.enter_messages_menu})
        elif level == "message":
            if has_parent:
                controls.update({"🏠": self.enter_messages_menu})
            if has_edits:
                controls.update({"📝": self.enter_edits_menu})
        elif level == "edit":
            controls.update({"🏠": self.enter_messages_menu})
        return controls

    async def menu(
        self,
        ctx: commands.Context,
        pages: Union[List[str], List[discord.Embed]],
        controls: dict,
        message: discord.Message = None,
        page: int = 0,
        timeout: float = 30.0,
        has_top_level: bool = False,
    ):
        """
        An emoji-based menu
        .. note:: All pages should be of the same type
        .. note:: All functions for handling what a particular emoji does
                should be coroutines (i.e. :code:`async def`). Additionally,
                they must take all of the parameters of this function, in
                addition to a string representing the emoji reacted with.
                This parameter should be the last one, and none of the
                parameters in the handling functions are optional
        Parameters
        ----------
        ctx: commands.Context
            The command context
        pages: `list` of `str` or `discord.Embed`
            The pages of the menu.
        controls: dict
            A mapping of emoji to the function which handles the action for the
            emoji.
        message: discord.Message
            The message representing the menu. Usually :code:`None` when first opening
            the menu
        page: int
            The current page number of the menu
        timeout: float
            The time (in seconds) to wait for a reaction
        has_top_level: bool
            Whether the menu system can access the jail info menu
        Raises
        ------
        RuntimeError
            If either of the notes above are violated
        """
        if not isinstance(pages[0], (discord.Embed, str)):
            raise RuntimeError("Pages must be of type discord.Embed or str")
        if not all(isinstance(x, discord.Embed) for x in pages) and not all(isinstance(x, str) for x in pages):
            raise RuntimeError("All pages must be of the same type")
        for key, value in controls.items():
            maybe_coro = value
            if isinstance(value, functools.partial):
                maybe_coro = value.func
            if not asyncio.iscoroutinefunction(maybe_coro):
                raise RuntimeError("Function must be a coroutine")
        current_page = pages[page]

        if not message:
            if isinstance(current_page, discord.Embed):
                message = await ctx.send(embed=current_page)
            else:
                message = await ctx.send(current_page)
            # Don't wait for reactions to be added (GH-1797)
            # noinspection PyAsyncCall
            start_adding_reactions(message, controls.keys())
        else:
            try:
                if isinstance(current_page, discord.Embed):
                    await message.edit(embed=current_page)
                else:
                    await message.edit(content=current_page)
            except discord.NotFound:
                return

        # Message embeds may or may not have a parent level, and may or may not have a child level
        # Jail embeds will always have a child level, and never a parent level
        # Edit embeds will always have a parent level, and never a child level

        if self.is_jail_info_embed(current_page):
            controls = self.get_controls(level="jail")

        elif self.is_message_embed(current_page):
            has_edits = [i for i in current_page.fields if i.name == "Edits"]
            controls = self.get_controls(level="message", has_parent=has_top_level, has_edits=bool(has_edits))
            await self.enforce_controls(message, controls)

        elif self.is_edit_embed(current_page):
            controls = self.get_controls(level="edit")
            await self.enforce_controls(message, controls)

        try:
            react, _ = await ctx.bot.wait_for(
                "reaction_add",
                check=self.with_emojis(tuple(controls.keys()), message, ctx.author),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            if not ctx.me:
                return
            try:
                if message.channel.permissions_for(ctx.me).manage_messages:
                    await message.clear_reactions()
                else:
                    raise RuntimeError
            except (discord.Forbidden, RuntimeError):  # cannot remove all reactions
                for key in controls.keys():
                    try:
                        await message.remove_reaction(key, ctx.bot.user)
                    except discord.Forbidden:
                        return
                    except discord.HTTPException:
                        pass
            except discord.NotFound:
                return
        else:
            return await controls[react.emoji](ctx, pages, controls, message, page, timeout, react.emoji, has_top_level)

    async def enter_jail_menu(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool = False,
    ):
        """Method for entering the jail info menu from another menu"""
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove reacts
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)
        # Get jail ID from embed
        current_page = pages[page]
        # Embed type can only be "message"
        jail_id = current_page.fields[0].value
        # Get jail embeds
        async with self.config.guild(ctx.guild).jails() as jails:
            jail_info = sorted(
                jails,
                key=lambda m: m["created_at"],
            )
        pages = [await self.make_embed(ctx, "jail", j, i, len(pages)) for i, j in enumerate(jail_info)]
        # Reset page to 0
        page = jail_info.index([i for i in jail_info if i["id"] == jail_id][0])
        return await self.menu(ctx, pages, controls, message=message, page=page, timeout=timeout, has_top_level=has_top_level)

    async def enter_messages_menu(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool = False,
    ):
        """Method for entering the message history menu from another menu"""
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove reacts
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)
        # Get jail ID from embed
        current_page = pages[page]
        # Embed type can only be "jail" or "edit"
        jail_id = current_page.fields[2].value if self.is_jail_info_embed(current_page) else current_page.fields[0].value
        # Get message embeds
        async with self.config.guild(ctx.guild).history() as history:
            messages = sorted(
                history[jail_id],
                key=lambda m: m["created_at"],
            )

        pages = [await self.make_embed(ctx, "message", m, i, len(pages), jail_id) for i, m in enumerate(messages)]
        # Reset page to 0 or index of message if coming from "edit" menu
        if self.is_edit_embed(current_page):
            message_id = int(current_page.fields[1].value)
            page = messages.index([i for i in messages if i["id"] == message_id][0])
        else:
            page = 0
        return await self.menu(ctx, pages, controls, message=message, page=page, timeout=timeout, has_top_level=has_top_level)

    async def enter_edit_menu(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool = False,
    ):
        """Method for entering the edit history menu from the message history menu"""
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove reacts
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)
        # Get jail ID from embed
        current_page = pages[page]
        # Embed type can only be "edit"
        jail_id = current_page.fields[0].value
        message_id = current_page.fields[1].value
        # Get message embeds
        async with self.config.guild(ctx.guild).history() as history:
            message = [m for m in history[jail_id] if m["id"] == message_id][0]

        pages = [await self.make_embed(ctx, "edit", e, i, len(pages), jail_id) for i, e in enumerate(message["edits"])]
        # Reset page to 0
        page = 0
        return await self.menu(ctx, pages, controls, message=message, page=page, timeout=timeout, has_top_level=has_top_level)

    async def prev_page(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)
        if page == 0:
            page = len(pages) - 1  # Loop around to the last item
        else:
            page = page - 1
        return await self.menu(ctx, pages, controls, message=message, page=page, timeout=timeout, has_top_level=has_top_level)

    async def next_page(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool,
    ):
        perms = message.channel.permissions_for(ctx.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            with contextlib.suppress(discord.NotFound):
                await message.remove_reaction(emoji, ctx.author)
        if page == len(pages) - 1:
            page = 0  # Loop around to the first item
        else:
            page = page + 1
        return await self.menu(ctx, pages, controls, message=message, page=page, timeout=timeout, has_top_level=has_top_level)

    async def close_menu(
        self,
        ctx: commands.Context,
        pages: list,
        controls: dict,
        message: discord.Message,
        page: int,
        timeout: float,
        emoji: str,
        has_top_level: bool,
    ):
        with contextlib.suppress(discord.NotFound):
            await message.delete()
