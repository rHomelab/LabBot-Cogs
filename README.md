# LabBot Cogs

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [Authors](#authors)
- [Cog Summaries](#cog-summaries)
- [Cog Documentation](#cog-documentation)
  - [Purge](#purge)
  - [Verify](#verify)
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
* **Cog 1:** Summary of cog 1.

## Cog Documentation
### Cog 1
In-depth documentation/explanation of Cog 1, what it can do, what it can't do, and, if necessary, what it's used for.

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
When suggesting changes, please [open an issue](https://gitlab.com/homelab-mods/LabBot/-/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=) so it can be reviewed by the team.  
When submitting changes, please [create a merge request](https://gitlab.com/homelab-mods/LabBot/-/merge_requests/new) targetting the develop branch.