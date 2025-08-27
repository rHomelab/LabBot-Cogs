#!/usr/bin/env bash
set -euo pipefail

PACKAGE="Red-DiscordBot"

# Fetch requires_python string, e.g. ">=3.9,<3.13"
REQUIRES=$(curl -s "https://pypi.org/pypi/${PACKAGE}/json" | jq -r '.info.requires_python')

# Extract lower and upper bounds
LOWER=$(grep -oP '(?<=\>=)[0-9]+\.[0-9]+' <<<"$REQUIRES" || true)
UPPER=$(grep -oP '(?<=\<)[0-9]+\.[0-9]+' <<<"$REQUIRES" | head -n1 || true)

# Get all active Python versions from endoflife.date API
VERSIONS=$(curl -s https://endoflife.date/api/python.json | jq -r '.[].latest' | cut -d. -f1,2 | sort -Vu)

# Filter by lower/upper bounds
SUPPORTED=$(echo "$VERSIONS" | while read v; do
    if [[ -n "$LOWER" && "$(printf '%s\n' "$v" "$LOWER" | sort -V | head -n1)" != "$LOWER" ]]; then
        continue
    fi
    if [[ -n "$UPPER" && "$(printf '%s\n' "$v" "$UPPER" | sort -V | head -n1)" == "$UPPER" ]]; then
        continue
    fi
    echo "$v"
done)

LATEST=$(echo "$SUPPORTED" | sort -V | tail -n1)

echo "$LATEST"
