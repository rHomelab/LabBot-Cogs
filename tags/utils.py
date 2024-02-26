from datetime import datetime
from typing import List

from redbot.core import Config
from redbot.core.commands import commands

from tags.abstracts import TagConfigHelperABC, TagABC, AliasABC, UseABC


class Use(UseABC):

    @classmethod
    def new(cls, ctx: commands.Context, user: int, time: int):
        return cls(
            user=user,
            time=time
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        pass

    def to_dict(self) -> dict:
        pass


class TagConfigHelper(TagConfigHelperABC):

    # TODO TagABC, UseABC, etc. should not be the ABC thing (i.e. Tag.new(...))

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

    async def create_tag(self, ctx: commands.Context, trigger: str, content: str) -> TagABC:
        time = int(datetime.utcnow().timestamp())
        tag = TagABC.new(ctx, ctx.author.id, ctx.author.id, time, trigger, content)
        async with self.config.guild(ctx.guild).tags() as tags:
            tags[trigger] = tag.to_dict()
        return tag

    async def get_tag(self, ctx: commands.Context, trigger: str) -> TagABC:
        tag = None
        async with self.config.guild(ctx.guild).tags() as tags:
            if trigger in tags:
                tag = TagABC.from_storage(ctx, tags[trigger])
        return tag

    async def get_tag_by_alias(self, ctx: commands.Context, alias: AliasABC) -> TagABC:
        tag = None
        if alias is not None and alias.tag is not None:
            search = alias.tag
            async with self.config.guild(ctx.guild).tags() as tags:
                if search in tags:
                    tag = TagABC.from_storage(ctx, tags[search])
        return tag

    async def get_tags_by_owner(self, ctx: commands.Context, owner_id: int) -> List[TagABC]:
        filtered_tags = []
        async with self.config.guild(ctx.guild).tags() as tags:
            for tag in tags:
                if tag.owner == owner_id:
                    filtered_tags.append(TagABC.from_storage(ctx, tag))
        return filtered_tags

    async def get_tag_or_alias(self, ctx: commands.Context, trigger: str) -> (TagABC, AliasABC):
        return self.get_tag(ctx, trigger), self.get_alias(ctx, trigger)

    async def add_tag_use(self, ctx: commands.Context, tag: TagABC, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag.tag in tags:
                tags[tag].uses().append(use)

    async def get_alias(self, ctx: commands.Context, alias: str) -> AliasABC:
        pass

    async def get_aliases_by_tag(self, ctx: commands.Context, tag: TagABC) -> List[AliasABC]:
        pass

    async def get_aliases_by_owner(self, ctx: commands.Context, owner_id: int) -> List[AliasABC]:
        filtered_aliases = []
        async with self.config.guild(ctx.guild).aliases() as aliases:
            for alias in aliases:
                if alias.owner == owner_id:
                    filtered_aliases.append(TagABC.from_storage(ctx, aliases))
        return filtered_aliases

    async def add_alias_use(self, ctx: commands.Context, alias: AliasABC, user: int, time: int):
        use = Use.new(ctx, user, time)
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if alias.alias in aliases:
                aliases[alias].uses().append(use)
        tag = await self.get_tag_by_alias(ctx, alias)
        if tag is not None:
            await self.add_tag_use(ctx, tag, user, time)
