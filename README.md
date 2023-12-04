# LabBot Cogs

<p align="center">
  <img src=LabBot.png width="256" height="256">
</p>
<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/rhomelab/labbot-cogs/ci.yml?style=for-the-badge">
<p>

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [LabBot Cogs](#labbot-cogs)
  - [Table of Contents](#table-of-contents)
  - [Contributors](#contributors)
    - [Moderation Team](#moderation-team)
    - [Other](#other)
  - [Cog Summaries](#cog-summaries)
  - [Cog Documentation](#cog-documentation)
    - [AutoReact](#autoreact)
    - [AutoReply](#autoreply)
    - [BetterPing](#betterping)
    - [Convert](#convert)
    - [Custom-msg](#custom-msg)
    - [Enforcer](#enforcer)
      - [Configure Enforcer](#configure-enforcer)
    - [Feed](#feed)
    - [Google](#google)
    - [Latex](#latex)
    - [Letters](#letters)
    - [Markov](#markov)
      - [User commands](#user-commands)
      - [Mod Commands](#mod-commands)
      - [Owner Commands](#owner-commands)
    - [Notes](#notes)
    - [Penis](#penis)
    - [Phishingdetection](#phishingdetection)
    - [Purge](#purge)
    - [Quotes](#quotes)
    - [Reactrole](#reactrole)
    - [Report](#report)
    - [Roleinfo](#roleinfo)
    - [Sentry](#sentry)
    - [Tags](#tags)
    - [prom\_export](#prom_export)
    - [Timeout](#timeout)
    - [Topic](#topic)
    - [Verify](#verify)
    - [xkcd](#xkcd)
  - [License](#license)
  - [Contributing](#contributing)
    - [Linting your code](#linting-your-code)
    - [Making changes](#making-changes)

## Contributors

This is a joint project involving any of the [Homelab Discord](https://discord.gg/homelab) admins, moderators, and community members that would like to get involved.

A number of people have contributed to this project: Members of the moderation team, former members of the moderation team, and members of the wider community.

A massive thank you to all who've helped out with this project ❤️

### Moderation Team

- [portalBlock](https://github.com/portalBlock)
- [tigattack](https://github.com/tigattack)

### Other

- [BeryJu](https://github.com/BeryJu)
- [DanTho](https://github.com/dannyt66)
- [Darkflame72](https://github.com/Darkflame72)
- [Hugh Mungus (the1337g33k)](https://github.com/the1337g33k)
- [Issy](https://github.issy.dev)
- [McTwist](https://github.com/McTwist)
- [ripple](https://github.com/rippleFCL)
- [Sneezey](https://github.com/kdavis)
- [TheDevFreak](https://github.com/TheDevFreak)
- [s33g](https://github.com/s33g)

## Cog Summaries

- **[AutoReact](#autoreact):** React to specific phrases with one or more emotes.
- **[AutoReply](#autoreply):** Automatically replies to messages that match a trigger phrase.
- **[BetterPing](#betterping):** Outputs the current channel topic as a message in the channel.
- **[Convert](#convert):** Converts any unit to any another unit.
- **[Custom-msg](#custom-msg):** Allows moderators to send/edit messages from the bot.
- **[Enforcer](#enforcer):** Allows you to enforce certain characteristics on a channel.
- **[Feed](#feed):** This allows users to feed each other.
- **[Google](#google):** Send a google link to someone.
- **[LaTeX](#latex):** Render a LaTeX statement.
- **[Letters](#letters):** Outputs large emote letters/numbers from input text.
- **[Notes](#notes):** Manage notes and warnings against users.
- **[Penis](#penis):** Allows users to check the size of their penis.
- **[prom_export](#prom_export):** Exposes a HTTP endpoint for exporting guild metrics in Prometheus format
- **[Purge](#purge):** This will purge users based on criteria.
- **[Quotes](#quotes):** Allows users to quote other users' messages in a quotes channel.
- **[Reactrole](#reactrole):** Allows roles to be applied and removed using reactions.
- **[Report](#report):** Allows users to report issues.
- **[Roleinfo](#roleinfo):** Displays info on a role
- **[Sentry](#sentry):** Send unhandled errors to sentry.
- **[Tags](#tags):** Allow user-generated stored messages.
- **[Timeout](#timeout):** Manage users' timeout status.
- **[Topic](#topic):** Outputs the current channel topic as a message in the channel.
- **[Verify](#verify):** Allows users to verify themselves.
- **[xkcd](#xkcd):** Allows users to look at xkcd comics.

## Cog Documentation

### AutoReact

This cog allows mods to add auto reactions to certain phrases.

`[p]autoreact`

### AutoReply

This cog automatically responds to messages that match specific trigger phrases, set by admins.

`[p]autoreact`

### BetterPing

This cog is an upgraded version of the built-in ping command showing some latency information. It will override the built-in ping command when loaded, but reinstate it once when loaded.

It was inspired by [Vexed01's AnotherPingCog](https://cogdocs.vexcodes.com/en/latest/cogs/anotherpingcog.html), but it's slimmed down and not as snazzy.

`[p]ping`

### Convert

Converts any unit to any another unit.

`[p]convert`

### Custom-msg

Allows moderators to send/edit messages from the bot.

```
[p]msg create
[p]msg edit
```

### Enforcer

This cog allows you to enforce certain characteristics on a channel.

`[p]enforcer`

There are numerous attributes than can be used to restrict messages/content into a channel.

While some attributes are available in discord via role-based permissions, sometimes a bot may be better off enforcing content in a pinch.

#### Configure Enforcer

`[p]enforcer configure <channel> <attribute> [value]`

Example:

- `[p]enforcer configure #channel enabled true`

| Attribute           | Type   | Description                                                                                                      |
| ------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| `enabled`           | `bool` | Whether to enable enforcements on a channel                                                                      |
| `minchars`          | `int`  | The minimum number of characters a message must contain to be allowed into the channel                           |
| `maxchars`          | `int`  | The maximum number of characters a message may contain to be allowed into the channel                            |
| `notext`            | `bool` | The sent message must have _no_ text, i.e. should be an image-only message                                       |
| `requiremedia`      | `bool` | The sent message must contain an attached image                                                                  |
| `nomedia`           | `bool` | The sent message must **not** contain an attached image                                                          |
| `minimumguildage`   | `int`  | How old a server member must be part of the guild, in seconds, before they are able to contribute to the channel |
| `minimumdiscordage` | `int`  | How old a member's discord account must be, in seconds, before they are able to contribute to the channel        |

An example enforcement would be a channel to show off server pictures.
In which case, you could allow members to post a set of images with a description of their setup.

In which case, the following would be appropriate

```
[p]enforcer logchannel #admin-log
[p]enforcer configure #serverpics requiremedia true
[p]enforcer configure #serverpics minimumguildage 600
[p]enforcer configure #serverpics minchars 20
[p]enforcer configure #serverpics maxchars 300
[p]enforcer configure enabled true
```

### Feed

This cog allows users to feed each other.

### Google

This cog allows users to send google links to each other.

`[p]google <query>`

### Latex

This cog allows users to display complex mathematical information using LaTeX renderings.

`[p]latex <latex statement>`

### Letters

This cog converts a string of letters/numbers into large emote letters ("regional indicators") or numbers.
`-raw` flag can be used to output raw emote code.

`[p]letters I would like this text as emotes 123`
`[p]letters -raw I would like this text as raw emote code 123`

### Markov

This cog generates messages based on markov chains generated per-user.

User messages will never be analysed unless the user explicitly opts in.
It must also be enabled per-channel: `[p]markov channelenable`

#### User commands

- `[p]markov generate` - Generate text based on user language models.
- `[p]markov enable` - Allow the bot to model your messages and generate text.
- `[p]markov disable` - Disallow the bot from model;ing your messages or generating text.
- `[p]markov mode` - Set the tokenization mode for model building.
- `[p]markov depth` - Set the modelling depth (the "n" in "ngrams").
- `[p]markov show_user` - Show your current settings and models, or those of another user.
- `[p]markov delete` - Delete a specific model from your profile.
- `[p]markov reset` - Remove all language models from your profile.

#### Mod Commands

- `[p]markov show_guild` - Show current guild settings.
- `[p]markov channelenable` - Allow language modelling on messages in a given channel.
- `[p]markov channeldisable` - Disallow language modelling on messages in a given channel.

#### Owner Commands

- `[p]markov show_global [guild_id]` - Show global summary info or summary of `guild_id`.

### Notes

Manage notes and warnings against users.

`[p]notes`
`[p]warnings`

Notes can be used for long-term storage information of problematic users or for future reference.

When listing the notes of a user, the warnings will be prioritised as they will be deemed more important.

It is possible to add notes to a user who has left or not yet joined. Notes are stored against a user's ID and do not require the user to be part of the server.
Deleting a note does not actually delete the note. It simply marks it in the datastore as deleted and does not show it in normal use. This can allow future recovery of notes (using the `restore` subcommand) if a bad party is attempting to wipe existing notes.

Notes and warnings can be edited using the `edit` subcommand.

### Penis

This cog allows users to check the size of their penis.

`[p]penis <user>`

### Phishingdetection

This cog automatically deletes any messages containing suspected phishing/scam links. This information is sourced from [phish.sinking.yachts](https://phish.sinking.yachts/)

### Purge

This cog will purge users that hold no roles as a way to combat accounts being created and left in an un-verified state.

`[p]purge`

- `[p]purge schedule "0 */6 * * *"` - It is possible to run the purge on a schedule. By default, it is **disabled**, but configured for `0 */6 * * *` which is a crontab for every 6 hours. E.g. will run at `00:00`, `06:00`, `12:00` and `18:00` every day.

- `[p]purge minage 5` It will attempt to prune users that hold _no_ roles, that have been part of the server for at least `<minage>` days (default to 5). `<minage>` can be altered to fit your server's requirements to ensure that people that joined but never verified, are not clogging up mention lists and to keep activity ratios high.

By default, purge's schedule is disabled and must be enabled to prune unverified users.

- `[p]purge simulate` - It's possible to do a simulated purge by running `[p]purge simulate`. This will retrieve the list of users it would prune, had it run as normal. This allows moderators to test out configuration without performing any permanent actions.

- `[p]purge exclude @Sneezey#2695` - If a user does not hold any roles for any reason, but you wish to exclude them from the purge, it is possible to add this user to the `exclude` list. This action can also be undone with the `include` subcommand.

- `[p]purge status` - To check how many users have been purged any other configuration items, the status command allows you to see the values in an easy-to-see embed.

### Quotes

This cog will allow members to add quotes to the quotes channel easily.

`[p]quote`

### Reactrole

Allows roles to be applied and removed using reactions.

`[p]reactrole`

### Report

This cog will allow members to send a report into a channel where it can be reviewed and actioned upon by moderators.

- `[p]reports logchannel #admin-log` - For reports to be able to be taken, a log channel must be set which will receive an embed upon a user using the report command.

- `[p]reports channel [allow|deny] [channel]` - Disallow the `report`/`emergency` commands to be used in certain channels

- `[p]reports confirm [true|false]` - When a report is issued, this sets whether the bot will DM the user with confirmation or not

- `[p]report [message]` - A report can be sent to the logchannel for any moderators to see and action upon when they are ready.

- `[p]emergency [message]` - An emergency can be requested which will ping all members in the configured logchannel if they are online.

### Roleinfo

Allows you to view info on a role

- `[p]roleinfo <role>`

### Sentry

Send unhandled errors and performance metrics to sentry.

Configure Sentry DSN using `[p]set api sentry dsn,https://fooo@bar.baz/9`, then load the Cog `[p]load sentry`.

- `[p]sentry get_log_level` - Get the current log level.
- `[p]sentry set_log_level` - Set the desired log level, must be one of `error`, `warning`, `info` or `debug`. Does not require a reload.
- `[p]sentry get_env` - Returns the currently configured Sentry environment.
- `[p]sentry set_env` - Set the currently configured Sentry environment. Requires a reload of the cog.
- `[p]sentry test` - Raise a test exception to test the Sentry connection.

### Tags

Allow user-generated stored messages to be triggered upon configurable tags. Aliases can also be created to make
accessing information even quicker. Users can transfer tag ownership between themselves and even claim ownership of
abandoned tags. Ever use of a tag or alias is tracked. Same with ownership transfers of any kind. Statistics and
searching have not yet been implemented.

- `[p]tag <tag>` - Triggers the specified tag.
- `[p]tag search <query>` - Searches for a tag or alias (WIP).
- `[p]tag create <tag> <content>` - Creates the specified tag which will reply with the provided content when triggered.
- `[p]tag stats [user]` - Provides general stats about the tag system, or if a user is provided, about that user (WIP).
- `[p]tag info <tag>` - Provides info about the tag such as its creator, date of creation, etc. (WIP).
- `[p]tag edit <tag> <content>` - Updates the content of the specified tag.
- `[p]tag delete <tag>` - Deletes the specified tag.
- `[p]tag claim <tag>` - Allows the runner to claim ownership of the tag if the current owner is not in the guild.
- `[p]tag transfer <tag> <user>` - Transfers ownership of the specified tag to the specified user.
- `[p]tag alias create <alias> <tag>` - Creates the specified alias to the specified tag.
- `[p]tag alias delete <alias>` - Deletes the specified alias.

### prom_export

This cog exposes a HTTP endpoint for exporting guild metrics in Prometheus format.

- `[p]prom_exporter set_port <port>` - Set the port the HTTP server should listen on
- `[p]prom_exporter set_address <address>` - Sets the bind address (IP) of the HTTP server
- `[p]prom_exporter set_poll_interval <interval>` - Set the metrics poll interval (seconds)
- `[p]prom_exporter config` - Show the current running config


### Timeout

Manage the timeout status of users.

Run the command to add a user to timeout, run it again to remove them. Append a reason if you wish: `[p]timeout @someUser said a bad thing`
If the user is not in timeout, they are added. If they are in timeout, they are removed.
All of the member's roles will be stripped when they are added to timeout, and re-added when they are removed.

- `[p]timeout <user> [reason]` - Add/remove a user from timeout, optionally specifying a reason.
- `[p]timeoutset list` - Print the current configuration.
- `[p]timeoutset role <role name>` - Set the timeout role.
- `[p]timeoutset report <bool>` - Set whether timeout reports should be logged or not.
- `[p]timeoutset logchannel <channel>` - Set the log channel.

### Topic

Shows the current channel topic as a message in the channel.

Channel topics are notoriously hard for users to see.  It's in a not so obvious place in the desktop UI and it's not possible to see in the mobile UI unless you are looking at the memberlist.  Topic allows users to easily view the current channel topic or use it to remind other users in the channel what the topic currently is.

- `[p]topic` - Prints the current channel topic. Output message format: `#channel: topic`
- `/topic` - Same as above but implemented as a discord slash command.

### Verify

This cog will allow users to prove they're not a bot by having to read rules and complete an action. They will then be given the verified role if they can complete this.

- `[p]verify block <user>` - Add the specified user to the verification blocklist.
- `[p]verify channel <channel>` - Set the channel in which the cog listens for verification attemps.
- `[p]verify logchannel <channel>` - Set the channel in which the cog logs verification attemps.
- `[p]verify message <message>` - Set the verification string (e.g. `I agree to the rules`.
- `[p]verify role <role>` - Set the role to which users are added upon successful verification.

Further configuration options can be seen with `[p]verify help`

### xkcd

This cog allows users to look at xkcd comics

`[p]xkcd <comicnumber>`

## License

All code in this repository is licensed under the [GNU General Public License version 3](https://github.com/rHomelab/LabBot-Cogs/blob/main/LICENSE).

Copyright (c) 2018-2023 tigattack, contributors and original authors.

## Contributing

### Linting your code

The CI will fail unless your code is [PEP8](https://www.python.org/dev/peps/pep-0008/) compliant.

```bash
pip install -r requirements-ci.txt
isort . # This will fix the order of imports
black . # This will auto-format and fix a lot of common mistakes
pylint * # This will show general pep8-violations
```

If you use [VSCode](https://code.visualstudio.com/) you can use the tasks integrated into the repo to locally run the same tasks as our CI

### Making changes

When suggesting changes, please [open an issue](https://github.com/rHomelab/LabBot-Cogs/issues/new/choose) so it can be reviewed by the team who can then suggest how and if the idea is to be implemented.

When submitting changes, please [create a pull request](https://github.com/rHomelab/LabBot-Cogs/compare) targeting the main branch.

