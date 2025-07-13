#!/usr/bin/env bash -e

# This aligns with the VSCode launch.json config and gitignore
INSTANCE_NAME="RedBot_dev_homelab"
DATA_PATH=".red_data"

echo "This script assumes you have python3 and pip installed on your system. If you don't, please install them before continuing."
echo

read -p "Enter your bot token: " TOKEN
if [ -z "$TOKEN" ]; then
    echo "You must provide a bot token."
    exit 1
fi

read -p "Enter your bot prefix [!]: " PREFIX
PREFIX=${PREFIX:-"!"}

is_venv_sourced=$(python3 -c 'import sys;print(sys.prefix != sys.base_prefix)')
if [ "$is_venv_sourced" = "True" ]; then
    echo "You are already in a virtual environment. If you are not currently using the venv you wish to use for RedBot, please deactivate it."
    read -p "Do you want to continue? [y/N]: " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

echo "Creating and activating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating RedBot instance..."
redbot-setup --instance-name "$INSTANCE_NAME" --no-prompt --data-path $DATA_PATH
redbot "$INSTANCE_NAME" --edit --no-prompt --token "$TOKEN" --prefix "$PREFIX"

echo
echo "Bot setup complete. You can now run the bot using the command 'redbot $INSTANCE_NAME' or by using the launch.json configuration in VSCode for debugging."
echo
echo "Run '${PREFIX}addpath $(dirname $(realpath "$0"))' in a chat with the bot to add this repository to the bot's list of cog paths."
