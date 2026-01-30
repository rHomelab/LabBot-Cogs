#!/usr/bin/env bash -e

# This aligns with the VSCode launch.json config and gitignore
# Modified to use Python 3.11 (required for Red-DiscordBot)
INSTANCE_NAME="RedBot_dev_homelab"
DATA_PATH=".red_data"

echo "This script uses Python 3.11 (required for Red-DiscordBot compatibility)."
echo

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is not installed. Installing via Homebrew..."
    brew install python@3.11
fi

echo "Using Python 3.11: $(python3.11 --version)"
echo

read -p "Enter your bot token: " TOKEN
if [ -z "$TOKEN" ]; then
    echo "You must provide a bot token."
    exit 1
fi

read -p "Enter your bot prefix [!]: " PREFIX
PREFIX=${PREFIX:-"!"}

is_venv_sourced=$(python3.11 -c 'import sys;print(sys.prefix != sys.base_prefix)')
if [ "$is_venv_sourced" = "True" ]; then
    echo "You are already in a virtual environment. If you are not currently using the venv you wish to use for RedBot, please deactivate it."
    read -p "Do you want to continue? [y/N]: " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

# Check if venv or instance already exists
if [ -d ".venv" ] || [ -d "$DATA_PATH" ]; then
    echo "⚠️  Existing dev bot environment detected."
    echo "This may be from a previous setup or using an incompatible Python version."
    read -p "Do you want to clean up and start fresh? [y/N]: " CLEANUP
    if [ "$CLEANUP" = "y" ]; then
        echo "Cleaning up existing environment..."
        rm -rf .venv "$DATA_PATH"
        redbot-setup delete -y "$INSTANCE_NAME" 2>/dev/null || true
        echo "Cleanup complete!"
    else
        echo "Keeping existing environment. Note: This may cause issues if it was created with a different Python version."
    fi
    echo
fi

echo "Creating and activating virtual environment with Python 3.11..."
python3.11 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements-dev.txt -r requirements.txt

echo "Creating RedBot instance..."
redbot-setup --instance-name "$INSTANCE_NAME" --no-prompt --data-path $DATA_PATH --overwrite-existing-instance
redbot "$INSTANCE_NAME" --edit --no-prompt --token "$TOKEN" --prefix "$PREFIX"

echo
echo "Bot setup complete. You can now run the bot using the command 'redbot $INSTANCE_NAME' or by using the launch.json configuration in VSCode for debugging."
echo
echo "Run '${PREFIX}addpath $(dirname $(realpath "$0"))' in a chat with the bot to add this repository to the bot's list of cog paths."
