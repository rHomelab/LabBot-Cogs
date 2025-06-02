import pathlib
from datetime import datetime, timezone
from typing import Optional

import discord
from aiofiles import open as aio_open
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import menu
from redbot.core.utils.mod import is_admin_or_superior


class GuildProfilesCog(commands.Cog):
    """Cog for managing guild profiles (icon and banner)"""

    MAX_PROFILE_NAME_LENGTH = 32
    REQUIRED_ATTACHMENTS = 2

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9237612345, force_registration=True)

        default_guild = {
            # Structure: {profile_name: {"creator": id, "created": timestamp, "icon_path": path, "banner_path": path}}
            "profiles": {}
        }

        self.config.register_guild(**default_guild)

        # Ensure profile storage directories exist
        self.data_path = cog_data_path(self)
        self.profiles_path = self.data_path / "profiles"
        self.profiles_path.mkdir(exist_ok=True, parents=True)

    async def _save_attachment(
        self, attachment: discord.Attachment, guild_id: int, profile_name: str, file_type: str
    ) -> Optional[str]:
        """
        Save an attachment to the cog's data directory.

        Args:
            attachment: The discord attachment to save
            guild_id: The ID of the guild
            profile_name: The name of the profile
            file_type: Either 'icon' or 'banner'

        Returns:
            The path to the saved file relative to the profiles directory, or None if saving failed
        """
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            return None

        # Create guild directory if it doesn't exist
        guild_path = self.profiles_path / str(guild_id)
        guild_path.mkdir(exist_ok=True)

        # Create profile directory if it doesn't exist
        profile_path = guild_path / profile_name.lower()
        profile_path.mkdir(exist_ok=True)

        # Determine file extension
        file_ext = attachment.filename.split(".")[-1] if "." in attachment.filename else "png"

        # Set save path
        file_path = profile_path / f"{file_type}.{file_ext}"

        # Save the file
        try:
            await attachment.save(file_path)
            # Return relative path from profiles directory
            return str(file_path.relative_to(self.profiles_path))
        except Exception:
            # In a real-world scenario, you might want to log this error
            return None

    def _get_file_path(self, rel_path: str) -> pathlib.Path:
        """Convert a relative path to an absolute path within the profiles directory."""
        return self.profiles_path / rel_path

    @commands.group(name="guildprofile")  # type: ignore
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _guildprofile(self, ctx: commands.GuildContext):
        """Manage guild profiles (icon and banner)."""
        pass

    @_guildprofile.command(name="create")
    async def _create(self, ctx: commands.GuildContext, name: str):
        """
        Create a new guild profile with the specified name.

        You must attach both an icon and a banner image, **in this order**, to the message.
        """
        # Validate profile name
        if not name or len(name) > self.MAX_PROFILE_NAME_LENGTH:
            await ctx.send(f"Profile name must be between 1 and {self.MAX_PROFILE_NAME_LENGTH} characters.")
            return

        # Check for attachments
        if len(ctx.message.attachments) < self.REQUIRED_ATTACHMENTS:
            await ctx.send("You must attach both an icon and a banner image, **in this order**, to the message.")
            return

        # Assumes first attachment is icon, second is banner
        icon_attachment = ctx.message.attachments[0]
        banner_attachment = ctx.message.attachments[1]

        # Check if both are images
        if not icon_attachment.content_type or not icon_attachment.content_type.startswith("image/"):
            await ctx.send("The first attachment must be an image for the guild icon.")
            return

        if not banner_attachment.content_type or not banner_attachment.content_type.startswith("image/"):
            await ctx.send("The second attachment must be an image for the guild banner.")
            return

        async with self.config.guild(ctx.guild).profiles() as profiles:
            if name.lower() in profiles:
                await ctx.send(f"A profile named '{name}' already exists. Please use a different name.")
                return

            # Save the attachments
            icon_path = await self._save_attachment(icon_attachment, ctx.guild.id, name, "icon")
            banner_path = await self._save_attachment(banner_attachment, ctx.guild.id, name, "banner")

            if not icon_path or not banner_path:
                await ctx.send("Failed to save one or both images. Please try again.")
                return

            # Create the profile
            profiles[name.lower()] = {
                "creator": ctx.author.id,
                "created": int(datetime.now(timezone.utc).timestamp()),
                "icon_path": icon_path,
                "banner_path": banner_path,
            }

        await ctx.send(f"Guild profile '{name}' created successfully.")

    @_guildprofile.command(name="list")
    async def _list(self, ctx: commands.GuildContext):
        """List all available guild profiles."""
        profiles = await self.config.guild(ctx.guild).profiles()

        if not profiles:
            await ctx.send("No guild profiles have been created yet.")
            return

        embed_page_length = 10  # Number of profiles per page

        profile_list = []
        for name, data in profiles.items():
            creator = ctx.guild.get_member(data["creator"])
            creator_name = creator.display_name if creator else "Unknown User"
            created_time = f"<t:{data['created']}:R>"
            profile_list.append(f"• **{name}** - Created by {creator_name} {created_time}")

        if not profile_list:
            await ctx.send("No guild profiles have been created yet.")
            return

        profile_chunks = [profile_list[i : i + embed_page_length] for i in range(0, len(profile_list), embed_page_length)]

        embeds = []
        for i, chunk in enumerate(profile_chunks):
            embed = discord.Embed(title="Guild Profiles", description="\n".join(chunk), color=await ctx.embed_colour())
            embed.set_footer(text=f"Page {i + 1}/{len(profile_chunks)}")
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, timeout=120)

    @_guildprofile.command(name="info")
    async def _info(self, ctx: commands.GuildContext, name: str):
        """View information about a specific guild profile."""
        profiles = await self.config.guild(ctx.guild).profiles()

        if name.lower() not in profiles:
            await ctx.send(f"No profile named '{name}' exists.")
            return

        profile = profiles[name.lower()]
        creator = ctx.guild.get_member(profile["creator"])
        creator_name = creator.mention if creator else "Unknown User"

        embed = discord.Embed(title=f"Guild Profile: {name}", color=await ctx.embed_colour())
        embed.add_field(name="Creator", value=creator_name, inline=True)
        embed.add_field(name="Created", value=f"<t:{profile['created']}:F>", inline=True)

        # Get file paths for attaching
        icon_path = self._get_file_path(profile["icon_path"])
        banner_path = self._get_file_path(profile["banner_path"])

        # Initialize files list
        files = []

        # Display preview if files exist
        if icon_path.exists():
            # Set the thumbnail to the icon
            file_icon = discord.File(icon_path, filename="icon.png")
            embed.set_thumbnail(url="attachment://icon.png")
            files.append(file_icon)
        else:
            embed.add_field(name="Icon", value="⚠️ Icon unset or not found.", inline=True)

        if banner_path.exists():
            # Set the image to the banner
            file_banner = discord.File(banner_path, filename="banner.png")
            embed.set_image(url="attachment://banner.png")
            files.append(file_banner)
        else:
            embed.add_field(name="Banner", value="⚠️ Banner unset or not found.", inline=True)

        await ctx.send(embed=embed, files=files)

    @_guildprofile.command(name="update")
    async def _update(self, ctx: commands.GuildContext, name: str):
        """
        Update a guild profile's icon and/or banner.

        Attach one or both images to update. The first attachment will be used as the icon,
        and the second attachment (if present) will be used as the banner.
        """

        # Check if the profile exists and validate permissions in one function
        async def validate_profile():
            profiles = await self.config.guild(ctx.guild).profiles()
            if name.lower() not in profiles:
                await ctx.send(f"No profile named '{name}' exists.")
                return None

            profile = profiles[name.lower()]

            return profiles, profile

        result = await validate_profile()
        if result is None:
            return

        profiles, _ = result

        # Check for attachments
        if not ctx.message.attachments:
            await ctx.send("You must attach at least one image (icon or banner) to update.")
            return

        # Update icon if provided (first attachment)
        if len(ctx.message.attachments) >= 1:
            icon_attachment = ctx.message.attachments[0]
            if not icon_attachment.content_type or not icon_attachment.content_type.startswith("image/"):
                await ctx.send("The first attachment must be an image for the guild icon.")
                return

            icon_path = await self._save_attachment(icon_attachment, ctx.guild.id, name, "icon")
            if not icon_path:
                await ctx.send("Failed to save the icon image. Please try again.")
                return

            async with self.config.guild(ctx.guild).profiles() as profiles:
                profiles[name.lower()]["icon_path"] = icon_path

        # Update banner if provided (second attachment)
        if len(ctx.message.attachments) >= self.REQUIRED_ATTACHMENTS:
            banner_attachment = ctx.message.attachments[1]
            if not banner_attachment.content_type or not banner_attachment.content_type.startswith("image/"):
                await ctx.send("The second attachment must be an image for the guild banner.")
                return

            banner_path = await self._save_attachment(banner_attachment, ctx.guild.id, name, "banner")
            if not banner_path:
                await ctx.send("Failed to save the banner image. Please try again.")
                return

            async with self.config.guild(ctx.guild).profiles() as profiles:
                profiles[name.lower()]["banner_path"] = banner_path

        await ctx.send(f"Guild profile '{name}' updated successfully.")

    @_guildprofile.command(name="delete")
    async def _delete(self, ctx: commands.GuildContext, name: str):
        """Delete a guild profile."""
        async with self.config.guild(ctx.guild).profiles() as profiles:
            if name.lower() not in profiles:
                await ctx.send(f"No profile named '{name}' exists.")
                return

            profile = profiles[name.lower()]

            # Check if user is creator or has admin privileges
            if profile["creator"] != ctx.author.id and not await is_admin_or_superior(self.bot, ctx.author):
                await ctx.send("You don't have permission to delete this profile. Only the creator or admins can delete it.")
                return

            # Try to delete the files
            try:
                icon_path = self._get_file_path(profile["icon_path"])
                banner_path = self._get_file_path(profile["banner_path"])

                if icon_path.exists():
                    icon_path.unlink()

                if banner_path.exists():
                    banner_path.unlink()

                # Try to remove the profile directory if it's empty
                profile_dir = icon_path.parent
                if profile_dir.exists() and not any(profile_dir.iterdir()):
                    profile_dir.rmdir()
            except Exception:
                # Continue even if file deletion fails
                pass

            # Remove the profile from config
            del profiles[name.lower()]

        await ctx.send(f"Guild profile '{name}' deleted successfully.")

    @_guildprofile.command(name="apply")
    async def _apply(self, ctx: commands.GuildContext, name: str):
        """
        Apply a guild profile to the current guild.

        This will update the guild's icon and banner to match the profile.
        Requires administrator privileges.
        """
        profiles = await self.config.guild(ctx.guild).profiles()

        if name.lower() not in profiles:
            await ctx.send(f"No profile named '{name}' exists.")
            return

        profile = profiles[name.lower()]

        # Get file paths
        icon_path = self._get_file_path(profile["icon_path"])
        banner_path = self._get_file_path(profile["banner_path"])

        if not icon_path.exists():
            await ctx.send("The icon file for this profile no longer exists.")
            return

        if not banner_path.exists():
            await ctx.send("The banner file for this profile no longer exists.")
            return
        # Apply changes
        try:
            async with aio_open(icon_path, "rb") as icon_file:
                icon_data = await icon_file.read()

            async with aio_open(banner_path, "rb") as banner_file:
                banner_data = await banner_file.read()

            await ctx.guild.edit(icon=icon_data, banner=banner_data, reason=f"Guild profile '{name}' applied by {ctx.author}")
            await ctx.send(f"Guild profile '{name}' has been applied to the guild.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to change the guild's icon and banner.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while updating the guild: {e!s}")
