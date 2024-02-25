from datetime import datetime

import discord
from discord import Guild
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.mod import is_mod_or_superior


class TagCog(commands.Cog):
    """Tag cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384002)

        default_guild_config = {
            "log": {  # TODO: The log booleans are not respected right now. Everything is logged.
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
        """Manage tags and aliases."""

        async def on_resolve(trigger: str, tag, alias, trigger_is_alias: bool):
            use = {"user": ctx.author.id, "time": int(datetime.utcnow().timestamp())}
            if "uses" not in tag:
                tag["uses"] = []
            tag["uses"].append(use)
            if trigger_is_alias:
                if "uses" not in alias:
                    alias["uses"] = []
                alias["uses"].append(use)
            await ctx.send(tag["content"])

        async def fail_resolve(trigger: str, trigger_is_alias):
            if trigger_is_alias:
                await ctx.send("That alias' tag doesn't exist!")
            else:
                await ctx.send("That's not a valid tag!")

        await self.resolve_trigger(ctx, tag, on_resolve, fail_resolve)

    @_tag.command(name="search")
    async def _search(self, ctx: commands.Context, query: str):
        """Fuzzy search for tags and aliases matching the provided query. (WIP)"""
        # TODO: Search for a matching tag or alias and return information about it to the user
        await ctx.send("Not yet implemented, please try again later. Sorry!")

    @_tag.command(name="create")
    async def _create(self, ctx: commands.Context, tag: str, *, content: str):
        """Create a new tag with the provided content (attachments excluded)."""
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
                    "content": content,
                    "transfers": [],
                    "uses": []
                }
                await ctx.send("Tag successfully created!")
            else:
                await ctx.send("That tag already exists!")

    @_tag.command(name="stats")
    async def _stats(self, ctx: commands.Context, member: discord.Member):
        """Provide general stats about the tag system, or if a user is provided, about that user. (WIP)"""
        await ctx.send("Stats reporting has not yet been implemented. Don't worry, we're tracking the stats though!")
        if not member:
            # TODO Return general stats
            pass
        else:
            # TODO Return stats about the user (we've collected many)
            pass
        pass

    @_tag.command(name="info")
    async def _info(self, ctx: commands.Context, tag: str):
        """Provide information about the specified tag/alias."""
        tag, aliases, is_tag, is_alias = await self.get_tag_or_alias(tag, ctx.guild)
        if not is_tag and not is_alias:
            await ctx.send("That's not a known tag or alias!")
        else:
            embed = self.make_tag_info_embed(tag, aliases)
            await ctx.send(embed=embed)

    @_tag.command(name="edit")
    async def _edit(self, ctx: commands.Context, tag: str, *, content: str):
        """Replace the tag content with the supplied content."""
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag in tags:
                to = tags[tag]
                if not to["owner"] == ctx.author.id and not await is_mod_or_superior(self.bot, ctx.author):
                    await ctx.send("Sorry, you're not the tag owner and you don't have permissions to do that.")
                else:
                    to["content"] = content
                    await ctx.send("Tag successfully updated!")
            else:
                await ctx.send("That's not a tag!")

    @_tag.command(name="delete")
    async def _delete(self, ctx: commands.Context, tag: str):
        """Delete the specified tag."""
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag in tags:
                to = tags[tag]
                if not to["owner"] == ctx.author.id and not await is_mod_or_superior(self.bot, ctx.author):
                    await ctx.send("Sorry, you're not the tag owner and you don't have permissions to do that.")
                else:
                    del tags[tag]
                    await ctx.send("Tag successfully deleted!")
            else:
                await ctx.send("That's not a tag!")

    @_tag.command(name="claim")
    async def _claim(self, ctx: commands.Context, tag: str):
        """Claim an abandoned tag (if the creator has left the guild)."""
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag in tags:
                to = tags[tag]
                if to["owner"] == ctx.author.id:
                    await ctx.send("You're already that tag owner!")
                else:
                    curr_owner = ctx.guild.get_member(int(to["owner"]))
                    if curr_owner is not None:
                        await ctx.send(f"That tag's owner is still in the guild! You can see if "
                                       f"{curr_owner.mention} wants to transfer it to you.")
                    else:
                        new_owner_id = ctx.author.id
                        if "transfers" not in to:
                            to["transfers"] = []
                        to["transfers"].append({"from": to["owner"], "reason": "Claim",
                                                "to": new_owner_id, "time": int(datetime.utcnow().timestamp())})
                        to["owner"] = new_owner_id
                        await ctx.send("Tag successfully claimed!")
            else:
                await ctx.send("Sorry, that isn't a valid tag so you can't claim it. Good news! You can create it!")

    @_tag.command(name="transfer")
    async def _transfer(self, ctx: commands.Context, tag: str, member: discord.Member):
        """Transfer ownership of the tag to the specified user."""
        is_mod = await is_mod_or_superior(self.bot, ctx.author)
        reason = "Transfer ("
        if is_mod:
            reason += f"Mod-initiated {ctx.author.mention})"
        else:
            reason += "Owner-initiated)"
        async with self.config.guild(ctx.guild).tags() as tags:
            if tag in tags:
                to = tags[tag]
                if not to["owner"] == ctx.author.id and not is_mod:
                    await ctx.send("Sorry, you're not the tag owner and you don't have permissions to do that.")
                else:
                    curr_owner = to["owner"]
                    new_owner = member.id
                    if "transfers" not in to:
                        to["transfers"] = []
                    to["transfers"].append({"from": curr_owner, "reason": reason,
                                            "to": new_owner, "time": int(datetime.utcnow().timestamp())})
                    to["owner"] = new_owner
                    await ctx.send("Tag successfully transferred!")
            else:
                await ctx.send("That's not a tag!")

    @_tag.group(name="alias")
    async def _alias(self, ctx: commands.Context):
        """Manage tag aliases."""
        pass

    @_alias.command("create")
    async def _alias_create(self, ctx: commands.Context, alias: str, tag: str):
        """Create an alias to the specified tag."""
        to, al, tag_proper, alias_proper = await self.get_tag_or_alias(alias, ctx.guild)
        if tag_proper:
            await ctx.send("That's already a tag!")
        elif alias_proper:
            await ctx.send("That's already an alias!")
        else:
            async with self.config.guild(ctx.guild).aliases() as aliases:
                aliases[alias] = {
                    "creator": ctx.author.id,
                    "created": int(datetime.utcnow().timestamp()),
                    "tag": tag,
                    "uses": []
                }
                await ctx.send("Alias successfully created!")

    @_alias.command("delete")
    async def _alias_delete(self, ctx: commands.Context, alias: str):
        """Delete the specified alias."""
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if alias in aliases:
                a = aliases[alias]
                if not a["creator"] == ctx.author.id and await is_mod_or_superior(self.bot, ctx.author):
                    await ctx.send("Sorry, you're not the alias creator and you don't have permissions to do that.")
                    return
                else:
                    del aliases[alias]
                    await ctx.send("Alias deleted successfully!")

    async def get_tag_or_alias(self, tag: str, guild: Guild) -> (object, [], bool, bool):
        """Searches for a tag or alias based on the value provided.

        If the provided query is a tag, it will return the tag and all aliases associated with it.

        If the provided query is an alias, it will return itself as an alias plus the resolved tag.

        If the provided query is a tag, the first returned boolean will be true.

        If the provided query is an alias, the second returned boolean will be true.

        All returned values are fully hydrated.

        If no aliases are found, a zero-length array is returned.

        """
        hydrated_tag = None  # A single tag to return
        hydrated_aliases = []  # All aliases for a tag
        tag_proper = False
        alias_proper = False
        tag_search = tag
        async with self.config.guild(guild).aliases() as aliases:
            if tag in aliases:
                hydrated_aliases = [aliases[tag]]  # Provided tag is only an alias
                alias_proper = True
                tag_search = aliases[tag]["tag"]
            else:
                for alias in aliases:
                    if aliases[alias]["tag"] == tag:
                        hydrated_aliases.append(aliases[alias])
        async with self.config.guild(guild).tags() as tags:
            if tag_search in tags:
                tag_proper = tag_search == tag
                hydrated_tag = tags[tag_search]
        return hydrated_tag, hydrated_aliases, tag_proper, alias_proper

    async def resolve_trigger(self, ctx: commands.Context, trigger: str, on_resolve, fail_resolve):
        search_tag = trigger
        alias = None
        trigger_is_alias = False
        async with self.config.guild(ctx.guild).aliases() as aliases:
            if search_tag in aliases:
                alias = aliases[search_tag]
                search_tag = alias["tag"]
                trigger_is_alias = True
            async with self.config.guild(ctx.guild).tags() as tags:
                if search_tag in tags:
                    tag = tags[search_tag]
                    if on_resolve is not None:
                        await on_resolve(trigger, tag, alias, trigger_is_alias)
                else:
                    if fail_resolve is not None:
                        await fail_resolve(trigger, trigger_is_alias)

    def make_tag_info_embed(self, tag, aliases) -> discord.Embed:
        """Construct the Tag information embed to be sent."""
        transfers = ""
        for xfer in tag['transfers']:
            transfers += xfer['from']
        alias_list = ""
        for alias in aliases.keys():
            alias_list += alias
        return (
            discord.Embed(
                colour=discord.Colour.blue(),
            )
            .add_field(name="Creator", value=f"<@{tag['creator']}>")
            .add_field(name="Owner", value=f"<@{tag['owner']}>")
            .add_field(name="Created", value=f"<t:{tag['created']}:F>")
            .add_field(name="Usage", value=len(tag['uses']))
            .add_field(name="Aliases", value=alias_list)
            .add_field(name="Prior Owners", value=transfers)
        )
