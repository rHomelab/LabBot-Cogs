from datetime import datetime
from typing import List, Optional

import discord
from redbot.core import Config, commands

from tags.abstracts import AliasABC, TagABC, TagConfigHelperABC, TransferABC, UseABC


class Transfer(TransferABC):
    @classmethod
    def new(cls, ctx: commands.Context, prior: int, reason: str, to: int, time: int):
        return cls(prior=prior, reason=reason, to=to, time=time)

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(prior=data["prior"], reason=data["reason"], to=data["to"], time=data["time"])

    def to_dict(self) -> dict:
        return {"prior": self.prior, "reason": self.reason, "to": self.to, "time": self.time}


class Use(UseABC):
    @classmethod
    def new(cls, ctx: commands.Context, user: int, time: int):
        return cls(user=user, time=time)

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(user=data["user"], time=data["time"])

    def to_dict(self) -> dict:
        return {"user": self.user, "time": self.time}


class Alias(AliasABC):
    @classmethod
    def new(cls, ctx: commands.Context, alias: str, creator: int, created: int, tag: str, uses: List[UseABC]):
        return cls(alias=alias, creator=creator, created=created, tag=tag, uses=uses)

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(alias=data["alias"], creator=data["creator"], created=data["created"], tag=data["tag"], uses=data["uses"])

    def to_dict(self) -> dict:
        return {"alias": self.alias, "creator": self.creator, "created": self.created, "tag": self.tag, "uses": self.uses}


class Tag(TagABC):
    @classmethod
    def new(cls, ctx: commands.Context, creator: int, owner: int, created: int, tag: str, content: str):
        return cls(tag=tag, creator=creator, owner=owner, created=created, content=content, transfers=[], uses=[])

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(
            tag=data["tag"],
            creator=data["creator"],
            owner=data["owner"],
            created=data["created"],
            content=data["content"],
            transfers=data["transfers"],
            uses=["uses"],
        )

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "creator": self.creator,
            "owner": self.owner,
            "created": self.created,
            "content": self.content,
            "transfers": [],
            "uses": [],
        }


