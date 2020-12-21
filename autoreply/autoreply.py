"""discord red-bot autoreply"""
import asyncio

import discord
import discord.utils
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import menu, next_page, prev_page
import random
import string
from typing import Tuple

CUSTOM_CONTROLS = {"⬅️": prev_page, "➡️": next_page}


class AutoReplyCog(commands.Cog):
    """AutoReply Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633005)

        default_guild_config = {
            "triggers": {},  # trigger: [{response: str, fuzzy: bool}]
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        triggers = await self.config.guild(message.guild).triggers()

        for key in triggers:
            for response, fuzzy, _ in [[i for (_, i) in d.items()] for d in triggers[key]]:
                if fuzzy and key.lower() in message.content.lower():
                    await message.channel.send(response)
                elif not fuzzy and message.content.lower().strip() == key.lower():
                    await message.channel.send(response)

        for trigger in triggers:
            if trigger.lower() == message.content.lower():
                await message.channel.send(triggers[trigger])

    # Command groups

    @checks.admin()
    @commands.group(name="autoreply", pass_context=True)
    async def _autoreply(self, ctx):
        """Automatically reply to messages matching certain trigger phrases"""

    # Commands

    @_autoreply.command(name="add")
    async def _add(self, ctx, trigger: str = "", response: str = ""):
        """Add autoreply trigger"""
        if not trigger:
            question = "Let's set up an autoreply trigger. Please enter the phrase you want this autoreply to trigger on"
            trigger = await self.get_reply(ctx, question)
            if not trigger:
                return

        if not response:
            question = "Please enter the response for this trigger"
            response = await self.get_reply(ctx, question)
            if not response:
                return

        question = "Do you want this trigger to be fuzzy matched? (allows matching in the middle of a message)"
        fuzzy = await self.get_confirmation(ctx, question)
        if fuzzy is None:
            return

        question = "Are you sure you want to add this autoreply trigger?"
        colour = await ctx.embed_colour()
        embed = self.make_trigger_embed(colour, {"trigger": trigger, "response": response, "fuzzy": fuzzy})
        sure = await self.get_confirmation(ctx, question, embed=embed)
        if not sure:
            return

        async with self.config.guild(ctx.guild).triggers() as triggers:
            to_insert = {
                "response": response,
                "fuzzy": fuzzy,
                "uid": await self.make_uid()
            }
            if trigger in triggers:
                triggers[trigger].append(to_insert)
            else:
                triggers[trigger] = [to_insert]

        await ctx.send(f"✅ Autoreply trigger successfully added with ID {}")

    @commands.guild_only()
    @_autoreply.command(name="view")
    async def _view(self, ctx):
        """View the configuration for the autoreply cog"""
        triggers = await self.get_flattened_config(ctx.guild)
        colour = await ctx.embed_colour()
        embed_list = [self.make_trigger_embed(colour, i) for i in triggers]

        if not embed_list:
            error_embed = self.make_error_embed(ctx, error_type="NoConfiguration")
            await ctx.send(embed=error_embed)
            return

        for i, embed in enumerate(embed_list):
            embed.set_footer(text=f"{i + 1} of {len(embed_list)}")

        if len(embed_list) > 1:
            await menu(
                ctx,
                pages=embed_list,
                controls=CUSTOM_CONTROLS,
                timeout=5 * 60,
            )

        elif len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])

    @commands.guild_only()
    @_autoreply.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx, uid: str):
        """Remove a reaction pair

        Example:
        - `[p]autoreply remove <index>`
        To find the index of an autoreply pair do `[p]autoreply view`
        """
        items = await self.get_flattened_config(ctx.guild)
        if uid not in [i["uid"] for i in items]:
            await ctx.send("Sorry, couldn't find any autoreply pairs with that UID")
            return

        to_del = [i for i in items if i["uid"] == uid][0]
        colour = await ctx.embed_colour()
        embed = self.make_trigger_embed(colour, to_del)
        confirmation = await self.get_confirmation(
            ctx,
            "Are you sure you want to remove this autoreply trigger?",
            embed=embed,
        )
        if not confirmation:
            return

        await self.remove_trigger(ctx.guild, to_del)
        success_embed = self.make_trigger_embed(colour, to_del)
        success_embed.title = "Autoreply trigger pair removed"
        await ctx.send(embed=success_embed)

    # Helper functions

    async def remove_trigger(self, guild: discord.Guild, trigger: dict):
        async with self.config.guild(guild).triggers() as triggers:
            if key := trigger["trigger"] in triggers:
                del trigger["trigger"]
                triggers[key].remove(trigger)

    def make_error_embed(self, ctx, error_type: str) -> discord.Embed:
        error_msgs = {
            "NoConfiguration": "No configuration has been set for this guild",
            "UIDNotFound": "Autoreply UID not found in guild configuration"
        }
        error_embed = discord.Embed(
            title="Error",
            description=error_msgs[error_type],
            colour=ctx.guild.me.colour,
        )
        return error_embed

    def make_trigger_embed(self, colour: discord.Colour, trigger_dict: dict) -> discord.Embed:
        """Generate a trigger embed"""
        trigger = (
            trigger_dict["trigger"][:1020].ljust(1024, ".")
            if len(trigger_dict["trigger"]) > 1024
            else trigger_dict["trigger"]
        )
        response = (
            trigger_dict["response"][:1020].ljust(1024, ".")
            if len(trigger_dict["response"]) > 1024
            else trigger_dict["response"]
        )
        embed = discord.Embed(colour=colour)
        embed.add_field(name="Trigger", value=trigger, inline=False)
        embed.add_field(name="Response", value=response, inline=False)
        embed.add_field(name="Fuzzy", value=trigger_dict["fuzzy"], inline=True)
        embed.add_field(name="UID", value=trigger_dict["uid"], inline=True)
        return embed

    async def get_reply(self, ctx: discord.Context, question: str, embed: discord.Embed = None) -> str:
        """Get user response"""
        message_object = await ctx.send(question, embed=embed)

        def reply_check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            msg = await self.bot.wait_for(
                "message", check=reply_check, timeout=5 * 60
            )
        except asyncio.TimeoutError:
            await message_object.delete()
            return None
        else:
            return msg.content.strip()

    async def get_confirmation(self, ctx, question: str, embed: discord.Embed = None) -> bool:
        """Docstring here"""
        message_object = await ctx.send(question, embed=embed)

        emojis = ["✅", "❌"]
        for i in emojis:
            await message_object.add_reaction(i)

        def reaction_check(reaction, user):
            return (
                (user == ctx.author)
                and (reaction.message.id == message_object.id)
                and (reaction.emoji in emojis)
            )

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=reaction_check, timeout=5 * 60
            )
        except asyncio.TimeoutError:
            return None
        else:
            if reaction.emoji == "❌":
                await message_object.clear_reactions()
                return False
            return True

    def get_uids(self, triggers: dict) -> Tuple[str]:
        """Fetch all UIDs from a guild config dict"""
        all_uids = []
        for key in triggers:
            for item in triggers[key]:
                all_uids.append(item["uid"])

    async def make_uid(self, triggers: dict) -> str:
        """Generate a unique UID for a trigger pair to be inserted"""
        all_uids = []
        for key in triggers:
            for _, _, uid in [[i for (_, i) in d.items()] for d in triggers[key]]:
                all_uids.append(uid)
        while True:
            new_uid = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(7))
            if new_uid not in all_uids:
                break
        return new_uid

    async def get_flattened_config(self, guild: discord.Guild) -> Tuple[dict]:
        """Returns a tuple of all unique key pairs for the specified guild"""
        triggers = await self.config.guild(guild).triggers()
        flattened_config = []
        for key in triggers:
            for response in triggers[key]:
                response["trigger"] = key
                flattened_config.append(response)
        return tuple(flattened_config)