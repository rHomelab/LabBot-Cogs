from typing import List

import discord
from discord import CategoryChannel
from redbot.core import commands, Config

from jail.abstracts import EditABC, MessageABC, JailABC, JailConfigHelperABC


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
    def new(cls, ctx: commands.Context, datetime: int, author: int, deleted: bool, deleted_datetime: int, content: str,
            edits: List[EditABC]):
        return cls(
            datetime=datetime,
            author=author,
            deleted=deleted,
            deleted_datetime=deleted_datetime,
            content=content,
            edits=edits
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return Message.new(ctx, datetime=data['datetime'], author=data['author'], deleted=data['deleted'],
                           deleted_datetime=data['deleted_datetime'], content=data['content'],
                           edits=[Edit.from_storage(ctx, e) for e in data['edits']])

    def to_dict(self) -> dict:
        return {
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


class JailConfigHelper(JailConfigHelperABC):

    def __init__(self):
        self.config = Config.get_conf(self, identifier=1289862744207523842002, cog_name="JailCog")
        self.config.register_guild()

    async def set_category(self, ctx: commands.Context, category: CategoryChannel):
        await self.config.guild(ctx.guild).channels().category.set(category.id)

    async def get_category(self, ctx: commands.Context) -> CategoryChannel:
        channel = ctx.guild.get_channel(await self.config.guild(ctx.guild).channels().category())
        if channel is None:
            return None
        return channel

    async def create_jail(self, ctx: commands.Context, datetime: int, member: discord.Member) -> Jail:
        category = await self.get_category(ctx)
        if category is None:
            return None
        reason = f"Jail: {ctx.author.name} created a jail for: {member.name}"
        channel = await ctx.guild.create_text_channel(
            name=f"{member.name}'s Timeout",
            reason=reason,
            category=category,
            news=False,
            topic=f"{member.display_name} was bad and now we're here. DO NOT LEAVE! Leaving is evading and will "
                  f"result in an immediate ban.",
            nsfw=False,
        )
        role = await ctx.guild.create_role(
            name=f"Jail:{member.name}",
            mentionable=False,
            reason=reason,
            # TODO Permissions
        )
        async with self.config.guild(ctx.guild).jails() as jails:
            jail = Jail.new(ctx, datetime, channel.id, role.id, True, ctx.author.id, member.id, [], [])
            jails[member.id] = jail.to_dict()

        return jail

    async def save_user_roles(self, ctx: commands.Context, jail: Jail, member: discord.Member):
        jail.user_roles = [r.id for r in member.roles]
        async with self.config.guild(ctx.guild).jails() as jails:
            jails[jail.user] = jail.to_dict()

    async def restore_user_roles(self, ctx: commands.Context, jail: Jail, member: discord.Member):
        for rid in jail.user_roles:
            role = ctx.guild.get_role(rid)
            if role is not None:
                await member.add_roles(role, reason="Jail: Restore Roles")

    async def jail_user(self, ctx: commands.Context, jail: Jail, member: discord.Member):
        await self.save_user_roles(ctx, jail, member)
        reason = "Jail: Timeout"
        for r in member.roles:
            await member.remove_roles(r, reason=reason)

        role = ctx.guild.get_role(jail.role_id)
        if role is not None:
            await member.add_roles(role, reason=reason)

    async def free_user(self, ctx: commands.Context, jail: Jail, member: discord.Member):
        await self.restore_user_roles(ctx, jail, member)

        role = ctx.guild.get_role(jail.role_id)
        if role is not None:
            await member.remove_roles(role, reason="Jail: Free User")

    async def get_jail_by_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> Jail:
        async with self.config.guild(ctx.guild).jails() as jails:
            for jid in jails.keys():
                jail = Jail.from_storage(ctx, jails[jid])
                if channel.id == jail.channel_id:
                    return jail
        return None
