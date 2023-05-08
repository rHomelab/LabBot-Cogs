from datetime import datetime

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core import commands


class TagCog(commands.Cog):
    """Tag cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384002)

        default_guild_config = {
            "log": {
                "transfers": True,
                "uses": True
            },
            "tags": {
                "example": {
                    "creator": "128986274420752384",
                    "owner": "128986274420752384",
                    "created": int(datetime.utcnow().timestamp()),
                    "content": "This is an example tag!",
                    "transfers": [
                        {
                            "time": int(datetime.utcnow().timestamp()),
                            "from": "128986274420752384",
                            "to": "128986274420752384"
                        }
                    ],
                    "uses": [
                        {
                            "user": "128986274420752384",
                            "time": int(datetime.utcnow().timestamp())
                        }
                    ]
                }
            },
            "aliases": {
                "ex": {
                    "tag": "example",
                    "creator": "128986274420752384",
                    "created": int(datetime.utcnow().timestamp()),
                    "uses": [
                        {
                            "user": "128986274420752384",
                            "time": int(datetime.utcnow().timestamp())
                        }
                    ]
                }
            }
        }

        self.config.register_guild(**default_guild_config)

    @commands.guild_only()
    @commands.group(name="tag", pass_context=True, invoke_without_command=True)
    async def _tag(self, ctx: commands.Context, tag: str):

        async def fire_tag(t) -> bool:
            async with self.config.guild(ctx.guild).tags.get_attr(t) as to:
                if to is not None:
                    async with to.uses() as metrics:
                        metrics.append({"user": ctx.author.id, "time": int(datetime.utcnow().timestamp())})
                    await ctx.send(await to.content())
                    return True

        if not await fire_tag(tag):  # Fires the tag if it's a tag itself, otherwise continue and fire as an alias
            async with self.config.guild(ctx.guild).aliases.get_attr(tag) as alias:
                if alias is not None:
                    async with alias.uses() as uses:
                        uses.append({"user": ctx.author.id, "time": int(datetime.utcnow().timestamp())})
                    await fire_tag(await alias.tag())

    @_tag.command(name="search")
    async def _search(self, ctx: commands.Context, query: str):
        # TODO: Search for a matching tag or alias and return information about it to the user
        await ctx.send("Not yet implemented, please try again later. Sorry!")

    @_tag.command(name="create")
    async def _create(self, ctx: commands.Context, tag: str, content: str):
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if tag in aliases:
                await ctx.send("That tag already exists as an alias!")
                return
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag not in tags:
                tags[tag] = {
                    "creator": ctx.author.id,
                    "owner": ctx.author.id,
                    "created": int(datetime.utcnow().timestamp()),
                    content: content,
                    "transfers": [],
                    "uses": []
                }
            else:
                await ctx.send("Tag successfully created!")

    @_tag.command(name="stats")
    async def _stats(self, ctx: commands.Context, member: discord.Member):
        if not member:
            # TODO Return general stats
            pass
        else:
            # TODO Return stats about the user (we've collected many)
            pass
        pass

    @_tag.command(name="info")
    async def _info(self, ctx: commands.Context, tag: str):
        if not tag:
            # TODO Error
            pass
        else:
            # TODO return information about the tag
            pass

    @_tag.command(name="edit")
    async def _edit(self, ctx: commands.Context, tag: str, content: str):
        # TODO: Like in create, confirm the full sentence/content is passed as content, not just one word
        # TODO: Check if owner and edit the tag if so
        pass

    @_tag.command(name="delete")
    async def _delete(self, ctx: commands.Context, tag: str):
        # TODO: Check if owner/mod+ and delete if so
        pass

    @_tag.command(name="claim")
    async def _claim(self, ctx: commands.Context, tag: str):
        # TODO check if current tag owner is in the server. If not, set as new owner
        pass

    @_tag.command(name="transfer")
    async def _transfer(self, ctx: commands.Context, tag: str, member: discord.Member):
        # TODO: Check if owner or mod+ and set owner to member then make the relevant ownership transfer entry
        pass

    @_tag.group(name="alias")
    async def _alias(self, ctx: commands.Context, alias: str, tag: str):
        pass

    @_alias.command("create")
    async def _alias_create(self, ctx: commands.Context, alias: str, tag: str):
        # TODO See if the tag (or alias) exists and create the alias if not
        pass

    @_alias.command("delete")
    async def _alias_delete(self, ctx: commands.Context, alias: str):
        # TODO: Check if owner or mod+ and delete if so
        pass
