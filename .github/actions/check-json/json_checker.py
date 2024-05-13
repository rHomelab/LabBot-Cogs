import json
import re
from glob import glob
from typing import List, Tuple, Union

import fastjsonschema


def format_output(*, level: str, file: str, line: int, col: int, message: str) -> str:
    return "::{level} file={file},line={line},col={col}::{message}".format(
        level=level, file=file, line=line, col=col, message=message
    )


def get_json(filename: str) -> Union[dict, list]:
    """Returns an interpreted json file from a filepath"""
    with open(filename, "r") as f:
        return json.load(f)


def validate(schema_name: str, filename: str) -> bool:
    """Validates a json file based on a schema"""
    try:
        schema = get_json(schema_name)
        json_file = get_json(filename)
        fastjsonschema.validate(schema, json_file)
        return True
    except fastjsonschema.exceptions.JsonSchemaValueException as error:
        print(error)

        if error.rule == "additionalProperties" and not error.rule_definition:
            error_keys, msg_bounds = list_from_str(error.message)
            for key in error_keys:
                line, col = get_key_pos(filename, key)
                message = f"{error.message[:msg_bounds[0] + 1]}{key}{error.message[msg_bounds[1] - 1:]}"
                print(format_output(level="error", file=filename, line=line, col=col, message=message))
        else:
            key_name = error.path[1]
            line, col = get_key_pos(filename, key_name)
            print(format_output(level="warning", file=filename, line=line, col=col, message=error.message))
            return False


def get_key_pos(filename: str, key: str) -> Tuple[int, int]:
    """Returns the position of a key in a json file"""
    reg_match = re.compile(f'"{key}"\\s?:')
    with open(filename, "r") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines, start=1):
        match = reg_match.search(line)
        if not match:
            continue
        span = match.span()
        return i, span[0] + 1
    raise Exception(f"could not get position of key: {key}")


def list_from_str(set_str: str) -> Tuple[List[str], Tuple[int, int]]:
    """Returns a list from a string representation of a list"""
    list_reg = re.compile("^.*{(.*)}.*$")
    match = list_reg.match(set_str)
    if not match:
        raise Exception(f"Failed to parse set from string {set_str}")
    to_list = "[" + match.group(1).replace('"', '\\"').replace("'", '"') + "]"
    return json.loads(to_list), match.regs[1]


def main() -> int:
    validation_success: List[bool] = []
    for file_pattern, schema_path in {
        "info.json": ".github/actions/check-json/repo.json",
        "*/info.json": ".github/actions/check-json/cog.json",
    }.items():
        for filename in glob(file_pattern):
            validation_success.append(validate(schema_path, filename))

    return int(not all(validation_success))


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
