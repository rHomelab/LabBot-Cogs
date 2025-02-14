import uuid
from io import BytesIO
from os import path
from typing import List

import discord
from chat_exporter import chat_exporter
from discord import CategoryChannel, NotFound
from redbot.core import Config, commands, data_manager

from jail.abstracts import JailABC, JailConfigHelperABC, JailSetABC


class Jail(JailABC):
    @classmethod
    def new(  # noqa: PLR0913
        cls,
        ctx: commands.Context,
        datetime: int,
        channel_id: int,
        role_id: int,
        active: bool,
        jailer: int,
        user: int,
        user_roles: List[int],
        archive_id: uuid.UUID,
    ):
        return cls(
            datetime=datetime,
            channel_id=channel_id,
            role_id=role_id,
            active=active,
            jailer=jailer,
            user=user,
            user_roles=user_roles,
            archive_id=archive_id,
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return Jail.new(
            ctx,
            datetime=data["datetime"],
            channel_id=data["channel_id"],
            role_id=data["role_id"],
            active=data["active"],
            jailer=data["jailer"],
            user=data["user"],
            user_roles=data["user_roles"],
            archive_id=data["archive_id"],
        )

    def to_dict(self) -> dict:
        return {
            "datetime": self.datetime,
            "channel_id": self.channel_id,
            "role_id": self.role_id,
            "active": self.active,
            "jailer": self.jailer,
            "user": self.user,
            "user_roles": self.user_roles,
            "archive_id": str(self.archive_id),
        }

    def __str__(self) -> str:
        return f"<@{self.user}> <t:{self.datetime}>: {self.archive_id}"


class JailSet(JailSetABC):
    @classmethod
    def new(cls, ctx: commands.Context, jails: List[JailABC]):
        return cls(jails=jails)

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: list):
        return JailSet.new(ctx, [Jail.from_storage(ctx, j) for j in data])

    def to_list(self) -> list:
        return [j.to_dict() for j in self.jails]

    def get_active_jail(self) -> JailABC:
        for jail in reversed(self.jails):
            if jail.active:
                return jail
        return None

    def add_jail(self, jail: JailABC):
        self.jails.append(jail)

    def deactivate_jail(self, archive_uuid: uuid.UUID):
        for jail in reversed(self.jails):
            if jail.active:
                jail.archive_id = archive_uuid
                jail.active = False


class JailConfigHelper(JailConfigHelperABC):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=1289862744207523842002, cog_name="JailCog")
        self.config.register_guild(jails={})

    async def set_category(self, ctx: commands.Context, category: CategoryChannel):
        await self.config.guild(ctx.guild).category.set(category.id)

    async def get_category(self, guild: discord.Guild):
        channel = guild.get_channel(await self.config.guild(guild).category())
        if channel is None:
            return None
        return channel

    async def create_jail(self, ctx: commands.Context, datetime: int, member: discord.Member) -> Jail:
        category = await self.get_category(ctx.guild)
        if category is None:
            return None
        reason = f"Jail: {ctx.author.name} created a jail for: {member.name}"

        role = await ctx.guild.create_role(name=f"Jail:{member.name}", mentionable=False, reason=reason)
        perms = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, read_messages=True, send_messages=True
        )
        channel = await ctx.guild.create_text_channel(
            name=f"{member.name}-timeout",
            reason=reason,
            category=category,
            news=False,
            topic=f"{member.display_name} was bad and now we're here. DO NOT LEAVE! Leaving is evading and will "
            f"result in an immediate ban.",
            nsfw=False,
        )
        await channel.set_permissions(role, overwrite=perms)
        async with self.config.guild(ctx.guild).jails() as jails:
            jail = Jail.new(
                ctx, datetime, channel.id, role.id, True, ctx.author.id, member.id, [r.id for r in member.roles], None
            )
            if str(member.id) in jails.keys():
                jailset = JailSet.from_storage(ctx, jails[str(member.id)])
            else:
                jailset = JailSet.new(ctx, [])
            jailset.add_jail(jail)
            jails[str(member.id)] = jailset.to_list()

        return jail

    async def restore_user_roles(self, ctx: commands.Context, jail: JailABC, member: discord.Member):
        for rid in jail.user_roles:
            try:
                role = ctx.guild.get_role(rid)
                if role is not None:
                    await member.add_roles(role, reason="Jail: Restore Roles")
            except NotFound:
                pass

    async def jail_user(self, ctx: commands.Context, jail: Jail, member: discord.Member):
        reason = "Jail: Timeout"
        for r in member.roles:
            if r.name != "@everyone":
                await member.remove_roles(r, reason=reason)

        role = ctx.guild.get_role(jail.role_id)
        if role is not None:
            await member.add_roles(role, reason=reason)

    async def free_user(self, ctx: commands.Context, jail: JailABC, member: discord.Member):
        await self.restore_user_roles(ctx, jail, member)

        role = ctx.guild.get_role(jail.role_id)
        if role is not None:
            await member.remove_roles(role, reason="Jail: Free User")

    async def cleanup_jail(self, ctx: commands.Context, jail: JailABC):
        try:
            role = ctx.guild.get_role(jail.role_id)
            if role is not None:
                await role.delete(reason="Jail: Jail deleted.")
            channel = ctx.guild.get_channel(jail.channel_id)
            if channel is not None:
                archive_uuid = uuid.uuid4()
                await self.archive_channel(ctx, channel, archive_uuid)
                await channel.delete(reason="Jail: Jail deleted.")
                async with self.config.guild(ctx.guild).jails() as jails:
                    if str(jail.user) in jails:
                        jailset = JailSet.from_storage(ctx, jails[str(jail.user)])
                        jailset.deactivate_jail(archive_uuid)
                        jails[str(jail.user)] = jailset.to_list()
        except NotFound:
            pass

    async def archive_channel(self, ctx: commands.Context, channel: discord.TextChannel, archive_uuid: uuid.UUID):
        """Archive supplied channel to an HTML file"""
        # Copied this from tig because the work was already done :)
        if ctx.guild is None:
            raise TypeError("ctx.guild is None")
        data_path = data_manager.cog_data_path(self)
        transcript_file_name = f"{archive_uuid}.html"
        transcript_path = path.join(data_path, transcript_file_name)

        async with ctx.typing():
            transcript = await chat_exporter.export(
                channel=channel,
                tz_info="UTC",  # Original had this as tz_info=
            )
            if transcript is None:
                await ctx.send("None transcript")
                return

            # Encode transcript to bytes object
            transcript_object = BytesIO(initial_bytes=transcript.encode())

            # Write transcript to storage
            # fixme: this is rly bad, dont use possibly blocking functions in async.
            with open(transcript_path, "wb") as file:  # noqa: ASYNC101
                file.write(transcript_object.getbuffer())

    async def get_jail_by_user(self, ctx: commands.Context, user: discord.User) -> JailABC:
        async with self.config.guild(ctx.guild).jails() as jails:
            if str(user.id) in jails:
                return JailSet.from_storage(ctx, jails[str(user.id)]).get_active_jail()
        return None

    async def get_jailset_by_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> JailSetABC:
        async with self.config.guild(ctx.guild).jails() as jails:
            for jailsetkey in jails:
                jailset = JailSet.from_storage(ctx, jails[jailsetkey])
                for jail in jailset.jails:
                    if jail.channel_id == channel.id:
                        return jailset
        return None

    async def get_jailset_by_user(self, ctx: commands.Context, user: discord.User) -> JailSetABC:
        async with self.config.guild(ctx.guild).jails() as jails:
            if str(user.id) in jails:
                return JailSet.from_storage(ctx, jails[str(user.id)])
        return None
