"""Python unittest utility functions."""

import csv
import json

import yaml


def get_readonly_yaml_file(file_path) -> dict:
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_readonly_csv_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def get_readonly_json_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        return json.load(file)
