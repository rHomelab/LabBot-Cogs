from __future__ import annotations

from typing import Any, Dict, List, Union

import discord
from redbot.core import commands


class SessionCancelled(Exception):
    "Raised when an interactive session is closed by the user"


class InteractiveSession:
    ctx: commands.Context
    payload: Dict[str, Any]

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
        if not all([a.islower() for a in answers]):
            raise ValueError("All values in the answer list must be lowercase")

        possible_answers = "/".join(f"`{a}`" for a in answers)
        while True:
            answer = (await self.get_response(f"{question} {possible_answers}")).lower()
            if answer not in answers:
                await self.ctx.send(f"Please send a valid answer (listed below)")
            else:
                return answer

    async def get_boolean_answer(self, question: str) -> bool:
        return True if (await self.get_literal_answer(question, ["y", "n"])) == "y" else False

    @classmethod
    def from_session(cls, session: InteractiveSession) -> InteractiveSession:
        return cls(session.ctx)

    async def confirm_sample(self) -> bool:
        """
        Method to be used by subclasses only.
        Sends the constructed payload and confirms the user is happy with it.
        """
        await self.ctx.send("Here is the message you have created.")
        await self.ctx.send(**self.payload)
        return await self.get_boolean_answer("Are you happy with this?")


class MessageBuilder(InteractiveSession):
    payload: Dict[str, str]

    async def run(self) -> Dict[str, str]:
        content = await self.get_response("Please enter the message you want to send.")
        self.payload.update({"content": content})
        if await self.confirm_sample():
            return self.payload
        else:
            return await self.run()


class EmbedBuilder(InteractiveSession):
    payload: Dict[str, discord.Embed]

    async def get_title(self) -> str:
        title = await self.get_response("What should the title be?")
        if len(title) > 256:
            await self.ctx.send("The title must be 256 characters or less.")
            return await self.get_title()

        return title

    async def get_description(self, *, send_tutorial: bool = True) -> str:
        MAX_LENGTH = 4096
        if send_tutorial:
            await self.ctx.send(
                f"The description can be up to {MAX_LENGTH} characters in length.\n"
                "For this section you may send multiple messages, and you can send `retry()` to clear the description and start again.\n"
                "Sending `finish()` will complete the description and move forward to the next stage."
            )
        description: List[str] = []
        while len("\n".join(description)) <= MAX_LENGTH:
            response = (await self.ctx.bot.wait_for("message", check=self.predicate, timeout=60 * 10)).content
            if response == "exit()":
                raise SessionCancelled
            if response == "retry()":
                return await self.get_description(send_tutorial=False)
            elif response == "finish()":
                break

            if len("\n".join(["\n".join(description), response])) > MAX_LENGTH:
                remaining_chars = MAX_LENGTH - len("\n".join(description)) - 1
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

    async def run(self) -> Dict[str, discord.Embed]:
        embed = discord.Embed(colour=await self.ctx.embed_colour())
        if await self.get_boolean_answer("Do you want a title on this embed?"):
            embed.title = await self.get_title()
            await self.ctx.send("Title added.")

        if await self.get_boolean_answer("Do you want to add a description?"):
            embed.description = await self.get_description()
            await self.ctx.send("Description added.")

        self.payload.update({"embed": embed})
        if not embed:
            await self.ctx.send("You can't use an empty embed.\n Please go through the options again.")
            return await self.run()

        if await self.confirm_sample():
            return self.payload
        else:
            return await self.run()

    async def confirm_sample(self) -> bool:
        """
        Sends the constructed payload and confirms the user is happy with it.
        """
        await self.ctx.send("Here is the embed you have created.")
        await self.ctx.send(**self.payload)
        return await self.get_boolean_answer("Are you happy with this?")


class MixedBuilder(InteractiveSession):
    payload: Dict[str, Union[str, discord.Embed]]

    async def run(self) -> Dict[str, Union[str, discord.Embed]]:
        message_payload = await MessageBuilder.from_session(self).run()
        await self.ctx.send("Message added.")
        embed_payload = await EmbedBuilder.from_session(self).run()
        await self.ctx.send("Embed added.")

        self.payload.update(message_payload)
        self.payload.update(embed_payload)
        return self.payload


async def make_session(ctx: commands.Context) -> Union[MessageBuilder, EmbedBuilder]:
    await ctx.send(
        "Entering the interactive message builder. You can send `exit()` at any point to cancel the current builder."
    )
    session = InteractiveSession(ctx)
    builders = {"embed": EmbedBuilder, "message": MessageBuilder, "both": MixedBuilder}
    builder: Union[MessageBuilder, EmbedBuilder] = builders[
        await session.get_literal_answer("Do you want this to be an embed or regular message?", builders.keys())
    ].from_session(session)
    return await builder.run()
