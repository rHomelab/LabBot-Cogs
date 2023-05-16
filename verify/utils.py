from datetime import timedelta
from typing import Callable, Literal

import discord


def within_an_hour_predicate(member: discord.Member, attribute: Literal["joined_at", "created_at"]) -> Callable[[discord.Member], bool]:
    median = getattr(member, attribute)
    minimum = median - timedelta(hours=1)
    maximum = median + timedelta(hours=1)

    def predicate(m: discord.Member):
        return m.id != member.id and minimum < getattr(m, attribute) < maximum

    return predicate

def select_groups(members: list[discord.Member]) -> tuple[tuple[discord.Member]]:
    """Find members that joined around the same time period, and accounts were created in same time period"""
    groups = []
    to_ignore = []

    for member in members:
        similar_joined = tuple(filter(within_an_hour_predicate(member, "joined_at"), members))
        if not similar_joined:
            continue

        similar_created = tuple(filter(within_an_hour_predicate(member, "created_at"), members))
        if not similar_created:
            continue

        overlap = []
