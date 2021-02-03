# LabBot Cogs

<img src=LabBot.png width="256" height="256">

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [Contributors](#Contributors)
- [Cog Summaries](#cog-summaries)
- [Cog Documentation](#cog-documentation)
  - [AutoReact](#autoreact)
  - [AutoReply](#autoreply)
  - [Convert](#convert)
  - [Enforcer](#autoreply)
  - [Feed](#feed)
  - [Google](#google)
  - [Notes](#notes)
  - [Penis](#penis)
  - [Purge](#purge)
  - [Quotes](#quotes)
  - [Reactrole](#reactrole)
  - [Report](#report)
  - [Verify](#verify)
  - [xkcd](#xkcd)
- [License](#license)

## Contributors

This is a joint project involving any of the [Homelab Discord](https://discord.gg/homelab) admins, moderators, and community members that would like to get involved.

A number of people have contributed to this project: Members of the moderation team, former members of the moderation team, and members of the wider community.

A massive thank you to all who've helped out with this project ❤️

### Moderation Team

* [tigattack](https://github.com/tigattack)
* [Issy](https://github.issy.dev)
* [portalBlock](https://github.com/portalBlock)

### Other
* [Sneezey](https://github.com/kdavis)
* [DanTho](https://github.com/dannyt66)
* [BeryJu](https://github.com/BeryJu)
* [TheDevFreak](https://github.com/TheDevFreak)
* [McTwist](https://github.com/McTwist)

## Cog Summaries

- **[AutoReact](#autoreact):** React to specific phrases with one or more emotes.
- **[AutoReply](#autoreply):** Automatically replies to messages that match a trigger phrase.
- **[Convert](#convert):** Converts any unit to an another unit.
- **[Enforcer](#enforcer):** Allows you to enforce certain characteristics on a channel.
- **[Feed](#feed):** This allows users to feed each other.
- **[Google](#google):** Send a google link to someone.
- **[LaTeX](#latex):** Render a LaTeX statement. 
- **[Notes](#notes):** Manage notes and warnings against users.
- **[Penis](#penis):** Allows users to check the size of their penis.
- **[Purge](#purge):** This will purge users based on criteria.
- **[Quotes](#quotes):** Allows users to quote other users' messages in a quotes channel.
- **[Reactrole](#reactrole):** Allows roles to be applied and removed using reactions.
- **[Report](#report):** Allows users to report issues.
- **[Verify](#verify):** Allows users to verify themselves.
- **[xkcd](#xkcd):** Allows users to look at xkcd comics.

## Cog Documentation

### AutoReact

This cog allows mods to add auto reactions to certain phrases.

`[p]autoreact`

### AutoReply

This cog automatically responds to messages that match specific trigger phrases, set by admins.

`[p]autoreact`

### Convert

Converts any unit to an another unit.

`[p]convert`

### Enforcer

This cog allows you to enforce certain characteristics on a channel.

`[p]enforcer`

### Feed

This cog allows users to feed each other.

### Google
This cog allows users to send google links to each other.

`[p]google <query>`

### Latex

This cog allows users to display complex mathematical information using LaTeX renderings.

`[p]latex <latex statement>`

### Notes

Manage notes and warnings against users.

`[p]notes`
`[p]warnings`

### Penis

This cog allows users to check the size of their penis.

`[p]penis <user>`

### Purge

This cog will purge users that hold no roles as a way to combat accounts being created and left in an un-verified state.

`[p]purge`

### Quotes

This cog will allow members to add quotes to the quotes channel easily.

`[p]quote`

### Reactrole

Allows roles to be applied and removed using reactions.

`[p]reactrole`

### Report

This cog will allow members to send a report into a channel where it can be reviewed and actioned upon by moderators.

`[p]report`

### Verify

This cog will allow users to prove they're not a bot by having to read rules and complete an action. They will then be given the verified role if they can complete this.

`[p]verify`

### xkcd

This cog allows users to look at xkcd comics

`[p]xkcd <comicnumber>`

## License

All code in this repository is licensed under the [GNU General Public License version 3](https://github.com/tigattack/LabBot/blob/master/LICENSE).

Copyright (c) 2018-2020 tigattack, contributors and original authors.

## Contributing

### Linting your code

The CI will fail unless your code is [PEP8](https://www.python.org/dev/peps/pep-0008/) complient

```bash
pip install -r requirements-ci.txt
isort . # This will fix the order of imports
black . # This will auto-format and fix a lot of common mistakes
pylint * # This will show general pep8-violations
```

### Making changes

When suggesting changes, please [open an issue](https://gitlab.com/homelab-mods/LabBot/-/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=) so it can be reviewed by the team who can then suggest how and if the idea is to be implmented.
When submitting changes, please [create a merge request](https://gitlab.com/homelab-mods/LabBot/-/merge_requests/new) targetting the develop branch.
