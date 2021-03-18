from glob import glob
from json import loads


with open("requirements.txt", "r") as f:
    requirements = [i for i in f.read().split("\n") if i]


for filename in glob("*/info.json"):
    with open(filename, "r") as f:
        info = loads(f.read())
    if 'REQUIREMENTS' in info:
        requirements.extend(info['REQUIREMENTS'])


with open("requirements.txt", "w") as f:
    f.writelines("\n".join(requirements))
