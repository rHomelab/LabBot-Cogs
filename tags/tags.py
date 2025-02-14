from datetime import datetime
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu
from redbot.core.utils.mod import is_mod_or_superior

from tags.utils import Alias, Tag, TagConfigHelper


async def make_tag_info_embed(tag: Tag, aliases: [Alias]) -> discord.Embed:
    """Construct the Tag information embed to be sent."""
    transfers = []
    for xfer in tag.transfers:
        transfers.append(f"<@{xfer.prior}>")

    alias_list = []
    for alias in aliases:
        alias_list.append(alias.alias)

    result = (
        discord.Embed(
            colour=discord.Colour.blue(),
        )
        .add_field(name="Tag", value=f"`{tag.tag}`")
        .add_field(name="Creator", value=f"<@{tag.creator}>")
        .add_field(name="Owner", value=f"<@{tag.owner}>")
        .add_field(name="Created", value=f"<t:{tag.created}:F>")
        .add_field(name="Usage", value=len(tag.uses))
        .add_field(name="Transfers", value=len(tag.transfers))
    )
    if len(aliases) > 0:
        result.add_field(name="Aliases", value=f"`{', '.join(alias_list)}`")
    if len(transfers) > 0:
        result.add_field(name="Prior Owners", value=", ".join(transfers))

    return result


