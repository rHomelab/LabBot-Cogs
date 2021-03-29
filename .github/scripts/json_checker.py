import json
import re
from glob import glob
from typing import Union

import fastjsonschema

OUTPUT = "::{level} file={file},line={line},col={col}::{message}"


def get_json(filename: str) -> Union[dict, list]:
    """Returns an interpreted json file from a filepath"""
    with open(filename, "r") as f:
        return json.load(f)


def validate(schema_name: str, filename: str):
    """Validates a json file based on a schema"""
    schema = get_json(schema_name)
    json_file = get_json(filename)
    fastjsonschema.validate(schema, json_file)


def get_key_pos(filename: str, key: str) -> tuple[int]:
    """Returns the position of a key in a json file"""
    reg_match = re.compile(f'"{key}"\\s?:')
    with open(filename, "r") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines):
        match = reg_match.search(line)
        if not match:
            continue
        span = match.span()
        return (i + 1, span[0] + 1)
    raise Exception(f"could not get position of key: {key}")


def list_from_str(set_str: str) -> set[str]:
    """Returns a list from a string representation of a list"""
    set_reg = re.compile("^.*{(.*)}.*$")
    match = set_reg.match(set_str)
    if not match:
        raise Exception(f"Failed to parse set from string {set_str}")
    to_list = "[" + match.group(1).replace('"', '\\"').replace("'", '"') + "]"
    return json.loads(to_list)


if __name__ == "__main__":
    error_count = 0

    for iterable, schema_path in (("info.json", ".github/schemas/repo.json"), ("*/info.json", ".github/schemas/cog.json")):
        for filename in glob(iterable):
            try:
                validate(schema_path, filename)
            except fastjsonschema.exceptions.JsonSchemaValueException as error:
                if error.rule == "additionalProperties" and error.rule_definition == False:
                    error_keys = list_from_str(error.message)
                    if len(error_keys) > 1:
                        line, col = (1, 1)
                    else:
                        line, col = get_key_pos(filename, error_keys[0])
                    print(OUTPUT.format(level="error", file=filename, line=line, col=col, message=error.message))
                else:
                    key_name = error.path[-1]
                    line, col = get_key_pos(filename, key_name)
                    print(OUTPUT.format(level="warning", file=filename, line=line, col=col, message=error.message))

    exit(1) if error_count else exit(0)
