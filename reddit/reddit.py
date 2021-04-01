"""discord red-bot reddit"""
import asyncio
from typing import List, Union
from datetime import datetime as dt

import discord
from redbot.core import Config, checks, commands, tasks
import asyncpraw


class RedditCog(commands.Cog):
    praw = None
    praw_last_auth_time = None

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633004)

        default_global_config = {
            # A list of submission IDs and subreddit names for the scan_subreddits task - [{'subreddit': str, 'id': str}]
            "seen_posts": [],
            # A list of dicts containing recently posted messages by the bot from the scan_subreddits task
            "recent_posts": []
            # [{'guild_id': int, 'channel_id': int, 'message_id': int, 'subreddit': str, 'submission_id': str}]
        }
        default_guild_config = {
            # Regular feeds - [{'subreddit': str, 'channel_id': int}]
            "feeds": [],
            # Feeds filtered by post flair - [{'subreddit': str, 'channel_id': int, 'filter': {'flair': str, 'title': str}}]
            "filtered_feeds": [],
        }

        self.config.register_global(**default_global_config)
        self.config.register_guild(**default_guild_config)

        self.check_subreddits.start()
        self.check_recent_posts.start()

    # Events

    @commands.Cog.listener()
    async def on_ready(self):
        await self.authenticate_praw()
        self.scan_subreddits.start()

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.scan_subreddits.cancel()

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name: str, api_tokens: dict):
        if service_name != "reddit":
            return

        await self.authenticate_praw()

    # Command groups

    @checks.mod()
    @commands.group(name="reddit", pass_context=True)
    async def _feed(self, ctx):
        """Subscribe/Unsubscribe to Reddit feeds"""
        pass

    # Commands

    @_feed.command(name="subscribe")
    async def subscribe(self, ctx, subreddit: str, channel: discord.TextChannel):
        """Subscribe to a Reddit feed

        Example:
        - `[p]redditfeed subscribe <subreddit> <channel>`
        """
        async with self.config.guild(ctx.guild).feeds() as feeds:
            if {"subreddit": subreddit.lower(), "channel_id": channel.id} in feeds:
                error_embed = await self.make_error_embed(ctx, error_type="FeedExists")
                await ctx.send(embed=error_embed)
                return
            feeds.append({"subreddit": subreddit.lower(), "channel_id": channel.id})
            success_embed = discord.Embed(
                title="Subscribed to feed",
                description=f"<#{channel.id}> **-** r/{subreddit.lower()}",
                colour=await ctx.colour(),
            )
            await ctx.send(embed=success_embed)

    @_feed.command(name="unsubscribe")
    async def unsubscribe(self, ctx, subreddit: str, channel: discord.TextChannel):
        """Unsubscribe from a Reddit feed

        Example:
        - `[p]redditfeed unsubscribe <subreddit>`
        """
        async with self.config.guild(ctx.guild).feeds() as feeds:
            if {"subreddit": subreddit.lower(), "channel_id": channel.id} not in feeds:
                error_embed = self.make_error_embed(ctx, error_type="FeedNotFound")
                await ctx.send(embed=error_embed)
                return

            feeds.remove({"subreddit": subreddit.lower(), "channel_id": channel.id})
            success_embed = discord.Embed(
                title="Unsubscribed from feed",
                description=f"<#{channel.id}> **-** r/{subreddit.lower()}",
                colour=await ctx.colour,
            )
            await ctx.send(embed=success_embed)

    # Tasks

    @tasks.loop(seconds=30)
    async def check_subreddits(self):
        """Scan subreddits for new posts and send them to Discord channels"""
        # Wait until the bot is ready
        await self.bot.wait_until_ready()
        if not self.praw:
            # Authenticate if not already authenticated
            await self.authenticate_praw()
        if not await self.bot.get_shared_api_tokens("reddit"):
            # Exit if API keys not set
            return

        # Get seen posts
        seen_posts = await self.get_seen_posts()

        # Unpack guild configs
        all_guild_config = await self.config.all_guilds()
        subreddits = []
        for _, guild_config in all_guild_config.items():
            for feed in guild_config["feeds"]:
                if feed["subreddit"] not in subreddits:
                    subreddits.append(feed["subreddit"])

        # We now have a list of all unique subreddit names
        for subreddit_name in subreddits:
            subreddit = await self.praw.subreddit(subreddit_name, fetch=True)
            # Retrieve list of seen submissions for this subreddit
            subreddit_seen_posts = map(lambda x: x["id"], map(lambda x: x["subreddit"] == subreddit_name, seen_posts))

            # Make a list of channels to send to
            channels = []
            for guild_id, guild_config in all_guild_config.items():
                for feed_channel in map(lambda x: x[""], guild_config["feeds"]):
                    channels.append(
                        {
                            "guild_id": guild_id,
                        }
                    )

            async for submission in subreddit.new(limit=25):
                if submission.id not in subreddit_seen_posts:
                    # Send to channels
                    embed = self.make_reddit_embed(submission)
                    for channel in channels:
                        guild = self.bot.get_guild(channel["guild_id"])
                        channel = guild.get_channel(channel["channel_id"])
                        await channel.send(embed=embed)

        # Old code
        for subreddit in subreddits:
            sub = Subreddit(subreddit)
            posts = await sub.new()
            new_posts = list(filter(lambda x: x not in seen_posts, posts))

            if not new_posts:  # If there are no new posts
                continue

            for guild in all_guild_config:
                guild_subscriptions = [i for i in all_guild_config[guild]["feeds"] if i["subreddit"] == sub.name]
                # Go through the regular feed subscriptions
                for subscription in guild_subscriptions:
                    guild_object = await discord.fetch_guild(guild)
                    channel = await guild_object.fetch_channel(subscription["channel_id"])
                    # Post to Discord channel
                    for post in new_posts:
                        await channel.send(embed=post.embed)

                guild_filtered_subscriptions = [
                    i for i in all_guild_config[guild]["filtered_feeds"] if i["subreddit"] == sub.name
                ]
                # Go through the filtered subscriptions
                async with self.config.seen_posts() as seen_posts:
                    for filtered_subscription in guild_filtered_subscriptions:
                        guild_object = await discord.fetch_guild(guild)
                        channel = await guild_object.fetch_channel(filtered_subscription["channel_id"])
                        # Post to Discord if filter matches
                        for post in new_posts:
                            if (filtered_subscription["filter"]["title"] in post.title.lower()) and (
                                filtered_subscription["filter"]["flair"] is post.flair_text
                            ):
                                msg = await channel.send(embed=post.embed)
                                await self.update_seen_posts(post, msg)

    @tasks.loop(seconds=60)
    async def check_recent_posts(self):
        """Check recently posted posts and edit/remove the discord messages accordingly"""
        if not self.praw:
            return
        if not await self.bot.get_shared_api_tokens("reddit"):
            return

        # Get recent posts
        seen_posts = await self.get_seen_posts()
        for post in seen_posts:

            if post["post"]["content"] == post_data.text:
                continue

        # Check new content against old
        # Continue if identical
        # Remove message if post deleted
        # Edit message if content different

    # Helper functions

    async def authenticate_praw(self, force_auth: bool = False, tokens: dict = None):
        """Create the praw instance"""
        if self.praw_last_auth_time and not force_auth:
            if (dt.now() - self.praw_last_auth_time).total_seconds() < 6000:
                # If the client authenticated within the last 10 minutes
                return

        if not tokens:
            tokens = await self.bot.get_shared_api_tokens("reddit")

        required_keys = {"client_secret", "client_id", "user_agent"}
        if set(tokens) != required_keys:
            for key in tokens:
                if key not in required_keys:
                    raise Exception(f"Asyncpraw failed to authenticate: Unrecognised key in API credentials {key}")
            for key in required_keys:
                if key not in tokens:
                    raise Exception(f"Asyncpraw failed to authenticate: Key missing from API credentials {key}")

        tasks = (self.check_subreddits, self.check_recent_posts)
        for task_loop in tasks:
            if task_loop.is_running():
                task_loop.cancel()

        self.praw = asyncpraw.Reddit(**tokens)

    async def get_seen_posts(self) -> List[dict]:
        """Returns only the submission ids"""
        async with self.config.seen_posts() as seen_posts:
            return seen_posts

    async def get_recent_posts(self, by: str = "") -> dict:
        """Transforms the list of recent posts into a dict with list values"""
        async with self.config.recent_posts() as recent_posts:
            if not recent_posts:
                return {}
            table = {}
            for key in set(i[by] for i in recent_posts):
                table[key] = list(filter(lambda item: item[by] == key, recent_posts))
            return table

    async def update_recent_posts(self, post: asyncpraw.models.Submission, msg: discord.Message):
        async with self.config.recent_posts() as recent_posts:
            recent_posts.append(
                {
                    "guild_id": msg.guild.id,
                    "channel_id": msg.channel.id,
                    "message_id": msg.id,
                    "subreddit": post.subreddit.display_name,
                    "submission_id": post.id,
                }
            )

    async def make_reddit_embed(self, channel: discord.abc.Messageable, post: asyncpraw.models.Submission) -> discord.Embed:
        title = f"[{post.link_flair_text}] {post.title}" if post.link_flair_text else post.title
        description = f"{post.selftext[:253]}..." if len(post.selftext) >= 256 else post.selftext
        post_type = "Self post" if post.is_self else "Link post"
        embed = discord.Embed(
            title=f"[{title}]({post.permalink})",
            description=description,
            colour=await self.bot.get_embed_colour(channel),
            timestamp=dt.fromtimestamp(post.created_at_utc),
        )
        embed.set_footer(text=f"{post_type} by u/{post.author.name}", icon_url="https://reddit.com/favicon.ico")
        return embed