class TagConfigHelper(TagConfigHelperABC):
    def __init__(self):
        self.config = Config.get_conf(None, identifier=128986274420752384002, cog_name="TagCog")
        self.config.register_guild(log={}, tags={}, aliases={})

    async def log_uses(self, ctx: commands.Context) -> bool:
        return self.config.guild(ctx.guild).log().uses()

    async def set_log_uses(self, ctx: commands.Context, log: bool):
        return self.config.guild(ctx.guild).log().uses.set(log)

    async def log_transfers(self, ctx: commands.Context) -> bool:
        return self.config.guild(ctx.guild).log().transfers()

    async def set_log_transfers(self, ctx: commands.Context, log: bool):
        return self.config.guild(ctx.guild).log().uses.transfers(log)

    async def create_tag(self, ctx: commands.Context, trigger: str, content: str) -> Tag:
        time = int(datetime.utcnow().timestamp())
        tag = Tag.new(ctx, ctx.author.id, ctx.author.id, time, trigger, content)
        async with self.config.guild(ctx.guild).tags() as tags:
            tags[trigger] = tag.to_dict()
        return tag

    async def edit_tag(self, ctx: commands.Context, trigger: str, content: str) -> Tag:
        tag = await self.get_tag(ctx, trigger)
        if tag is not None:
            tag.content = content
            async with self.config.guild(ctx.guild).tags() as tags:
                tags[trigger] = tag.to_dict()
        return tag

    async def transfer_tag(self, ctx: commands.Context, trigger: str, to: int, reason: str, time: int):
        tag = await self.get_tag(ctx, trigger)
        if tag is not None:
            transfers = tag.transfers
            transfers.append(Transfer.new(ctx, tag.owner, reason, to, time))
            tag.transfers = transfers
            tag.owner = to
            async with self.config.guild(ctx.guild).tags() as tags:
                tags[trigger] = tag.to_dict()

    async def delete_tag(self, ctx: commands.Context, tag: str):
        async with self.config.guild(ctx.guild).tags() as tags:
            del tags[tag]

    async def get_tag(self, ctx: commands.Context, trigger: str) -> Tag:
        tag = None
        async with self.config.guild(ctx.guild).tags() as tags:
            if trigger in tags:
                tag = Tag.from_storage(ctx, tags[trigger])
        return tag

    async def get_tag_by_alias(self, ctx: commands.Context, alias: Alias) -> Tag:
        tag = None
        if alias is not None and alias.tag is not None:
            search = alias.tag
            async with self.config.guild(ctx.guild).tags() as tags:
                if search in tags:
                    tag = Tag.from_storage(ctx, tags[search])
        return tag

    async def get_tags(self, ctx: commands.Context, owner: Optional[discord.User]) -> List[TagABC]:
        tag_list = []
        async with self.config.guild(ctx.guild).tags() as tags:
            for tag_key in tags.keys():
                tag = Tag.from_storage(ctx, tags[tag_key])
                if owner is not None:
                    if not tag.owner == owner.id:
                        continue
                tag_list.append(tag)
        return tag_list

    async def get_tags_by_owner(self, ctx: commands.Context, owner_id: int) -> List[Tag]:
        filtered_tags = []
        async with self.config.guild(ctx.guild).tags() as tags:
            for tag in tags:
                if tag.owner == owner_id:
                    filtered_tags.append(Tag.from_storage(ctx, tag))
        return filtered_tags

    async def get_tag_or_alias(self, ctx: commands.Context, trigger: str) -> (Tag, Alias):
        return await self.get_tag(ctx, trigger), await self.get_alias(ctx, trigger)

    async def add_tag_use(self, ctx: commands.Context, tag: Tag, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag.tag in tags:
                tags[tag.tag]["uses"].append(use.to_dict())

    async def create_alias(self, ctx: commands.Context, alias: str, tag: str, creator: int, created: int):
        new_alias = Alias.new(ctx, alias, creator, created, tag, [])
        async with self.config.guild(ctx.guild).aliases() as aliases:
            aliases[alias] = new_alias.to_dict()

    async def delete_alias(self, ctx: commands.Context, alias: str):
        async with self.config.guild(ctx.guild).aliases() as aliases:
            del aliases[alias]

    async def get_alias(self, ctx: commands.Context, trigger: str) -> Alias:
        alias = None
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if trigger in aliases:
                alias = Alias.from_storage(ctx, aliases[trigger])
        return alias

    async def get_aliases(self, ctx: commands.Context, creator: Optional[discord.User]) -> List[Alias]:
        alias_list = []
        async with self.config.guild(ctx.guild).aliases() as aliases:
            for alias_key in aliases.keys():
                alias = Alias.from_storage(ctx, aliases[alias_key])
                if creator is not None:
                    if not alias.creator == creator.id:
                        continue
                alias_list.append(alias)
        return alias_list

    async def get_aliases_by_tag(self, ctx: commands.Context, tag: Tag) -> List[Alias]:
        alias_list = []
        async with self.config.guild(ctx.guild).aliases() as aliases:
            for alias_key in aliases.keys():
                alias = Alias.from_storage(ctx, aliases[alias_key])
                if alias.tag == tag.tag:
                    alias_list.append(alias)
        return alias_list

    async def get_aliases_by_owner(self, ctx: commands.Context, owner_id: int) -> List[Alias]:
        filtered_aliases = []
        async with self.config.guild(ctx.guild).aliases() as aliases:
            for alias_key in aliases.keys():
                alias = Alias.from_storage(ctx, aliases[alias_key])
                if alias.creator == owner_id:
                    filtered_aliases.append(alias)
        return filtered_aliases

    async def add_alias_use(self, ctx: commands.Context, alias: Alias, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if alias.alias in aliases:
                aliases[alias.alias]["uses"].append(use.to_dict())
        tag = await self.get_tag_by_alias(ctx, alias)
        if tag is not None:
            await self.add_tag_use(ctx, tag, user, time)
