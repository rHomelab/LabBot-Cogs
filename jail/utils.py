import json
from typing import List

import discord
from discord import CategoryChannel, NotFound
from redbot.core import commands, Config

from jail.abstracts import EditABC, MessageABC, JailABC, JailConfigHelperABC, JailSetABC


class Edit(EditABC):

    @classmethod
    def new(cls, ctx: commands.Context, datetime: int, content: str):
        return cls(
            datetime=datetime,
            content=content
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return Edit.new(ctx, data['datetime'], data['content'])

    def to_dict(self) -> dict:
        return {
            "datetime": self.datetime,
            "content": self.content
        }


class Message(MessageABC):

    @classmethod
    def new(cls, ctx: commands.Context, message_id: int, datetime: int, author: int, deleted: bool, deleted_datetime:
            int, content: str, edits: List[EditABC]):
        return cls(
            message_id=message_id,
            datetime=datetime,
            author=author,
            deleted=deleted,
            deleted_datetime=deleted_datetime,
            content=content,
            edits=edits
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return Message.new(ctx, message_id=int(data['message_id']), datetime=data['datetime'], author=data['author'],
                           deleted=data['deleted'], deleted_datetime=data['deleted_datetime'], content=data['content'],
                           edits=[Edit.from_storage(ctx, e) for e in data['edits']])

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "datetime": self.datetime,
            "author": self.author,
            "deleted": self.deleted,
            "deleted_datetime": self.deleted_datetime,
            "content": self.content,
            "edits": [e.to_dict() for e in self.edits]
        }


class Jail(JailABC):

    @classmethod
    def new(cls, ctx: commands.Context, datetime: int, channel_id: int, role_id: int, active: bool, jailer: int,
            user: int, user_roles: List[int], messages: List[Message]):
        return cls(
            datetime=datetime,
            channel_id=channel_id,
            role_id=role_id,
            active=active,
            jailer=jailer,
            user=user,
            user_roles=user_roles,
            messages=[]
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return Jail.new(ctx, datetime=data['datetime'], channel_id=data['channel_id'], role_id=data['role_id'],
                        active=data['active'], jailer=data['jailer'], user=data['user'], user_roles=data['user_roles'],
                        messages=[Message.from_storage(ctx, m) for m in data['messages']])

    def to_dict(self) -> dict:
        return {
            "datetime": self.datetime,
            "channel_id": self.channel_id,
            "role_id": self.role_id,
            "active": self.active,
            "jailer": self.jailer,
            "user": self.user,
            "user_roles": self.user_roles,
            "messages": [m.to_dict() for m in self.messages]
        }


class JailSet(JailSetABC):

    @classmethod
    def new(cls, ctx: commands.Context, jails: List[JailABC]):
        return cls(
            jails=jails
        )

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

    def deactivate_jail(self):
        for jail in reversed(self.jails):
            if jail.active:
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

        role = await ctx.guild.create_role(
            name=f"Jail:{member.name}",
            mentionable=False,
            reason=reason
        )
        perms = discord.PermissionOverwrite(view_channel=True, read_message_history=True, read_messages=True,
                                            send_messages=True)
        channel = await ctx.guild.create_text_channel(
            name=f"{member.name}-timeout",
            reason=reason,
            category=category,
            news=False,
            topic=f"{member.display_name} was bad and now we're here. DO NOT LEAVE! Leaving is evading and will "
                  f"result in an immediate ban.",
            nsfw=False
        )
        await channel.set_permissions(role, overwrite=perms)
        async with self.config.guild(ctx.guild).jails() as jails:
            jail = Jail.new(ctx, datetime, channel.id, role.id, True, ctx.author.id, member.id,
                            [r.id for r in member.roles], [])
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
            await channel.delete(reason="Jail: Jail deleted.")
            async with self.config.guild(ctx.guild).jails() as jails:
                if str(jail.user) in jails:
                    jailset = JailSet.from_storage(ctx, jails[str(jail.user)])
                    jailset.deactivate_jail()
                    jails[str(jail.user)] = jailset.to_list()
        except NotFound:
            pass

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

    async def save_message_to_jail(self, ctx: commands.Context, jailset: JailSetABC, message: discord.Message,
                                   time: int):
        jail = jailset.get_active_jail()
        if jail is not None:
            jail.messages.append(Message.new(ctx, message.id, time, message.author.id, False, 0, message.content, []))
            async with self.config.guild(ctx.guild).jails() as jails:
                jails[str(jail.user)] = jailset.to_list()

    async def edit_message(self, ctx: commands.Context, jailset: JailSetABC, edited: discord.Message, time: int):
        jail = jailset.get_active_jail()
        if jail is not None:
            for message in jail.messages:
                await ctx.send("Checking message: " + json.dumps(message.to_dict()))
                if message.message_id == edited.id:
                    await ctx.send("Before: " + json.dumps(message.to_dict()))
                    message.edits.append(Edit.new(ctx, time, edited.content))
                    await ctx.send("After: " + json.dumps(message.to_dict()))
                else:
                    await ctx.send("MID Mismatch")
            async with self.config.guild(ctx.guild).jails() as jails:
                jails[str(jail.user)] = jailset.to_list()
        else:
            await ctx.send("Jail is none!")