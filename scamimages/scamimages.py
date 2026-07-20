"""discord red-bot scam image detection"""

import asyncio
import logging
from io import BytesIO
from typing import Optional

import aiohttp
import discord
import imagehash
from PIL import Image
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

log = logging.getLogger("red.rhomelab.scamimages")

SIMILARITY_THRESHOLD = 10
MAX_HASH_DISPLAY = 10
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class ScamImagesCog(commands.Cog):
    """Scam Images Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=988776655443322111)
        self.session = aiohttp.ClientSession()

        default_guild_settings = {
            "hashes": [],
            "logchannel": 0,
        }

        self.config.register_guild(**default_guild_settings)

    async def cog_unload(self):
        await self.session.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not message.attachments:
            return

        image_attachments = [a for a in message.attachments if a.content_type and a.content_type.startswith("image/")]
        if not image_attachments:
            return

        known_hashes = await self.config.guild(message.guild).hashes()
        if not known_hashes:
            return

        for attachment in image_attachments:
            try:
                phash = await self._compute_phash_from_url(attachment.url)
            except Exception:
                log.debug(f"Failed to compute hash for attachment {attachment.url}", exc_info=True)
                continue

            if phash is None:
                continue

            for stored_hash_str in known_hashes:
                try:
                    stored_hash = imagehash.hex_to_hash(stored_hash_str)
                except Exception:
                    continue

                if phash - stored_hash <= SIMILARITY_THRESHOLD:
                    await self._handle_match(message, attachment, phash, stored_hash_str)
                    return

    async def _handle_match(
        self,
        message: discord.Message,
        attachment: discord.Attachment,
        phash: imagehash.ImageHash,
        matched_hash: str,
    ):
        log.info(
            "Scam image detected from %s (%s) in %s (%s) - hash match: %s",
            message.author, message.author.id, message.guild.name, message.guild.id, str(phash),
        )

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning("Could not delete scam image message from %s", message.author.id)
        except discord.NotFound:
            pass

        ban_reason = f"Automatic ban: posted a known scam image. Hash: {str(phash)}"

        try:
            await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
            log.info("Banned user %s (%s) for posting scam image", message.author, message.author.id)
        except discord.Forbidden:
            log.warning("Could not ban user %s - missing permissions", message.author.id)
            return

        logchannel_id = await self.config.guild(message.guild).logchannel()
        if logchannel_id:
            logchannel = message.guild.get_channel(logchannel_id)
            if logchannel is not None:
                try:
                    embed = discord.Embed(
                        title="Scam Image Detected - User Banned",
                        description=(
                            f"**User:** {message.author} ({message.author.id})\n"
                            f"**Channel:** {message.channel.mention}\n"
                            f"**Matched Hash:** {matched_hash}\n"
                            f"**Image Hash:** {str(phash)}"
                        ),
                        colour=discord.Colour.red(),
                    )
                    if attachment.filename:
                        embed.add_field(name="Filename", value=attachment.filename)
                    await logchannel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def _compute_phash_from_url(self, url: str) -> Optional[imagehash.ImageHash]:
        async with self.session.get(url, timeout=REQUEST_TIMEOUT) as response:
            if response.status != 200:
                return None
            image_data = await response.read()

        try:
            image = Image.open(BytesIO(image_data))
            return imagehash.phash(image)
        except Exception:
            return None

    async def _compute_phash_from_message(self, message: discord.Message) -> list[Optional[imagehash.ImageHash]]:
        results = []
        image_attachments = [a for a in message.attachments if a.content_type and a.content_type.startswith("image/")]
        for attachment in image_attachments:
            phash = await self._compute_phash_from_url(attachment.url)
            results.append(phash)
        return results

    @checks.admin()
    @commands.guild_only()
    @commands.group(name="scamimages")  # type: ignore
    async def _scamimages(self, ctx: commands.GuildContext):
        """Scam image detection commands."""

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="add")  # type: ignore
    async def scamimages_add(self, ctx: commands.GuildContext, url: Optional[str] = None):
        """Add an image to the scam detection database.

        Provide a URL, attach an image, or reply to a message with an image.

        Examples:
        - `[p]scamimages add https://example.com/scam.png`
        - `[p]scamimages add` (with an image attached)
        - `[p]scamimages add` (reply to a message containing an image)
        """
        image_url: Optional[str] = url

        if image_url is None:
            if ctx.message.attachments:
                image_url = ctx.message.attachments[0].url
            elif ctx.message.reference is not None:
                replied = ctx.message.reference.resolved
                if replied is not None and isinstance(replied, discord.Message) and replied.attachments:
                    image_url = replied.attachments[0].url

        if image_url is None:
            await ctx.send("Please provide an image URL, attach an image, or reply to a message with an image.")
            return

        phash = await self._compute_phash_from_url(image_url)
        if phash is None:
            await ctx.send("Failed to process the image. Make sure the URL is valid and points to an image.")
            return

        hash_str = str(phash)
        known_hashes = await self.config.guild(ctx.guild).hashes()

        for stored_hash_str in known_hashes:
            try:
                stored_hash = imagehash.hex_to_hash(stored_hash_str)
            except Exception:
                continue
            if phash - stored_hash <= SIMILARITY_THRESHOLD:
                await ctx.send(
                    f"This image is already in the database (similar to hash `{stored_hash_str}`). "
                    f"Hamming distance: {phash - stored_hash}"
                )
                return

        async with self.config.guild(ctx.guild).hashes() as hashes:
            hashes.append(hash_str)

        await ctx.send(
            f"**Hash:** `{hash_str}`\n**Total hashes:** {len(known_hashes) + 1}"
        )
        log.info("Added scam image hash %s to guild %s (%s)", hash_str, ctx.guild.name, ctx.guild.id)

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="remove")  # type: ignore
    async def scamimages_remove(self, ctx: commands.GuildContext, index: int):
        """Remove an image hash from the database by its index.

        Use `[p]scamimages list` to see hashes and their indices.

        Example:
        - `[p]scamimages remove 3`
        """
        hashes = await self.config.guild(ctx.guild).hashes()
        if not hashes:
            await ctx.send("The scam image database is empty.")
            return

        if index < 1 or index > len(hashes):
            await ctx.send(f"Invalid index. Use a number between 1 and {len(hashes)}.")
            return

        removed = hashes.pop(index - 1)
        await self.config.guild(ctx.guild).hashes.set(hashes)

        await ctx.send(f"Removed hash `{removed}` from the database. **Remaining:** {len(hashes)}")
        log.info("Removed scam image hash %s from guild %s (%s)", removed, ctx.guild.name, ctx.guild.id)

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="list")  # type: ignore
    async def scamimages_list(self, ctx: commands.GuildContext):
        """List all image hashes in the scam detection database."""
        hashes = await self.config.guild(ctx.guild).hashes()

        if not hashes:
            await ctx.send("The scam image database is empty.")
            return

        pages = []
        for i in range(0, len(hashes), MAX_HASH_DISPLAY):
            chunk = hashes[i : i + MAX_HASH_DISPLAY]
            description = "\n".join(f"**{i + j + 1}.** `{h}`" for j, h in enumerate(chunk))
            embed = discord.Embed(
                title=f"Scam Image Database ({len(hashes)} total)",
                description=description,
                colour=await ctx.embed_colour(),
            )
            embed.set_footer(text=f"Threshold: {SIMILARITY_THRESHOLD} | Page {len(pages) + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await menu(ctx, pages=pages, controls={"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}, timeout=180.0)

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="logchannel")  # type: ignore
    async def scamimages_logchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Set the channel where ban alerts are logged.

        Example:
        - `[p]scamimages logchannel #mod-log`
        """
        if not channel.permissions_for(ctx.me).send_messages:
            await ctx.send("I do not have permission to send messages in that channel.")
            return

        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.message.add_reaction("✅")

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="scan")  # type: ignore
    async def scamimages_scan(self, ctx: commands.GuildContext):
        """Manually scan a message for scam images.

        Attach an image or reply to a message containing an image.

        Examples:
        - `[p]scamimages scan` (with an image attached)
        - `[p]scamimages scan` (reply to a message with an image)
        """
        target: Optional[discord.Message] = None

        if ctx.message.reference is not None:
            target = ctx.message.reference.resolved
            if not isinstance(target, discord.Message):
                target = None

        if target is None and ctx.message.attachments:
            hashes = await self._compute_phash_from_message(ctx.message)
            await self._report_scan_results(ctx, hashes)
            return

        if target is None:
            await ctx.send("Please reply to a message to scan it, or attach an image to your command message.")
            return

        if not target.attachments:
            await ctx.send("The target message has no attachments.")
            return

        hashes = await self._compute_phash_from_message(target)
        await self._report_scan_results(ctx, hashes)

    async def _report_scan_results(self, ctx: commands.GuildContext, hashes: list[Optional[imagehash.ImageHash]]):
        known_hashes = await self.config.guild(ctx.guild).hashes()

        if not hashes or all(h is None for h in hashes):
            await ctx.send("No valid images found to scan.")
            return

        matches = []
        for phash in hashes:
            if phash is None:
                continue
            for stored_hash_str in known_hashes:
                try:
                    stored_hash = imagehash.hex_to_hash(stored_hash_str)
                except Exception:
                    continue
                dist = phash - stored_hash
                if dist <= SIMILARITY_THRESHOLD:
                    matches.append((str(phash), stored_hash_str, dist))

        if matches:
            description = "\n".join(
                f"- Image hash `{ph}` matched stored hash `{sh}` (distance: {d})" for ph, sh, d in matches
            )
            embed = discord.Embed(
                title="Scam Image Match Found!",
                description=description,
                colour=discord.Colour.red(),
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No scam images detected in the scanned image(s).")

    @checks.admin()
    @commands.guild_only()
    @_scamimages.command(name="clear")  # type: ignore
    async def scamimages_clear(self, ctx: commands.GuildContext):
        """Clear the entire scam image database for this guild.

        This action is irreversible.
        """
        confirm_msg = await ctx.send(
            "Are you sure you want to clear the entire scam image database? "
            "React with ✅ to confirm or ❌ to cancel."
        )

        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return user == ctx.author and str(reaction.emoji) in ("✅", "❌") and reaction.message.id == confirm_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await confirm_msg.clear_reactions()
            await ctx.send("Timed out. Database was not cleared.")
            return

        if str(reaction.emoji) == "✅":
            await self.config.guild(ctx.guild).hashes.set([])
            await confirm_msg.clear_reactions()
            await ctx.send("Scam image database has been cleared.")
            log.info("Scam image database cleared for guild %s (%s)", ctx.guild.name, ctx.guild.id)
        else:
            await confirm_msg.clear_reactions()
            await ctx.send("Cancelled. Database was not cleared.")
