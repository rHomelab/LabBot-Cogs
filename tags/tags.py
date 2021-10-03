import math
import random
import time
from collections import Counter
from typing import List, Optional

import discord
import Levenshtein as lev
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page
from redbot.core.utils.mod import is_mod_or_superior

from .converters import LoggingEventName, TagConverter, TagNameConverter
from .exceptions import CanNotManageTag, TagNotFound
from .logging_configuration import LoggingConfiguration

MENU_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


async def can_create_tags(ctx: commands.Context) -> bool:
    """
    Command predicate.
    Checks that the author is not on the blocked members list.
    """
    blocked_members = await ctx.cog.config.guild(ctx.guild).blocked_members()
    return not bool([m for m in blocked_members if m["id"] == ctx.author.id]) or await is_mod_or_superior(ctx.bot, ctx.author)


class TagsCog(commands.Cog):
    config: Config

    def __init__(self):
        self.config = Config.get_conf(self, identifier=377212919068229633)

        default_guild_config = {
            "aliases": [],  # [{source: str, target: str (tag.id)}]
            "tags": [],  # [{id: str, name: str, content: str, author: {id: int, username: str (user.name + '#' + user.discriminator)}}]
            "usage": [],  # [{tag_id: str (tag.id), user_id: int (user.id)}]
            "blocked_members": [],  # [{id: int, username: str (user.name + '#' + user.discriminator)}]
            "logging_channel": None,  # int (channel.id)
            "logging_config": LoggingConfiguration.all().to_int(),  # int
            "logging_enabled": True,  # False
        }

        self.config.register_guild(**default_guild_config)

    # Events

    @commands.Cog.listener()
    async def on_tag_create(self, ctx: commands.Context, tag: dict):
        """Logs tag creations to a channel"""
        channel = await self.can_log(ctx, "on_tag_create")
        if not channel:
            return

        log_embed = (
            discord.Embed(title="Tag created", description=tag["content"], colour=await ctx.embed_colour())
            .add_field(name="Author", value=ctx.author.mention)
            .add_field(name="Tag ID", value=tag["id"])
        )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_delete(self, ctx: commands.Context, tag: dict, aliases: List[str]):
        """Logs tag deletions to a channel"""
        channel = await self.can_log(ctx, "on_tag_delete")
        if not channel:
            return

        log_embed = (
            discord.Embed(title="Tag deleted", description=tag["content"], colour=discord.Colour.red())
            .add_field(name="Name", value=tag["name"])
            .add_field(name="Aliases", value="\n".join(aliases) or None)
            .add_field(name="Deleted by", value=ctx.author.mention)
        )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_transfer(self, ctx: commands.Context, old_owner: dict, new_owner: discord.Member):
        """Logs tag ownership transfer to a channel"""
        channel = await self.can_log(ctx, "on_tag_transfer")
        if not channel:
            return

        if new_owner == ctx.author:
            log_embed = (
                discord.Embed(title="Tag claimed", colour=await ctx.embed_colour())
                .add_field(name="Previous owner", value=f"""{old_owner["username"]}\n<@{old_owner["id"]}>""")
                .add_field(name="Claimed by", value=new_owner.mention)
            )
        else:
            log_embed = (
                discord.Embed(title="Tag ownership transferred", colour=await ctx.embed_colour())
                .add_field(name="Previous owner", value=f"""{old_owner["username"]}\n<@{old_owner["id"]}>""")
                .add_field(name="New owner", value=new_owner.mention)
                .add_field(name="Transferred by", value=ctx.author.mention)
            )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_edit(self, ctx: commands.Context, tag: dict, old_content):
        """Logs tag edits to a channel"""
        channel = await self.can_log(ctx, "on_tag_edit")
        if not channel:
            return

        def shorten_to(input_str: str, length: int) -> str:
            return f"{input_str[:length - 3]}..." if len(input_str) > length else input_str[:length]

        log_embed = discord.Embed(
            title="Tag edited",
            description=f"""
            **Before**
            {shorten_to(old_content, 2037)}
            **After**
            {shorten_to(tag["content"], 2037)}
            """,
            colour=await ctx.embed_colour(),
        )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_rename(self, ctx: commands.Context, old_name: str, new_name: str):
        """Logs tag rename events to a channel"""
        channel = await self.can_log(ctx, "on_tag_rename")
        if not channel:
            return

        log_embed = (
            discord.Embed(title="Tag renamed", colour=await ctx.embed_colour())
            .add_field(name="Before", value=old_name)
            .add_field(name="After", value=new_name)
        )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_alias_create(self, ctx: commands.Context, alias_name: str, tag_name: str):
        """Logs tag alias creations to a channel"""
        channel = await self.can_log(ctx, "on_tag_alias_create")
        if not channel:
            return

        log_embed = (
            discord.Embed(title="Tag alias created", colour=await ctx.embed_colour())
            .add_field(name="Alias", value=alias_name)
            .add_field(name="Tag", value=tag_name)
        )
        await channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_tag_alias_delete(self, ctx: commands.Context, alias_name: str, tag_name: str):
        """Logs tag alias deletions to a channel"""
        channel = await self.can_log(ctx, "on_tag_alias_delete")
        if not channel:
            return

        log_embed = (
            discord.Embed(title="Tag alias removed", colour=await ctx.embed_colour())
            .add_field(name="Alias", value=alias_name)
            .add_field(name="Tag", values=tag_name)
        )
        await channel.send(embed=log_embed)

    # Command groups

    @commands.guild_only()
    @commands.group(name="tag", invoke_without_command=True)
    async def tag_group(self, ctx: commands.Context, *, tag: TagConverter):
        """
        Allows you to tag text for later retrieval.
        If a subcommand is not called, then this will search the tag database
        for the tag requested.
        """
        await ctx.send(tag["content"])

        # update the usage
        await self.update_tag_usage(ctx, tag)

    @commands.guild_only()
    @commands.group(name="tags", invoke_without_subcommand=True)
    async def tags_group(self, ctx: commands.Context):
        """View all the tags in this server"""
        tags = await self.config.guild(ctx.guild).tags()
        pages = [
            discord.Embed(
                description="\n".join(
                    f"**{tag_n}.** {tag_name}"
                    for tag_n, tag_name in enumerate(tags[page_start : page_start + 20], start=page_start)
                ),
                colour=await ctx.embed_colour(),
            ).set_footer(text=f"{page_n} of {math.ceil(len(tags) / 20)}")
            for page_n, page_start in enumerate(range(0, len(tags), 20), start=1)
        ]
        await menu(ctx, pages, controls=MENU_CONTROLS, timeout=180.0)

    @tag_group.group(name="alias")
    async def tag_alias(self, ctx: commands.Context):
        pass

    # Commands

    @commands.check(can_create_tags)
    @tag_group.command(name="create", aliases=["add", "new"])
    async def tag_create(self, ctx: commands.Command, tag_name: TagNameConverter, *, tag_content: str):
        """Creates a tag for later reference"""
        # Check if tag already exists
        try:
            await self.get_tag(ctx.guild, tag_name)
            return await ctx.send("A tag already exists with this name.")
        except TagNotFound:
            # Tag does not already exist
            pass

        async with self.config.guild(ctx.guild).tags() as tags:
            tag = {
                "id": self.generate_tag_id(ctx),
                "name": tag_name,
                "content": tag_content,
                "author": {"id": ctx.author.id, "username": str(ctx.author)},
            }

            tags.append(tag)

        await ctx.send("Tag created.")
        ctx.bot.dispatch("tag_create", ctx, tag)

    @tag_group.command(name="stats")
    async def tag_stats(self, ctx: commands.Context, stats_target: discord.Member = None):
        """View the stats for all tags in the server, or all the tags for a specific member"""
        tags = await self.config.guild(ctx.guild).tags()
        usage = await self.config.guild(ctx.guild).usage()

        def get_tag_by_id(tag_id: str) -> dict:
            # Tags are guaranteed to exist if they are referenced in usage
            return [t for t in tags if t["id"] == tag_id][0]

        def get_tag_usage_count(tag_id: str) -> int:
            return len([u for u in usage if u["tag_id"] == tag_id])

        # Guild tag stats
        if not stats_target:

            top_tags = "\n".join(
                f"""**{i}.** {get_tag_by_id(elem[0])["name"]} ({elem[1]} uses)"""
                for i, elem in enumerate(
                    sorted(Counter([u["tag_id"] for u in usage]).items(), key=lambda i: i[1], reverse=True)[:3], start=1
                )
            )
            top_users = "\n".join(
                f"""**{i}.** <@{elem[0]}> ({elem[1]} uses)"""
                for i, elem in enumerate(
                    sorted(Counter([u["user_id"] for u in usage]).items(), key=lambda i: i[1], reverse=True)[:3], start=1
                )
            )
            top_creators = "\n".join(
                f"""**{i}.** <@{elem[0]}> ({elem[1]} tags)"""
                for i, elem in enumerate(
                    sorted(Counter([t["author"]["id"] for t in tags]).items(), key=lambda i: i[1], reverse=True)[:3],
                    start=1,
                )
            )

            embed = (
                discord.Embed(
                    title="Tag stats", description=f"{len(tags)} tags, {len(usage)} tag uses", colour=await ctx.embed_colour()
                )
                .add_field(name="Top tags", value=top_tags or "None", inline=False)
                .add_field(name="Top users", value=top_users or "None", inline=False)
                .add_field(name="Top creators", value=top_creators or "None", inline=False)
            )
            return await ctx.send(embed=embed)

        # Member tag stats
        elif isinstance(stats_target, discord.Member):
            owned_tags: List[dict] = [t for t in tags if t["author"]["id"] == stats_target.id]
            owned_tag_uses: int = sum([get_tag_usage_count(t) for t in owned_tags])
            tag_cmd_uses: int = len([u for u in usage if u["user_id"] == stats_target.id])
            top_owned_tags = "\n".join(
                f"""**{i}.** {get_tag_by_id(elem[0])["name"]} ({elem[1]} uses)"""
                for i, elem in enumerate(
                    sorted(
                        Counter([u["tag_id"] for u in usage if u["tag_id"] in [t["id"] for t in owned_tags]]).items(),
                        key=lambda i: i[1],
                        reverse=True,
                    )[:3],
                    start=1,
                )
            )

            embed = (
                discord.Embed(colour=await ctx.embed_colour())
                .set_author(name=f"{stats_target.name}#{stats_target.discriminator}", icon_url=stats_target.avatar_url)
                .add_field(name="Owned tags", value=owned_tags)
                .add_field(name="Owned tag uses", value=owned_tag_uses)
                .add_field(name="Tag command uses", value=tag_cmd_uses)
                .add_field(name="Top owned tags", value=top_owned_tags)
            )
            return await ctx.send(embed=embed)

    @tag_group.command(name="info")
    async def tag_info(self, ctx: commands.Context, tag: TagConverter):
        """View info about a tag"""
        usage = await self.config.guild(ctx.guild).usage()
        aliases = await self.config.guild(ctx.guild).aliases()
        tag_aliases = "\n".join(a["source"] for a in aliases if a["target"] == tag["id"])

        embed = (
            discord.Embed(title=tag["name"], colour=await ctx.embed_colour())
            .add_field(name="Owner", value=f"""<@{tag["author"]["id"]}>""")
            .add_field(name="Uses", value=len([u for u in usage if u["tag_id"] == tag["id"]]))
            .add_field(name="Rank", value=await self.get_tag_rank(ctx.guild, tag["id"]))
            .add_field(name="Aliases", value=tag_aliases or None)
        )
        await ctx.send(embed)

    @commands.check(can_create_tags)
    @tag_alias.command(name="create", aliases=["add"])
    async def tag_alias_create(self, ctx: commands.Context, alias: TagNameConverter, *, tag: TagConverter):
        # Check that alias name isn't already taken by another tag
        try:
            await self.get_tag(ctx.guild, alias)
            return await ctx.send("This name is already taken.")
        except TagNotFound:
            # Name not already taken
            pass

        async with self.config.guild(ctx.guild).aliases() as aliases:
            if [a for a in aliases if a["source"] == alias]:
                return await ctx.send("This name is already taken.")

            aliases.append({"source": alias, "target": tag["id"]})

        await ctx.send(f"""Alias `{alias}` -> `{tag["name"]}` added.""")
        ctx.bot.dispatch("tag_alias_create", ctx, tag)

    @commands.check(can_create_tags)
    @tag_alias.command(name="delete", aliases=["remove"])
    async def tag_alias_delete(self, ctx: commands.Context, alias: TagNameConverter):
        """Delete an alias for a tag"""
        async with self.config.guild(ctx.guild).aliases() as aliases:
            # Check that the alias exists
            try:
                (match,) = [a for a in aliases if a["source"] == alias]
            except ValueError:
                return await ctx.send("This alias does not exist.")

            tag = await self.get_tag(ctx.guild, match["target"], check_aliases=False)
            # Check that the user can manage this tag
            if not (tag["author"]["id"] == ctx.author.id or await is_mod_or_superior(ctx.bot, ctx.author)):
                return await ctx.send("You do not have permission to manage this tag.")

            # Remove the alias
            aliases.remove(match)
            await ctx.send("This alias has been deleted.")

    @tag_group.command(name="edit")
    async def tag_edit(self, ctx: commands.Context, tag: TagConverter, new_content: str):
        """
        Edit a tag you own.
        Make sure you save a copy of the old content, because you can't undo your edits.
        """
        if tag["author"]["id"] != ctx.author.id:
            return await ctx.send(CanNotManageTag())

        async with self.config.guild(ctx.guild).tags() as tags:
            (tag_match,) = [t for t in tags if t["id"] == tag["id"]]
            old_content = tag_match["content"]
            tag_match.update({"content": new_content})
            await ctx.send("Tag content updated.")
            ctx.bot.dispatch("tag_edit", ctx, tag_match, old_content)

    @tag_group.command(name="delete", aliases=["remove"])
    async def tag_delete(self, ctx: commands.Context, tag: TagConverter):
        """
        Deletes a tag, along with all aliases pointing to said tag.
        """
        # Only the tag owner or guild moderators can delete a tag
        can_manage_tag = (tag["author"]["id"] == ctx.author.id) or (await is_mod_or_superior(ctx.bot, ctx.author))
        if not can_manage_tag:
            return await ctx.send(CanNotManageTag())

        # Remove tag from tags list
        async with self.config.guild(ctx.guild).tags() as tags:
            tags = [t for t in tags if t["id"] != tag["id"]]
        # Remove all usage occurrences related to the tag
        async with self.config.guild(ctx.guild).usage() as usage:
            usage = [u for u in usage if u["tag_id"] != tag["id"]]
        # Remove all aliases pointing to the tag
        async with self.config.guild(ctx.guild).aliases() as aliases:
            aliases_to_be_deleted = [a["source"] for a in aliases if a["target"] == tag["id"]]
            aliases = [a for a in aliases if a["source"] in aliases_to_be_deleted]
        await ctx.send("Tag deleted.")
        ctx.bot.dispatch("tag_delete", ctx, tag, aliases_to_be_deleted)

    @tag_group.command(name="search")
    async def tag_search(self, ctx: commands.Context, *, search_term: TagNameConverter):
        """Search for a tag by name."""

        def remove_whitespace(input_string: str) -> str:
            return "".join(input_string.split())

        def search_match(search_term: str, arg: str) -> bool:
            arg = remove_whitespace(arg)
            return (search_term in arg) or (lev.distance(search_term, arg) <= len(search_term) / 5)

        tags = await self.config.guild(ctx.guild).tags()
        modified_term = remove_whitespace(search_term)
        matched_tags = [t["name"] for t in tags if search_match(modified_term, t["name"])]
        if not matched_tags:
            return await ctx.send("No tags found matching this search.")

        pages = list(pagify("\n".join(f"**{i}.** {elem}" for i, elem in enumerate(matched_tags, start=1)), shorten_by=58))
        embeds = [
            (
                discord.Embed(title=f"Tag search results", description=page, colour=await ctx.embed_colour()).set_footer(
                    text=f"{i} of {len(pages)}"
                )
            )
            for i, page in enumerate(pages, start=1)
        ]
        if len(embeds) == 1:
            await ctx.send(embed=embeds)
        elif len(embeds) > 1:
            await menu(ctx, pages=embeds, controls=MENU_CONTROLS)

    @commands.check(can_create_tags)
    @tag_group.command(name="claim")
    async def tag_claim(self, ctx: commands.Context, tag: TagConverter):
        """Claim a tag if the owner of the tag has left the server"""
        try:
            ctx.guild.fetch_member(tag["author"]["id"])
        except discord.HTTPException:
            # Member not found
            pass
        else:
            # Member is in guild
            return await ctx.send("You can only claim a tag if the tag owner has left the server.")

        async with self.config.guild(ctx.guild).tags() as tags:
            (tag_match,) = [t for t in tags if t["id"] == tag["id"]]
            old_owner = tag_match["author"].copy()
            tag_match.update({"author": {"id": ctx.author.id, "username": str(ctx.author)}})
            await ctx.send("Tag claimed.")
            ctx.bot.dispatch("tag_transfer", ctx, old_owner, ctx.author)

    @tag_group.command(name="transfer")
    async def tag_transfer(self, ctx: commands.Context, tag: TagConverter, new_owner: discord.Member):
        """Transfer ownership of a tag to someone else."""
        can_manage_tag = (tag["author"]["id"] == ctx.author.id) or (await is_mod_or_superior(ctx.bot, ctx.author))
        if not can_manage_tag:
            return await ctx.send(CanNotManageTag())

        async with self.config.guild(ctx.guild).tags() as tags:
            (tag_match,) = [t for t in tags if t["id"] == tag["id"]]
            old_owner = tag_match["author"].copy()
            tag_match.update({"author": {"id": new_owner.id, "username": str(new_owner)}})
            await ctx.send(f"Tag transferred to {new_owner.mention}", allowed_mentions=discord.AllowedMentions.none)
            ctx.bot.dispatch("tag_transfer", ctx, old_owner, new_owner)

    @checks.mod()
    @tags_group.command(name="block")
    async def tags_block(self, ctx: commands.Context, member: discord.Member):
        """Block a member from creating tags"""
        async with self.config.guild(ctx.guild).blocked_members() as blocked_members:
            match = [m for m in blocked_members if m["id"] == member.id]
            if match:
                return await ctx.send("This member is already blocked from creating tags")

            blocked_members.append({"id": member.id, "username": f"{member.name}#{member.discriminator}"})

    @checks.mod()
    @tags_group.command(name="unblock")
    async def tags_unblock(self, ctx: commands.Context, member: discord.Member):
        """Allows a (currently blocked) member to create tags"""
        async with self.config.guild(ctx.guild).blocked_members() as blocked_members:
            try:
                (match,) = [m for m in blocked_members if m["id"] == member.id]
                blocked_members.remove(match)
                await ctx.send("Member now allowed to create tags.")
            except ValueError:
                # Member not on block list
                await ctx.send("Member not on block list.")

    @checks.mod()
    @tags_group.command(name="blocked")
    async def tags_blocked(self, ctx: commands.Context):
        """View all members blocked from creating tags"""
        blocked_members = [
            f"""{getattr(ctx.guild.get_member(m["id"]), "mention") or m["username"]} ({m["id"]})"""
            for m in await self.config.guild(ctx.guild).blocked_members()
        ]
        if not blocked_members:
            return await ctx.send("No members are currently blocked from creating tags.")

        pages = list(pagify("\n\n".join(blocked_members)))
        embeds = [
            (
                discord.Embed(
                    title=f"Blocked members - {len(blocked_members)}", description=page, colour=await ctx.embed_colour()
                ).set_footer(text=f"{i + 1} of {len(pages)}")
            )
            for i, page in enumerate(pages)
        ]
        await menu(ctx, embeds, controls=MENU_CONTROLS)

    @checks.mod()
    @tags_group.command(name="logchannel")
    async def tags_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Configure the log channel for this cog."""
        perms: discord.Permissions = channel.permissions_for(ctx.guild.me)
        if not all([perms.send_messages, perms.embed_links]):
            return await ctx.send("I need permission to send messages and embed links in the log channel")

        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.tick()

    @checks.mod()
    @tags_group.command(name="log")
    async def tags_log(self, ctx: commands.Context, event_name: LoggingEventName, value: bool):
        """Enable/disable logging certain tag-related events to the logging channel"""
        logging_config = LoggingConfiguration(await self.config.guild(ctx.guild).logging_config())
        logging_config.set(event_name, value)
        await self.config.guild(ctx.guild).logging_config.set(logging_config.to_int())
        await ctx.tick()

    @checks.mod()
    @tags_group.group(name="logging", invoke_without_subcommand=True)
    async def tags_logging_group(self, ctx: commands.Context, enable: bool):
        """Enable/disable logging of tag-related events"""
        await self.config.guild(ctx.guild).logging_enabled.set(enable)
        await ctx.tick()

    @tags_logging_group.command(name="show")
    async def tags_logging_show(self, ctx: commands.Context):
        """View the logging configuration for the tags cog"""
        logging_config = LoggingConfiguration(await self.config.guild(ctx.guild).logging_config())
        log_channel_id = await self.config.guild(ctx.guild).logging_channel()
        log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else "Not set"
        if log_channel:
            log_channel = log_channel.mention
        else:
            log_channel = "Invalid channel"

        description = "\n".join(f"`{key}` - {logging_config.get(key)}" for key in LoggingConfiguration.VALID_FLAGS.keys())
        embed = discord.Embed(
            title="Logging configuration for the tags cog",
            colour=await ctx.embed_colour(),
            description=description,
        ).add_field(name="Channel", value=log_channel)
        await ctx.send(embed=embed)

    # Helper functions

    async def can_log(self, ctx: commands.Context, event_name: str) -> Optional[discord.TextChannel]:
        """
        Returns the configured logging channel if the following conditions for the guild are met:
        - Logging is enabled
        - Logging is enabled for this event
        - Logging channel is configured
        - Logging channel is valid
        """
        config_group = self.config.guild(ctx.guild)
        if not await config_group.logging_enabled():
            return

        logging_config = LoggingConfiguration(await config_group.logging_config())
        if not logging_config.get(event_name):
            return

        logging_channel_id = await config_group.logging_channel()
        return ctx.guild.get_channel(logging_channel_id)

    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        log_channel_id = await self.config.guild(guild).logging_channel()
        if not log_channel_id:
            return None
        return guild.get_channel(log_channel_id)

    async def get_tag(self, guild: discord.Guild, name: str, *, check_aliases: bool = True) -> dict:
        """
        Retrieves a tag from config by name or alias name.
        Raises TagNotFound
        """
        try:
            tags = await self.config.guild(guild).tags()
            matched_tag = [t for t in tags if t["name"] == name]
            if matched_tag:
                return matched_tag[0]

            assert check_aliases == True

            aliases = await self.config.guild(guild).aliases()
            matched_alias = [t for t in aliases if t["source"] == name]

            assert len(matched_alias) == 1

            return await self.get_tag_by_id(guild, matched_alias[0]["target"])
        except AssertionError:
            raise TagNotFound

    async def get_tag_by_id(self, guild: discord.Guild, tag_id: int) -> dict:
        """
        Retrieves a tag from the database by tag ID.
        Raises TagNotFound
        """
        tags = await self.config.guild(guild).tags()
        tag_match = [t for t in tags if t["id"] == tag_id]
        if tag_match:
            return tag_match[0]
        else:
            raise TagNotFound

    async def update_tag_usage(self, ctx: commands.Context, tag: dict):
        """Logs when someone uses a tag"""
        async with self.config.guild(ctx.guild).tag_usage() as usage:
            usage.append({"tag_id": tag["id"], "user_id": str(ctx.author.id)})

    def generate_tag_id(self, ctx: commands.Context) -> str:
        """Generates a random ID seeded from context information and current time"""
        state = random.getstate()
        random.seed(f"{ctx.guild.id}{ctx.channel.id}{ctx.message.id}{ctx.author.id}")
        uuid = "-".join(
            [
                str(int(time.time())),
                str(ctx.guild.id),
                str(ctx.channel.id),
                str(ctx.message.id),
                str(ctx.author.id),
                str(random.randint(0, 99999999)).rjust(8, "0"),
            ]
        )
        uuid = f"""{int(time.time())}{str(random.randint(0, 99999999)).rjust(8, "0")}"""
        random.setstate(state)
        return uuid

    async def get_tag_rank(self, guild: discord.Guild, tag_id: str) -> int:
        """
        Fetches the rank of the tag given, based on how many times it has been used compared to all other tags in the guild.
        """
        usage = await self.config.guild(guild).usage()
        # Number of occurrences for each tag in usage
        counts = Counter([u["tag_id"] for u in usage])
        tag_count = counts.get(tag_id, 0)
        # All unique counts, sorted highest - lowest
        unique_counts = sorted(set(counts.values()), reverse=True)
        return (unique_counts.index(tag_count) if tag_count in unique_counts else len(unique_counts)) + 1
