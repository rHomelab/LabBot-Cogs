# LabBot Cogs

<img src=LabBot.png width="256" height="256">

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [Authors](#authors)
- [Cog Summaries](#cog-summaries)
- [Cog Documentation](#cog-documentation)
  - [Purge](#purge)
  - [Verify](#verify)
  - [Report](#report)
  - [Quotes](#quotes)
- [License](#license)

## Authors

This is a joint project involving any of the [Homelab Discord](https://discord.gg/homelab) admins & moderators that would like to get involved.

### Contributors

#### Admins

* [tigattack](https://github.com/tigattack)
* [Sneezey](https://github.com/kdavis)

#### Moderators

* [DanTho](https://github.com/dannyt66)

#### Other

## Cog Summaries

- **[Purge](#purge):** This will purge users based on criteria.
- **[Verify](#verify):** Allows users to verify themselves
- **[Report](#report):** Allows users to report issues
- **[Quotes](#quotes):** Allows users to quote other users' messages in a quotes channel.

## Cog Documentation

### Verify

This cog will allow users to prove they're not a bot by having to read rules and complete an action. They will then be given the verified role if they can complete this.

### Purge

This cog will purge users that hold no roles as a way to combat accounts being created and left in an un-verified state.

### Purge

This cog will purge users that hold no roles as a way to combat accounts being created and left in an un-verified state.

### Report

This cog will allow members to send a report into a channel where it can be reviewed and actioned upon by moderators.

### Quotes

This cog will allow members to add quotes to the quotes channel easily.

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
