"""Pipeline script for extracting imports from cogs"""

import json
from glob import glob


def fetch_requirements() -> tuple[set[str], int]:
    requirements = set()
    cogs_with_requirements = 0

    for filename in glob("*/info.json"):
        with open(filename, "r") as fp:
            info = json.load(fp)
        if "requirements" in info:
            requirements.update(info["requirements"])
            cogs_with_requirements += 1

    return requirements, cogs_with_requirements


def write_requirements(requirements: set[str]):
    with open("requirements.txt", "w") as fp:
        fp.write("\n".join(sorted(requirements)) + "\n")


if __name__ == "__main__":
    all_requirements, cog_count = fetch_requirements()
    write_requirements(all_requirements)
    print(f"Compiled {len(all_requirements)} requirements from {cog_count} cogs")
