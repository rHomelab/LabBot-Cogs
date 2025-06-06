import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Type

import discord
from aiofiles import open as aio_open
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import menu
from redbot.core.utils.mod import is_admin_or_superior

log = logging.getLogger("red.rhomelab.guild_profiles")


@dataclass
class GuildAsset:
    name: str
    creator: int
    created: int
    path: Path

    @classmethod
    def from_dict(cls: Type["GuildAsset"], data: dict) -> "GuildAsset":
        """Create a GuildAsset from a dictionary."""
        return cls(
            name=data["name"],
            creator=int(data["creator"]),
            created=int(data["created"]),
            path=Path(data["path"]),
        )

    def to_dict(self) -> dict:
        """Convert a GuildAsset to a dictionary for storage."""
        return {k: str(v) if isinstance(v, Path) else v for k, v in asdict(self).items()}


class GuildProfilesCog(commands.Cog):
    """Cog for managing guild profiles (icon and banner)"""

    MAX_PROFILE_NAME_LENGTH = 32
    REQUIRED_ATTACHMENTS = 2
    EMBED_PAGE_LENGTH = 10

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9237612345, force_registration=True)

        default_guild = {
            "next_asset_id": 0,
            # Structure: {profile_name: {"creator": id, "created": timestamp, "icon_id": id, "banner_id": id}}
            "profiles": {},
            # Structure: {asset_id: {"name": string, "creator": id, "created": timestamp, "path": path}}
            "assets": {},
        }

        self.config.register_guild(**default_guild)

        # Ensure asset storage directories exist
        self.data_path = cog_data_path(self)
        self.assets_path = self.data_path / "assets"
        self.assets_path.mkdir(exist_ok=True, parents=True)

    def validate_string_safe(self, name: str) -> bool:
        """
        Validate a string to ensure it is safe for use as a profile name.

        Args:
            name: The profile name to validate
        Returns:
            True if the name is valid, False otherwise.
        """
        # Validate profile name
        if not name or len(name) > self.MAX_PROFILE_NAME_LENGTH:
            return False
        # Must not be '.', '..', or contain path separators
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            return False
        # Must match allowed characters only
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", name):
            return False
        return True

    async def _save_attachment(self, attachment: discord.Attachment, guild_id: int, file_name: str) -> Path:
        """
        Save an attachment to the cog's data directory.

        Args:
            attachment: The discord attachment to save
            guild_id: The ID of the guild
            file_name: The name to save the file as (without extension)

        Returns:
            The path to the saved file relative to the assets directory
        """
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            raise ValueError("The attachment could not be identified as an image.")

        # Create guild directory if it doesn't exist
        guild_path = (self.assets_path / str(guild_id)).resolve()
        guild_path.mkdir(exist_ok=True)

        # Determine file extension
        file_ext = Path(attachment.filename).suffix if "." in attachment.filename else ".png"

        # Set save path
        file_path = guild_path / f"{file_name}{file_ext}"

        # Save the file
        await attachment.save(file_path)
        log.debug(f"Saved asset file to {file_path}")
        # Return relative path from guild directory
        return file_path.relative_to(self.assets_path)

    async def _get_asset(self, guild: discord.Guild, id: int, check_file_exists: bool = True) -> GuildAsset:
        """Get a GuildAsset object for a given asset ID.

        Args:
            guild: The guild to which the asset belongs.
            id: The ID of the asset to retrieve.
            check_file_exists: Whether to check if the asset file exists on disk. Defaults to True.

        Returns:
            A GuildAsset object containing the asset's details.

        Raises:
            ValueError: If the asset ID does not exist in the guild's assets.
        """
        asset_id = str(id)

        assets = await self.config.guild(guild).assets()
        if asset_id not in assets:
            log.error(f"Asset ID {asset_id} does not exist in guild {guild.id}.")
            raise ValueError(f"Asset ID {asset_id} does not exist in the guild's assets.")

        asset_data = assets[asset_id]

        file_path = self.assets_path / asset_data["path"]
        if check_file_exists and not file_path.exists():
            log.error(f"Asset file for ID {asset_id} does not exist at {file_path}.")
            raise FileNotFoundError(f"The asset file for ID {asset_id} does not exist.")

        log.debug(f"Retrieved asset: {asset_data['name']} for guild {guild.id}")

        return GuildAsset(
            name=asset_data["name"], creator=asset_data["creator"], created=asset_data["created"], path=file_path
        )

    async def _delete_asset(self, guild: discord.Guild, id: int, asset: GuildAsset):
        """Delete an asset file and remove it from the guild's assets config.

        Args:
            ctx: The context of the command.
            id: The ID of the asset to delete.
            asset: The GuildAsset object to delete.

        Raises:
            ValueError: If the asset ID does not exist in the guild's assets.
        """
        asset_id = str(id)

        if asset.path.exists():
            asset.path.unlink()
        else:
            log.warning(f"Asset file for ID {asset_id} does not exist at {asset.path}. Skipping deletion.")

        async with self.config.guild(guild).assets() as assets:
            if asset_id not in assets:
                raise ValueError(f"Asset ID {asset_id} does not exist in the guild's assets.")
            del assets[asset_id]

    async def _check_asset_assigned_profiles(self, guild: discord.Guild, id: int) -> list[str]:
        """Check if an asset ID is currently in use by any guild profile.

        Args:
            guild: The guild to check for asset usage.
            id: The ID of the asset to check.

        Returns:
            A list of profile names using the asset.
        """
        asset_assigned_profiles = []
        async with self.config.guild(guild).profiles() as profiles:
            for profile_name, profile_data in profiles.items():
                if int(profile_data.get("icon_id")) == id or int(profile_data.get("banner_id")) == id:
                    asset_assigned_profiles.append(profile_name)
        return asset_assigned_profiles

    @commands.group(name="guildprofile")  # type: ignore
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def guildprofile_cmd(self, ctx: commands.GuildContext):
        """Manage guild profiles and assets."""
        pass

    # Profile management commands

    @guildprofile_cmd.group("profile")
    async def profile_cmd(self, ctx: commands.GuildContext):
        """Manage guild profiles."""
        pass

    @profile_cmd.command(name="create")
    async def create_profile_cmd(self, ctx: commands.GuildContext, name: str, icon_id: int, banner_id: int):
        """
        Create a new guild profile with the specified name and assets.

        To create a profile, you must provide:
        - A profile name.
        - An icon asset ID to use as the profile's icon.
        - A banner asset ID to use as the profile's banner.

        The profile name must be unique and follow the naming rules:
        - Must be 1-32 characters long.
        - Can contain upper or lowercase letters, numbers, underscores, hyphens, and full stops.
        - Must not be `.`, `..`, or contain path separators.
        - Must not already exist in the guild's profiles.

        **Note:**
        The profile name is case-insensitive, meaning "Profile" and "profile" are considered the same.
        """
        profile_name = name.lower()

        if not self.validate_string_safe(profile_name):
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to create a profile with an invalid name: {name}"
            )
            return await ctx.send(
                "Invalid profile name. Please ensure it meets the requirements "
                + f"detailed in `{ctx.prefix}help guildprofile create`."
            )

        for i in [icon_id, banner_id]:
            try:
                _ = await self._get_asset(ctx.guild, i)
            except (ValueError, FileNotFoundError) as e:
                return await ctx.send(f"Error: {e!s}")

        async with self.config.guild(ctx.guild).profiles() as profiles:
            if profile_name in profiles:
                log.debug(
                    f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                    + f"attempted to create a profile with an existing name: {name}"
                )
                return await ctx.send(f"A profile named '{name}' already exists. Please use a different name.")

            # Create the profile
            profiles[profile_name] = {
                "creator": ctx.author.id,
                "created": int(datetime.now(timezone.utc).timestamp()),
                "icon_id": icon_id,
                "banner_id": banner_id,
            }

        log.info(
            f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
            + f"created a new profile with name {name}"
        )

        await ctx.send(f"Guild profile '{name}' created successfully.")

    @profile_cmd.command(name="list")
    async def list_profiles_cmd(self, ctx: commands.GuildContext):
        """List all available guild profiles."""
        profiles = await self.config.guild(ctx.guild).profiles()

        if not profiles:
            return await ctx.send("No guild profiles have been created yet.")

        profile_list = []
        for name, data in profiles.items():
            creator = ctx.guild.get_member(data["creator"])
            creator_name = creator.display_name if creator else "Unknown User"
            created_time = f"<t:{data['created']}:R>"
            profile_list.append(f"- **{name}** - Created by {creator_name} {created_time}")

        profile_chunks = [
            profile_list[i : i + self.EMBED_PAGE_LENGTH] for i in range(0, len(profile_list), self.EMBED_PAGE_LENGTH)
        ]

        embeds = []
        for i, chunk in enumerate(profile_chunks):
            embed = discord.Embed(title="Guild Profiles", description="\n".join(chunk), color=await ctx.embed_colour())
            embed.set_footer(text=f"Page {i + 1}/{len(profile_chunks)}")
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, timeout=120)

    @profile_cmd.command(name="info")
    async def profile_info_cmd(self, ctx: commands.GuildContext, name: str):
        """View information about a specific guild profile."""
        profiles = await self.config.guild(ctx.guild).profiles()
        name = name.lower()

        if name not in profiles:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to view a non-existent profile: {name}"
            )
            return await ctx.send(f"No profile named '{name}' exists.")

        # Show typing indicator while processing
        await ctx.typing()

        profile = profiles[name]
        creator = ctx.guild.get_member(profile["creator"])
        creator_name = creator.mention if creator else "Unknown User"

        embed = discord.Embed(title=f"Guild Profile: {name}", color=await ctx.embed_colour())
        embed.add_field(name="Creator", value=creator_name, inline=True)
        embed.add_field(name="Created", value=f"<t:{profile['created']}:F>", inline=True)

        # Get file paths for icon and banner
        try:
            icon_asset = await self._get_asset(ctx.guild, profile["icon_id"])
            banner_asset = await self._get_asset(ctx.guild, profile["banner_id"])
        except (ValueError, FileNotFoundError) as e:
            return await ctx.send(f"Failed to retrieve asset: {e!s}")

        icon_filename = f"icon.{icon_asset.path.suffix.lstrip('.')}"
        banner_filename = f"banner.{banner_asset.path.suffix.lstrip('.')}"

        file_icon = discord.File(icon_asset.path, filename=icon_filename)
        file_banner = discord.File(banner_asset.path, filename=banner_filename)

        # Set the thumbnail to the icon
        embed.set_thumbnail(url=f"attachment://{icon_filename}")
        # Set the image to the banner
        embed.set_image(url=f"attachment://{banner_filename}")

        await ctx.send(embed=embed, files=[file_icon, file_banner])

    @profile_cmd.command(name="update")
    async def update_profile_cmd(self, ctx: commands.GuildContext, name: str, icon_id: int | None, banner_id: int | None):
        """
        Update a guild profile's icon and/or banner.

        To update a profile, you must provide the profile name and at least one of the following:
        - An icon asset ID to update the profile's icon.
        - A banner asset ID to update the profile's banner.
        """
        profiles = await self.config.guild(ctx.guild).profiles()
        name = name.lower()

        if name not in profiles:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to update a non-existent profile: {name}"
            )
            return await ctx.send(f"No profile named '{name}' exists.")

        # Update icon if provided
        if icon_id is not None:
            try:
                _ = await self._get_asset(ctx.guild, icon_id)
            except (ValueError, FileNotFoundError) as e:
                return await ctx.send(f"Failed to retrieve asset: {e!s}")

            async with self.config.guild(ctx.guild).profiles() as profiles:
                profiles[name]["icon_id"] = icon_id

            log.info(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"updated the icon for profile {name} to asset ID {icon_id}"
            )

        # Update banner if provided
        if banner_id is not None:
            try:
                _ = await self._get_asset(ctx.guild, banner_id)
            except (ValueError, FileNotFoundError) as e:
                return await ctx.send(f"Failed to retrieve asset: {e!s}")

            async with self.config.guild(ctx.guild).profiles() as profiles:
                profiles[name]["banner_id"] = banner_id

            log.info(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"updated the banner for profile {name} to asset ID {banner_id}"
            )

        await ctx.send(f"Guild profile '{name}' updated successfully.")

    @profile_cmd.command(name="delete")
    async def delete_profile_cmd(self, ctx: commands.GuildContext, name: str):
        """Delete a guild profile."""
        name = name.lower()

        async with self.config.guild(ctx.guild).profiles() as profiles:
            if name not in profiles:
                log.debug(
                    f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                    + f"attempted to delete a non-existent profile: {name}"
                )
                return await ctx.send(f"No profile named '{name}' exists.")

            profile = profiles[name]

            # Check if user is creator or has admin privileges
            if profile["creator"] != ctx.author.id and not await is_admin_or_superior(self.bot, ctx.author):
                log.warning(
                    f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                    + f"attempted to delete profile {name} without the necessary permissions."
                )
                return await ctx.send(
                    "You don't have permission to delete this profile. " + "Only the creator or admins can delete it."
                )

            # Remove the profile from config
            del profiles[name]

        log.info(
            f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
            + f"deleted the profile {name}"
        )

        await ctx.send(f"Guild profile '{name}' deleted successfully.")

    @profile_cmd.command(name="apply")
    async def apply_profile_cmd(self, ctx: commands.GuildContext, name: str):
        """
        Apply a guild profile to the current guild.

        This will update the guild's icon and banner to match the profile.
        """
        profiles = await self.config.guild(ctx.guild).profiles()
        name = name.lower()

        if name not in profiles:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to apply a non-existent profile: {name}"
            )
            return await ctx.send(f"No profile named '{name}' exists.")

        # Show typing indicator while processing
        await ctx.typing()

        profile = profiles[name]

        # Get file paths
        try:
            icon_asset = await self._get_asset(ctx.guild, profile["icon_id"])
            banner_asset = await self._get_asset(ctx.guild, profile["banner_id"])
        except (ValueError, FileNotFoundError) as e:
            return await ctx.send(f"Failed to retrieve asset: {e!s}")

        # Apply changes
        try:
            async with aio_open(icon_asset.path, "rb") as icon_file:
                icon_data = await icon_file.read()

            async with aio_open(banner_asset.path, "rb") as banner_file:
                banner_data = await banner_file.read()

            await ctx.guild.edit(icon=icon_data, banner=banner_data, reason=f"Guild profile '{name}' applied by {ctx.author}")
            log.info(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"applied profile '{name}' to the guild."
            )
            await ctx.send(f"Guild profile '{name}' has been applied to the guild.")
        except discord.Forbidden:
            log.error(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to apply profile '{name}' but I don't have permission to change the guild's icon and banner."
            )
            await ctx.send("I don't have permission to change the guild's icon and banner.")
        except discord.HTTPException as e:
            log.error(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to apply profile '{name}' but an HTTP error occurred: {e!s}"
            )
            await ctx.send(f"An error occurred while updating the guild: {e!s}")

    # Asset management commands

    @guildprofile_cmd.group("asset")
    async def asset_cmd(self, ctx: commands.GuildContext):
        """Manage guild profile assets."""
        pass

    @asset_cmd.command(name="create")
    async def create_asset_cmd(self, ctx: commands.GuildContext, name: str | None):
        """
        Create a new guild profile asset.

        To create an asset, you must attach an image to the message.

        The asset name, if not provided, will default to the filename of the attached image.

        The asset name must be unique and follow the naming rules:
        - Must be 1-32 characters long.
        - Can contain upper or lowercase letters, numbers, underscores, hyphens, and full stops.
        - Must not be `.`, `..`, or contain path separators.
        """
        if not ctx.message.attachments:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + "attempted to create an asset without attaching an image."
            )
            return await ctx.send("You must attach an image to create an asset.")

        attachment = ctx.message.attachments[0]

        if not name:
            name = Path(attachment.filename).stem

        if not self.validate_string_safe(name):
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to create an asset with an invalid name: {name}"
            )
            return await ctx.send(
                "Invalid asset name. Please ensure it meets the requirements "
                + f"detailed in `{ctx.prefix}help guildprofile asset create`."
            )

        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + f"attempted to create an asset with an invalid attachment. Filename: {attachment.filename}"
            )
            return await ctx.send("The attached file could not be identified as an image.")

        # Get the next unique asset ID
        asset_id = int(await self.config.guild(ctx.guild).next_asset_id())

        try:
            file_path = await self._save_attachment(attachment, ctx.guild.id, str(asset_id))
        except Exception as e:
            log.error(f"Failed to save asset file for guild {ctx.guild.id}: {e!s}")
            return await ctx.send(f"Failed to save the asset file: {e!s}")

        asset = GuildAsset(
            name=name.lower(),
            creator=ctx.author.id,
            created=int(datetime.now(timezone.utc).timestamp()),
            path=file_path,
        )

        # Update the assets dictionary with the new asset
        async with self.config.guild(ctx.guild).assets() as assets:
            assets[asset_id] = asset.to_dict()

        # Increment the next_asset_id counter
        await self.config.guild(ctx.guild).next_asset_id.set(asset_id + 1)

        log.info(
            f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
            + f"created a new asset with name {name}"
        )
        await ctx.send(f"Guild profile asset '{name}' created successfully with ID {asset_id}")

    @asset_cmd.command(name="list")
    async def list_assets_cmd(self, ctx: commands.GuildContext):
        """List all available guild profile assets."""
        assets = await self.config.guild(ctx.guild).assets()

        if not assets:
            return await ctx.send("No guild profile assets have been created yet.")

        asset_list = []
        for id, data in assets.items():
            try:
                asset = GuildAsset(**data)
            except ValueError:
                asset_list.append(f"- **{id}** - Malformed asset. Please recreate.")
                continue

            creator = ctx.guild.get_member(asset.creator)
            creator_name = creator.display_name if creator else "Unknown User"
            created_time = f"<t:{asset.created}:R>"
            asset_list.append(f"- **{id}** - {asset.name} • Created by {creator_name} {created_time}")

        asset_chunks = [asset_list[i : i + self.EMBED_PAGE_LENGTH] for i in range(0, len(asset_list), self.EMBED_PAGE_LENGTH)]

        embeds = []
        for i, chunk in enumerate(asset_chunks):
            embed = discord.Embed(title="Guild Profile Assets", description="\n".join(chunk), color=await ctx.embed_colour())
            embed.set_footer(text=f"Page {i + 1}/{len(asset_chunks)}")
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, timeout=120)

    @asset_cmd.command(name="info")
    async def asset_info_cmd(self, ctx: commands.GuildContext, id: int):
        """View information about a specific guild profile asset."""
        try:
            asset = await self._get_asset(ctx.guild, id)
        except (ValueError, FileNotFoundError) as e:
            return await ctx.send(f"Failed to retrieve asset: {e!s}")

        # Show typing indicator while processing
        await ctx.typing()

        creator = ctx.guild.get_member(asset.creator)
        creator_name = creator.mention if creator else "Unknown User"

        embed = discord.Embed(title=f"Guild Profile Asset: {id}", color=await ctx.embed_colour())
        embed.add_field(name="Name", value=asset.name, inline=True)
        embed.add_field(name="Creator", value=creator_name, inline=True)
        embed.add_field(name="Created", value=f"<t:{asset.created}:F>", inline=True)

        asset_filename = f"asset.{asset.path.suffix.lstrip('.')}"
        file_asset = discord.File(asset.path, filename=asset_filename)
        embed.set_image(url=f"attachment://{asset_filename}")

        await ctx.send(embed=embed, files=[file_asset])

    @asset_cmd.command(name="delete")
    async def delete_asset_cmd(self, ctx: commands.GuildContext, id: int):
        """Delete a guild profile asset."""
        try:
            asset = await self._get_asset(ctx.guild, id, check_file_exists=False)
        except ValueError as e:
            return await ctx.send(f"Failed to retrieve asset for deletion: {e!s}")

        # Check if user is creator or has admin privileges
        if asset.creator != ctx.author.id and not await is_admin_or_superior(self.bot, ctx.author):
            return await ctx.send(
                "You don't have permission to delete this asset. " + "Only the creator or admins can delete it."
            )

        asset_assigned_profiles = await self._check_asset_assigned_profiles(ctx.guild, id)
        if not asset_assigned_profiles:
            try:
                await self._delete_asset(ctx.guild, id, asset)
            except Exception as e:
                log.error(f"Failed to delete asset {id} for guild {ctx.guild.id}: {e!s}")
                return await ctx.send(f"Failed to delete asset: {e!s}")
        else:
            return await ctx.send(
                "This asset is currently in use. Please remove it from the following "
                + f"profile(s) before deleting: {', '.join(asset_assigned_profiles)}"
            )

        await ctx.send(f"Guild profile asset '{id}' deleted successfully.")

    @asset_cmd.command(name="delete_all_unused")
    async def delete_all_unused_assets_cmd(self, ctx: commands.GuildContext):
        """Delete all unused guild profile assets."""
        assets = await self.config.guild(ctx.guild).assets()
        if not assets:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + "attempted to delete unused assets, but no assets exist."
            )
            return await ctx.send("No guild profile assets have been created yet.")

        unused_assets = []
        for id, _ in assets.items():
            try:
                asset = await self._get_asset(ctx.guild, int(id), check_file_exists=False)
            except ValueError as e:
                log.error(f"Failed to retrieve asset {id} for guild {ctx.guild.id}: {e!s}")
                continue
            asset_assigned_profiles = await self._check_asset_assigned_profiles(ctx.guild, int(id))
            if not asset_assigned_profiles:
                unused_assets.append((int(id), asset))

        if not unused_assets:
            log.debug(
                f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
                + "attempted to delete unused assets, but no unused assets were found."
            )
            return await ctx.send("No unused guild profile assets found.")

        deleted_count = 0
        for asset_id, asset in unused_assets:
            try:
                await self._delete_asset(ctx.guild, asset_id, asset)
                deleted_count += 1
            except Exception as e:
                log.error(f"Failed to delete unused asset {asset_id} for guild {ctx.guild.id}: {e!s}")
                await ctx.send(f"Failed to delete asset {asset_id}: {e!s}")
                continue

        log.info(
            f"User {ctx.author.global_name} ({ctx.author.id}) in guild {ctx.guild.name} ({ctx.guild.id}) "
            + f"deleted {deleted_count} unused assets."
        )
        await ctx.send(f"Deleted {deleted_count} unused guild profile assets.")
