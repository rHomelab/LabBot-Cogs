from __future__ import annotations

from typing import Any, List, Mapping, Union

import discord
from redbot.core import commands


class SessionCancelled(Exception):
    "Raised when an interactive session is closed by the user"


class InteractiveSession:
    ctx: commands.Context
    payload: Mapping[str, Any]

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.payload = {}

    def predicate(self, message: discord.Message) -> bool:
        return message.channel == self.ctx.channel and message.author == self.ctx.author

    async def get_response(self, question: str) -> str:
        await self.ctx.send(question)
        response = await self.ctx.bot.wait_for("message", check=self.predicate, timeout=60 * 10)
        if response == "exit()":
            raise SessionCancelled
        return response

    async def get_literal_answer(self, question: str, answers: List[str]):
        if not all([a.islower() for a in answers]):
            raise ValueError("All values in the answer list must be lowercase")

        possible_answers = " / ".join(f"`{a}`" for a in answers)
        while True:
            answer = (await self.get_response(f"{question} {possible_answers}")).lower()
            if answer not in answers:
                await self.ctx.send(f"Please send a valid answer {possible_answers}")
            else:
                return answer

    async def get_boolean_answer(self, question: str) -> bool:
        return True if (await self.get_literal_answer(question, ["y", "n"])) == "y" else False

    @classmethod
    def from_session(cls, session: InteractiveSession) -> InteractiveSession:
        return cls(session.ctx)


class MessageBuilder(InteractiveSession):
    payload: Mapping[str, str]

    async def run(self) -> Mapping[str, str]:
        content = await self.get_response("Please enter the message you want to send.")
        check = await self.get_boolean_answer("Are you sure you want to send this?")
        if not check:
            return await self.run()
        else:
            self.payload.update({"content": content})
            return self.payload


class EmbedBuilder(InteractiveSession):
    payload: Mapping[str, discord.Embed]

    async def get_title(self) -> str:
        title = await self.get_response("What should the title be?")
        if len(title) > 256:
            await self.ctx.send("The title must be 256 characters or less.")
            return await self.get_title()

    async def get_description(self, *, send_tutorial: bool = True) -> str:
        MAX_LENGTH = 4096
        if send_tutorial:
            await self.ctx.send(
                f"""
                The description can be up to {MAX_LENGTH} characters in length.
                For this section you may send multiple messages, and you can send `retry()` to clear the description and start again.
                Sending `finish()` will complete the description and move forward to the next stage.
                """
            )
        description: List[str] = []
        while len("\n".join(description)) <= MAX_LENGTH:
            response: discord.Message = await self.ctx.bot.wait_for("message", check=self.predicate, timeout=60 * 10)
            if response == "retry()":
                return await self.get_description(send_tutorial=False)
            elif response == "finish()":
                break

            if len("\n".join(["\n".join(description), response])) > MAX_LENGTH:
                remaining_chars = MAX_LENGTH - len("\n".join(description))
                await self.ctx.send(
                    f"""
                    This segment of the description is too long, please retry this part.
                    You have {remaining_chars} remaining.
                    """
                )
                continue

            description.append(response.content)

        return "\n".join(description)

    async def run(self) -> Mapping[str, discord.Embed]:
        embed = discord.Embed(colour=await self.ctx.embed_colour())
        if await self.get_boolean_answer("Do you want a title on this embed?"):
            embed.title = await self.get_title()
        if await self.get_boolean_answer("Do you want to add a description?"):
            embed.description = await self.get_description()


async def make_session(ctx: commands.Context) -> Union[MessageBuilder, EmbedBuilder]:
    await ctx.send(
        "Entering the interactive message builder. You can send `exit()` at any point to cancel the current builder."
    )
    session = InteractiveSession(ctx)
    builders = {"embed": EmbedBuilder, "message": MessageBuilder}
    builder: Union[MessageBuilder, EmbedBuilder] = builders[
        await session.get_literal_answer("Do you want this to be an embed or regular message?", builders.keys())
    ].from_session(session)
    return await builder.run()
