from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional, Self, TypedDict, Union

import discord
from redbot.core import commands


class SessionCancelled(Exception):
    """Raised when an interactive session is closed by the user"""


class Payload(TypedDict):
    content: Optional[str]
    embed: Optional[discord.Embed]


class InteractiveSession:
    ctx: commands.Context
    payload: Payload

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.payload = {"content": None, "embed": None}

    def predicate(self, message: discord.Message) -> bool:
        return message.channel == self.ctx.channel and message.author == self.ctx.author

    async def get_response(self, question: str) -> str:
        await self.ctx.send(question)
        response = (await self.ctx.bot.wait_for("message", check=self.predicate, timeout=60 * 10)).content
        if response == "exit()":
            raise SessionCancelled
        return response

    async def get_literal_answer(self, question: str, answers: List[str]):
        if not all(map(str.lower, answers)):
            raise ValueError("All values in the answer list must be lowercase")

        possible_answers = "/".join(f"`{a}`" for a in answers)
        while True:
            answer = (await self.get_response(f"{question} {possible_answers}")).lower()
            if answer not in answers:
                await self.ctx.send("Please send a valid answer (listed above)")
            else:
                return answer

    async def get_boolean_answer(self, question: str) -> bool:
        return (await self.get_literal_answer(question, ["y", "n"])) == "y"

    @classmethod
    def from_session(cls, session: InteractiveSession) -> Self:
        return cls(session.ctx)

    @abstractmethod
    async def confirm_sample(self) -> bool:
        """Sends the constructed payload and confirms the user is happy with it."""
        return False


class MessageBuilder(InteractiveSession):
    async def run(self) -> Payload:
        content = await self.get_response("Please enter the message you want to send.")
        self.payload.update({"content": content})
        if await self.confirm_sample():
            return self.payload

        return await self.run()

    async def confirm_sample(self) -> bool:
        await self.ctx.send("Here is the message you have created.")
        await self.ctx.send(**self.payload)
        return await self.get_boolean_answer("Are you happy with this?")


class EmbedBuilder(InteractiveSession):
    async def get_title(self) -> str:
        title = await self.get_response("What should the title be?")
        if len(title) > 256:  # noqa: PLR2004
            await self.ctx.send("The title must be 256 characters or less.")
            return await self.get_title()

        return title

    async def get_description(self, *, send_tutorial: bool = True) -> str:
        # fixme: your function is rubbish @Issy
        max_length = 4096
        if send_tutorial:
            await self.ctx.send(
                f"The description can be up to {max_length} characters in length.\n"
                "For this section you may send multiple messages, and you can send"
                "`retry()` to clear the description and start again.\n"
                "Sending `finish()` will complete the description and move forward to the next stage."
            )
        description: List[str] = []
        while len("\n".join(description)) <= max_length:
            response = (await self.ctx.bot.wait_for("message", check=self.predicate, timeout=60 * 10)).content
            if response == "exit()":
                raise SessionCancelled
            elif response == "retry()":
                return await self.get_description(send_tutorial=False)
            elif response == "finish()":
                break

            if sum(map(len, [*description, response])) > max_length:
                remaining_chars = max_length - len("\n".join(description)) - 1
                if remaining_chars == 0:
                    if not await self.get_boolean_answer("Max char limit reached. Do you want to submit this description?"):
                        return await self.get_description(send_tutorial=False)
                    else:
                        break

                await self.ctx.send(
                    "This segment of the description is too long, please retry this part.\n"
                    f"You have {remaining_chars} characters remaining."
                )
                continue

            description.append(response)

        return "\n".join(description)

    async def run(self) -> Payload:
        embed = discord.Embed(colour=await self.ctx.embed_colour())
        if await self.get_boolean_answer("Do you want a title on this embed?"):
            embed.title = await self.get_title()
            await self.ctx.send("Title added.")

        if await self.get_boolean_answer("Do you want to add a description?"):
            embed.description = await self.get_description()
            await self.ctx.send("Description added.")

        self.payload.update({"embed": embed})
        if not embed:
            await self.ctx.send("You can't use an empty embed.\nPlease go through the options again.")
            return await self.run()

        if await self.confirm_sample():
            return self.payload
        else:
            return await self.run()

    async def confirm_sample(self) -> bool:
        await self.ctx.send("Here is the embed you have created.")
        await self.ctx.send(**self.payload)
        return await self.get_boolean_answer("Are you happy with this?")


class MixedBuilder(InteractiveSession):
    async def run(self) -> Payload:
        message_payload = await MessageBuilder.from_session(self).run()
        await self.ctx.send("Message added.")
        embed_payload = await EmbedBuilder.from_session(self).run()
        await self.ctx.send("Embed added.")

        self.payload.update({"content": message_payload["content"], "embed": embed_payload["embed"]})
        return self.payload

    async def confirm_sample(self) -> bool:
        return False


async def make_session(ctx: commands.Context) -> Payload:
    await ctx.send(
        "Entering the interactive message builder. You can send `exit()` at any point to cancel the current builder."
    )
    session = InteractiveSession(ctx)
    builders = {"embed": EmbedBuilder, "message": MessageBuilder, "both": MixedBuilder}
    builder: Union[MessageBuilder, EmbedBuilder] = builders[
        await session.get_literal_answer("Do you want this to be an embed or regular message?", list(builders.keys()))
    ].from_session(session)
    return await builder.run()
