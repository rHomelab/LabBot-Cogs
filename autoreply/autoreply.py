"""discord red-bot autoreply"""

import asyncio
from typing import Optional

import discord
import discord.utils
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import menu, next_page, prev_page, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

CUSTOM_CONTROLS = {"⬅️": prev_page, "➡️": next_page}

EMBED_TRIM_SIZE = 1010


class AutoReplyCog(commands.Cog):
    """AutoReply Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633005)

        default_guild_config = {
            "triggers": {},  # trigger: str response
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        triggers = await self.config.guild(message.guild).triggers()

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
        if not trigger and not response:
            message_object = await ctx.send(
                "Let's set up an autoreply trigger. Please enter the phrase you want this autoreply to trigger on"
            )

            def reply_check(message):
                return message.author == ctx.author and message.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=reply_check, timeout=5 * 60)
            except asyncio.TimeoutError:
                await message_object.delete()
                return
            else:
                trigger = msg.content

            message_object1 = await ctx.send("Please enter the response for this trigger")

            try:
                msg = await self.bot.wait_for("message", check=reply_check, timeout=5 * 60)
            except asyncio.TimeoutError:
                await message_object1.delete()
                await message_object.delete()
                return
            else:
                response = msg.content

        async with self.config.guild(ctx.guild).triggers() as triggers:
            triggers[trigger] = response

        await ctx.send("✅ Autoreply trigger successfully added")

    @commands.guild_only()
    @_autoreply.command(name="view")
    async def _view(self, ctx):
        """View the configuration for the autoreply cog"""
        triggers = await self.ordered_list_from_config(ctx.guild)
        embed_list = [
            await self.make_trigger_embed(ctx, triggers[i], {"current": i + 1, "max": len(triggers)})
            for i in range(len(triggers))
        ]

        if len(embed_list) > 1:
            await menu(
                ctx,
                pages=embed_list,
                controls=CUSTOM_CONTROLS,
                message=None,
                page=0,
                timeout=5 * 60,
            )

        elif len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])

        else:
            error_embed = await self.make_error_embed(ctx, error_type="NoConfiguration")
            await ctx.send(embed=error_embed)

    @commands.guild_only()
    @_autoreply.command(name="remove", aliases=["delete"])
    async def _remove(self, ctx, num: int):
        """Remove a reaction pair

        Example:
        - `[p]autoreply remove <index>`
        To find the index of an autoreply pair do `[p]autoreply view`
        """
        items = await self.ordered_list_from_config(ctx.guild)
        to_del = items[num - 1]
        embed = await self.make_trigger_embed(ctx, to_del)
        msg = await ctx.send(
            embed=embed,
            content="Are you sure you want to remove this autoreply trigger?",
        )
        confirmation = await self.get_confirmation(ctx, msg)
        if confirmation:
            await self.remove_trigger(ctx.guild, to_del["trigger"])
            success_embed = await self.make_removal_success_embed(ctx, to_del)
            await ctx.send(embed=success_embed)

    # Helper functions

    async def remove_trigger(self, guild: discord.Guild, trigger: str):
        async with self.config.guild(guild).triggers() as triggers:
            if trigger in triggers:
                del triggers[trigger]

    async def ordered_list_from_config(self, guild):
        async with self.config.guild(guild).triggers() as triggers:
            return [{"trigger": i, "response": triggers[i]} for i in triggers]

    async def make_error_embed(self, ctx, error_type: str = ""):
        error_msgs = {"NoConfiguration": "No configuration has been set for this guild"}
        error_embed = discord.Embed(
            title="Error",
            description=error_msgs[error_type],
            colour=await ctx.embed_colour(),
        )
        return error_embed

    async def make_removal_success_embed(self, ctx, trigger_dict: dict):
        trigger = (
            trigger_dict["trigger"][:EMBED_TRIM_SIZE]
            if len(trigger_dict["trigger"]) > EMBED_TRIM_SIZE
            else trigger_dict["trigger"]
        )
        response = (
            trigger_dict["response"][:EMBED_TRIM_SIZE]
            if len(trigger_dict["response"]) > EMBED_TRIM_SIZE
            else trigger_dict["response"]
        )
        desc = f"**Trigger:**\n{trigger}\n**Response:**\n{response}"
        embed = discord.Embed(
            title="Autoreply trigger removed",
            description=desc,
            colour=await ctx.embed_colour(),
        )
        return embed

    async def make_trigger_embed(self, ctx, trigger_dict: dict, index=None):
        trigger = (
            trigger_dict["trigger"][:EMBED_TRIM_SIZE]
            if len(trigger_dict["trigger"]) > EMBED_TRIM_SIZE
            else trigger_dict["trigger"]
        )
        response = (
            trigger_dict["response"][:EMBED_TRIM_SIZE]
            if len(trigger_dict["response"]) > EMBED_TRIM_SIZE
            else trigger_dict["response"]
        )
        desc = f"**Trigger:**\n{trigger}\n**Response:**\n{response}"
        embed = discord.Embed(description=desc, colour=await ctx.embed_colour())
        if index:
            embed.set_footer(text=f"{index['current']} of {index['max']}")
        return embed

    async def get_confirmation(self, ctx: commands.Context, msg: discord.Message) -> Optional[bool]:
        """Get confirmation from user with reactions"""
        emojis = ["❌", "✅"]
        start_adding_reactions(msg, emojis)

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", timeout=180.0, check=ReactionPredicate.with_emojis(emojis, msg, ctx.author)
            )
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return
        else:
            await msg.clear_reactions()
            return bool(emojis.index(reaction.emoji))
