"""Python unittest utility functions."""

import yaml


def get_readonly_yaml_file(file_path) -> dict:
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)
