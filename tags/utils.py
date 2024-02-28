from datetime import datetime
from typing import List

from redbot.core import Config
from redbot.core.commands import commands

from tags.abstracts import TagConfigHelperABC, TagABC, AliasABC, UseABC, TransferABC


class Transfer(TransferABC):
    @classmethod
    def new(cls, ctx: commands.Context, prior: int, reason: str, to: int, time: int):
        return cls(
            prior=prior,
            reason=reason,
            to=to,
            time=time
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(
            prior=data['prior'],
            reason=data['reason'],
            to=data['to'],
            time=data['time']
        )

    def to_dict(self) -> dict:
        return {
            "prior": self.prior,
            "reason": self.reason,
            "to": self.to,
            "time": self.time
        }


class Use(UseABC):

    @classmethod
    def new(cls, ctx: commands.Context, user: int, time: int):
        return cls(
            user=user,
            time=time
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(
            user=data['user'],
            time=data['time']
        )

    def to_dict(self) -> dict:
        return {
            "user": self.user,
            "time": self.time
        }


class Alias(AliasABC):
    @classmethod
    def new(cls, ctx: commands.Context, alias: str, creator: int, created: int, tag: str, uses: List[UseABC]):
        return cls(
            alias=alias,
            creator=creator,
            created=created,
            tag=tag,
            uses=uses
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(
            alias=data['alias'],
            creator=data['creator'],
            created=data['created'],
            tag=data['tag'],
            uses=data['uses']
        )

    def to_dict(self) -> dict:
        return {
            "alias": self.alias,
            "creator": self.creator,
            "created": self.created,
            "tag": self.tag,
            "uses": self.uses
        }


class Tag(TagABC):
    @classmethod
    def new(cls, ctx: commands.Context, creator: int, owner: int, created: int, tag: str, content: str):
        return cls(
            creator=creator,
            owner=owner,
            created=created,
            tag=tag,
            content=content
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        return cls(
            creator=data['creator'],
            owner=data['owner'],
            created=data['created'],
            tag=data['tag'],
            content=data['content']
        )

    def to_dict(self) -> dict:
        return {
            "creator": self.creator,
            "owner": self.owner,
            "created": self.created,
            "tag": self.tag,
            "content": self.content
        }


class TagConfigHelper(TagConfigHelperABC):

    def __init__(self):
        self.config = Config.get_conf(None, identifier=128986274420752384002, cog_name="TagsCog")
        self.config.register_guild()

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

    async def get_tags_by_owner(self, ctx: commands.Context, owner_id: int) -> List[Tag]:
        filtered_tags = []
        async with self.config.guild(ctx.guild).tags() as tags:
            for tag in tags:
                if tag.owner == owner_id:
                    filtered_tags.append(Tag.from_storage(ctx, tag))
        return filtered_tags

    async def get_tag_or_alias(self, ctx: commands.Context, trigger: str) -> (Tag, Alias):
        return self.get_tag(ctx, trigger), self.get_alias(ctx, trigger)

    async def add_tag_use(self, ctx: commands.Context, tag: Tag, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag.tag in tags:
                tags[tag].uses().append(use)

    async def get_alias(self, ctx: commands.Context, alias: str) -> Alias:
        pass

    async def get_aliases_by_tag(self, ctx: commands.Context, tag: Tag) -> List[Alias]:
        pass

    async def get_aliases_by_owner(self, ctx: commands.Context, owner_id: int) -> List[Alias]:
        filtered_aliases = []
        async with self.config.guild(ctx.guild).aliases() as aliases:
            for alias in aliases:
                if alias.owner == owner_id:
                    filtered_aliases.append(Alias.from_storage(ctx, aliases))
        return filtered_aliases

    async def add_alias_use(self, ctx: commands.Context, alias: Alias, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if alias.alias in aliases:
                aliases[alias].uses().append(use)
        tag = await self.get_tag_by_alias(ctx, alias)
        if tag is not None:
            await self.add_tag_use(ctx, tag, user, time)