class TagCog(commands.Cog):
    """Tag cog"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = TagConfigHelper()

    @commands.guild_only()
    @commands.group(name="tag", pass_context=True, invoke_without_command=True)
    async def _tag(self, ctx: commands.Context, trigger: str):
        """Manage tags and aliases."""
        tag, alias = await self.config.get_tag_or_alias(ctx, trigger)

        time = int(datetime.utcnow().timestamp())

        if tag is None and alias is None:
            await ctx.send("That's not a valid tag or alias!")
            return
        if tag is None and alias is not None:
            tag = await self.config.get_tag_by_alias(ctx, alias)
            if tag is None:
                await ctx.send("That alias' tag doesn't exist!")
                return

        # Deploy the tag
        await ctx.send(tag.content)

        # Log statistics
        if alias is not None:  # Alias was used
            await self.config.add_alias_use(ctx, alias, ctx.author.id, time)  # Adding an alias use adds the tag use
        else:  # Alias was not used
            await self.config.add_tag_use(ctx, tag, ctx.author.id, time)

    # @_tag.command(name="search")
    # async def _search(self, ctx: commands.Context, query: str):
    #     """Fuzzy search for tags and aliases matching the provided query. (WIP)"""
    #     # TODO: Search for a matching tag or alias and return information about it to the user
    #     await ctx.send("Not yet implemented, please try again later. Sorry!")

    @_tag.command(name="create")
    async def _create(self, ctx: commands.Context, trigger: str, *, content: str):
        """Create a new tag with the provided content (attachments excluded)."""
        test_tag, test_alias = await self.config.get_tag_or_alias(ctx, trigger)

        if test_tag is not None:
            await ctx.send("That tag already exists! You might be able to claim it, or ask the owner to transfer it.")
            return
        if test_alias is not None:
            await ctx.send("That tag already exists as an alias!")
            return

        tag = await self.config.create_tag(ctx, trigger, content)

        await ctx.send("Tag successfully created!")

    # @_tag.command(name="stats")
    # async def _stats(self, ctx: commands.Context, member: discord.Member):
    #     """Provide general stats about the tag system, or if a user is provided, about that user. (WIP)"""
    #     await ctx.send("Stats reporting has not yet been implemented. Don't worry, we're tracking the stats though!")
    #     if not member:
    #         # TODO Return general stats
    #         pass
    #     else:
    #         # TODO Return stats about the user (we've collected many)
    #         pass
    #     pass

    @_tag.command(name="info")
    async def _info(self, ctx: commands.Context, tag: str):
        """Provide information about the specified tag/alias."""
        maybe_tag = await self.config.get_tag(ctx, tag)
        if maybe_tag is None:
            await ctx.send("That's not a known tag!")
        else:
            embed = await make_tag_info_embed(maybe_tag, await self.config.get_aliases_by_tag(ctx, maybe_tag))
            await ctx.send(embed=embed)

    @_tag.command(name="edit")
    async def _edit(self, ctx: commands.Context, trigger: str, *, content: str):
        """Replace the tag content with the supplied content."""
        tag = await self.config.get_tag(ctx, trigger)
        if tag is None:
            await ctx.send("Sorry, that's not a tag. That means you can create it!")
            return

        if not tag.owner == ctx.author.id and not await is_mod_or_superior(self.bot, ctx.author):
            await ctx.send("Sorry, you're not the tag owner and you don't have permissions to do that.")
            return

        if await self.config.edit_tag(ctx, trigger, content) is None:
            await ctx.send("Error editing tag, does not exist.")
        else:
            await ctx.send("Tag content updated!")

    @_tag.command(name="delete")
    async def _delete(self, ctx: commands.Context, trigger: str):
        """Delete the specified tag."""
        tag = await self.config.get_tag(ctx, trigger)
        if tag is None:
            await ctx.send("That isn't a tag, sorry.")
        elif tag.owner == ctx.author.id or await is_mod_or_superior(self.bot, ctx.author):
            await self.config.delete_tag(ctx, trigger)
            await ctx.send("Tag successfully deleted!")
        else:
            await ctx.send("You can't delete that tag. Only the creator or mods can do that, and you're neither!")

    @_tag.command(name="claim")
    async def _claim(self, ctx: commands.Context, trigger: str):
        """Claim an abandoned tag (if the creator has left the guild)."""
        tag = await self.config.get_tag(ctx, trigger)
        if tag is not None:
            if tag.owner == ctx.author.id:
                await ctx.send("You're already that tag's owner!")
            else:
                curr_owner = ctx.guild.get_member(tag.owner)
                if curr_owner is not None:
                    await ctx.send(
                        f"That tag's owner is still in the guild! You can see if {curr_owner.mention} "
                        f"wants to transfer it to you."
                    )
                else:
                    await self.config.transfer_tag(ctx, trigger, ctx.author.id, "Claim", int(datetime.utcnow().timestamp()))
                    await ctx.send("Tag successfully claimed!")
        else:
            await ctx.send("Sorry, that isn't a valid tag so you can't claim it. Good news! You can create it!")

    @_tag.command(name="transfer")
    async def _transfer(self, ctx: commands.Context, trigger: str, member: discord.Member):
        """Transfer ownership of the tag to the specified user."""
        tag = await self.config.get_tag(ctx, trigger)
        if tag is not None:
            allowable = False
            reason = ""
            if tag.owner == ctx.author.id:
                allowable = True
                reason = "Owner-initiated"
            elif await is_mod_or_superior(self.bot, ctx.author):
                allowable = True
                reason = f"Mod-initiated by {ctx.author.mention}"
            if allowable:
                await self.config.transfer_tag(
                    ctx, trigger, member.id, f"Transfer: {reason}", int(datetime.utcnow().timestamp())
                )
                await ctx.send("Tag successfully transferred!")
            else:
                await ctx.send("You can't transfer that tag. Ask the owner if they want to transfer it to you.")
        else:
            await ctx.send("That's not a tag! Good news, you can create now!")

    @_tag.command("list")
    async def _list(self, ctx: commands.Context, user: Optional[discord.User]):
        """List all tags and aliases, or just those owned by the user if specified."""
        embed_page_length = 300

        tags = []
        for tag in await self.config.get_tags(ctx, user):
            tags.append(f"* {tag.tag}")
        tags_str = "\n".join(sorted(tags))

        aliases = []
        for alias in await self.config.get_aliases(ctx, user):
            aliases.append(f"* **Tag:** {alias.tag}  \n  **Alias:** {alias.alias}")
        aliases_str = "\n".join(sorted(aliases))

        tags_pages = list(pagify(tags_str, page_length=embed_page_length))
        aliases_pages = list(pagify(aliases_str, page_length=embed_page_length))

        tags_embeds = [
            discord.Embed(title="Tags", colour=await ctx.embed_colour(), description=page).set_footer(
                text=f"Page {index} of {len(tags_pages)}"
            )
            for index, page in enumerate(tags_pages, start=1)
        ]
        aliases_embeds = [
            discord.Embed(title="Tag Aliases", colour=await ctx.embed_colour(), description=page).set_footer(
                text=f"Page {index} of {len(aliases_pages)}"
            )
            for index, page in enumerate(aliases_pages, start=1)
        ]

        for embed_list in [tags_embeds, aliases_embeds]:
            if len(embed_list) == 1:
                await ctx.send(embed=embed_list[0])
            else:
                self.bot.loop.create_task(menu(ctx=ctx, pages=embed_list, timeout=120.0))

    @_tag.group(name="alias")
    async def _alias(self, ctx: commands.Context):
        """Manage tag aliases."""
        pass

    @_alias.command("create")
    async def _alias_create(self, ctx: commands.Context, alias: str, tag: str):
        """Create an alias to the specified tag."""

        alias_search_tag, alias_search_aliases = await self.config.get_tag_or_alias(ctx, alias)
        tag_search_tag, tag_search_aliases = await self.config.get_tag_or_alias(ctx, tag)

        if alias_search_tag is not None:
            await ctx.send("Sorry, that alias already exists as a tag.")
            return
        if alias_search_aliases is not None and len(alias_search_aliases) > 0:
            await ctx.send("Sorry, that alias already exists as an alias! Silly you!")
            return

        if tag_search_tag is None:
            await ctx.send("Sorry, that tag doesn't exist so you can't alias it. You can create it though!")
            return
        if tag_search_aliases is not None and len(tag_search_aliases) > 0:
            await ctx.send("You can't alias to another alias! That gets messy.")
            return

        await self.config.create_alias(ctx, alias, tag, ctx.author.id, int(datetime.utcnow().timestamp()))
        await ctx.send("Alias created!")

    @_alias.command("delete")
    async def _alias_delete(self, ctx: commands.Context, trigger: str):
        """Delete the specified alias."""
        alias = await self.config.get_alias(ctx, trigger)
        if alias is None:
            await ctx.send("That isn't an alias, sorry.")
        elif alias.creator == ctx.author.id or await is_mod_or_superior(self.bot, ctx.author):
            await self.config.delete_alias(ctx, trigger)
            await ctx.send("Alias successfully deleted!")
        else:
            await ctx.send("You can't delete that alias. Only the creator or mods can do that, and you're neither!")
