# LabBot Cogs

<img src=LabBot.png width="256" height="256">

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [Authors](#authors)
- [Cog Summaries](#cog-summaries)
- [Cog Documentation](#cog-documentation)
  - [AutoReact](#autoreact)
  - [AutoReply](#autoreply)
  - [Enforcer](#autoreply)
  - [Feed](#feed)
  - [Notes](#notes)
  - [Purge](#purge)
  - [Quotes](#quotes)
  - [Reactrole](#reactrole)
  - [Report](#report)
  - [Verify](#verify)
- [License](#license)

## Authors

This is a joint project involving any of the [Homelab Discord](https://discord.gg/homelab) admins, moderators, and community members that would like to get involved.

### Contributors

#### Admins

* [tigattack](https://github.com/tigattack)
* [Sneezey](https://github.com/kdavis)

#### Moderators

* [DanTho](https://github.com/dannyt66)

#### Other

* [Issy](https://github.issy.dev)

## Cog Summaries

- **[AutoReact](#autoreact):** React to specific phrases with one or more emotes.
- **[AutoReply](#autoreply):** Automatically replies to messages that match a trigger phrase.
- **[Enforcer](#enforcer):** Allows you to enforce certain characteristics on a channel.
- **[Feed](#feed):** This allows users to feed each other.
- **[Notes](#notes):** Manage notes and warnings against users.
- **[Purge](#purge):** This will purge users based on criteria.
- **[Quotes](#quotes):** Allows users to quote other users' messages in a quotes channel.
- **[Reactrole](#reactrole):** Allows roles to be applied and removed using reactions.
- **[Report](#report):** Allows users to report issues.
- **[Verify](#verify):** Allows users to verify themselves.

## Cog Documentation

### AutoReact

This cog allows mods to add auto reactions to certain phrases.

`[p]autoreact`

### AutoReply

This cog automatically responds to messages that match specific trigger phrases, set by admins.

`[p]autoreact`

### Enforcer

This cog allows you to enforce certain characteristics on a channel.

`[p]enforcer`

### Feed

This cog allows users to feed each other.

`[p]feed <user>`

### Notes

Manage notes and warnings against users.

`[p]notes`
`[p]warnings`

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

## License

All code in this repository is licensed under the [GNU General Public License version 3](https://github.com/tigattack/LabBot/blob/master/LICENSE).

Copyright (c) 2018-2020 tigattack, contributors and original authors.

## Contributing

### Setting up Flake8 pre-commit hook

This will reject the commit unless the code passes flake8 standards.

```bash
pip install flake8
flake8 --install-hook git
git config --bool flake8.strict true
```

### Making changes

When suggesting changes, please [open an issue](https://gitlab.com/homelab-mods/LabBot/-/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=) so it can be reviewed by the team who can then suggest how and if the idea is to be implmented.
When submitting changes, please [create a merge request](https://gitlab.com/homelab-mods/LabBot/-/merge_requests/new) targetting the develop branch.
