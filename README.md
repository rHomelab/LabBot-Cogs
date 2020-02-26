# LabBot Cogs

Cogs for the [RED](https://github.com/Cog-Creators/Red-DiscordBot/)-based [Homelab](https://reddit.com/r/Homelab) Discord server bot.

## Table of Contents

- [Authors](#authors)
- [Cog Summaries](#cog-summaries)
- [Cog Documentation](#cog-documentation)
  - [Cog 1](#cog1)
  - [Purge](#purge)
- [License](#license)

## Authors

This is a joint project involving any of the Homelab Discord server admins & moderators that would like to get involved.

**Admins:**

[tigattack](https://github.com/tigattack), [MonsterMuffin](https://github.com/monstermuffin), [Sneezey](https://github.com/kdavis)

**Moderators:**

[DanTho](https://github.com/dannyt66)

## Cog Summaries

- **Cog 1:** Summary of cog 1.
- **[Purge](#purge):** This will purge users based on criteria.

## Cog Documentation

### Cog 1

In-depth documentation/explanation of Cog 1, what it can do, what it can't do, and, if necessary, what it's used for.

### Purge

This cog will purge users that hold no roles as a way to combat accounts being created and left in an un-verified state.

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
