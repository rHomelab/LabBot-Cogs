"""Pipeline script for extracting imports from cogs"""

import json
from glob import glob
from typing import Set


def fetch_requirements() -> Set[str]:
    requirements = set()

    for filename in glob("*/info.json"):
        with open(filename, "r") as fp:
            info = json.load(fp)
        if "requirements" in info:
            requirements.update(info["requirements"])

    return requirements


def write_requirements(requirements: Set[str]):
    with open("requirements-cogs.txt", "a") as fp:
        fp.write("\n".join(requirements))


if __name__ == "__main__":
    all_requirements = fetch_requirements()
    write_requirements(all_requirements)
    print("Compiled requirements")
