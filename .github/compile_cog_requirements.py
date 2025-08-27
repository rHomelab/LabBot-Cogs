"""Pipeline script for extracting imports from cogs"""

import json
from glob import glob


def fetch_requirements() -> set[str]:
    requirements = set()

    for filename in glob("*/info.json"):
        with open(filename, "r") as fp:
            info = json.load(fp)
        if "requirements" in info:
            requirements.update(info["requirements"])

    return requirements


def write_requirements(requirements: set[str]):
    with open("requirements.txt", "w") as fp:
        fp.write("\n".join(sorted(requirements)) + "\n")


if __name__ == "__main__":
    all_requirements = fetch_requirements()
    write_requirements(all_requirements)
    print("Compiled requirements")
