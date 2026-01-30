# Python Version Compatibility Note

## Issue

Red-DiscordBot currently supports **Python 3.8.1 to 3.11** only.

Your system has Python 3.14.2 as the default, which is too new for Red-DiscordBot.

## Solution

Python 3.11 has been installed via Homebrew and a modified setup script has been created.

## Usage

Use `create_dev_bot_py311.sh` instead of `create_dev_bot.sh`:

```bash
./create_dev_bot_py311.sh
```

This script will:
- Use Python 3.11 specifically
- Create a virtual environment with the correct Python version
- Install all dependencies compatible with Red-DiscordBot

## Verification

After setup, verify the Python version in the virtual environment:

```bash
source .venv/bin/activate
python --version  # Should show Python 3.11.14
```

## Why This Matters

Red-DiscordBot has specific dependencies that are only compatible with Python 3.8-3.11. Using Python 3.12+ will result in installation errors like:

```
ERROR: Could not find a version that satisfies the requirement Red-DiscordBot>=3.5.0
```

## Future Updates

When Red-DiscordBot adds support for Python 3.12+, you can switch back to using the default `create_dev_bot.sh` script.
