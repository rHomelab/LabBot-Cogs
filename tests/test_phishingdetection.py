from typing import List, Set

import aiohttp
import pytest

from phishingdetection import phishingdetection


def mutate_url(url: str) -> List[str]:
    return [url, f"http://{url}", f"https://{url}", f"https://www.{url}", f"https://www.{url}/foobar", f"https://{url}/foobar"]


@pytest.fixture
async def session() -> aiohttp.ClientSession:
    client_session: aiohttp.ClientSession = aiohttp.ClientSession(headers={"X-Identity": "Test client"})
    yield client_session
    await client_session.close()


@pytest.fixture
async def urls(session: aiohttp.ClientSession) -> Set[str]:
    return await phishingdetection.get_all_urls(session)


@pytest.fixture
def legitimate_urls() -> Set[str]:
    return {"discord.com", "discordapp.com", "twitch.tv", "twitter.com", "tenor.com", "giphy.com"}


async def test_fetch_urls(session: aiohttp.ClientSession):
    urls = await phishingdetection.get_all_urls(session)
    assert len(urls) > 0


async def test_can_match(urls: Set[str]):
    predicate = phishingdetection.generate_predicate_from_urls(urls)
    for url in urls:
        for mutation in mutate_url(url):
            assert predicate(mutation) is True


async def test_no_false_match(urls: Set[str], legitimate_urls: Set[str]):
    predicate = phishingdetection.generate_predicate_from_urls(urls)
    for url in legitimate_urls:
        for mutation in mutate_url(url):
            assert predicate(mutation) is False
