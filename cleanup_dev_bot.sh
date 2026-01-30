#!/usr/bin/env bash

# Cleanup script for dev bot environment
INSTANCE_NAME="RedBot_dev_homelab"
DATA_PATH=".red_data"

echo "This will remove the dev bot instance and virtual environment."
read -p "Are you sure you want to continue? [y/N]: " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo "Removing virtual environment..."
rm -rf .venv

echo "Removing data directory..."
rm -rf "$DATA_PATH"

echo "Attempting to delete Red instance from config..."
redbot-setup delete -y "$INSTANCE_NAME" 2>/dev/null || echo "Instance not found in redbot config (this is fine)"

echo
echo "Cleanup complete! You can now run ./create_dev_bot_py311.sh to start fresh."
