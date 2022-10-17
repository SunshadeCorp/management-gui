import configparser
from io import BytesIO
from pathlib import Path

import yaml
from fabric import Connection


def get_file(c: Connection, path: str) -> bytes:
    io_obj = BytesIO()
    c.get(path, io_obj)
    return io_obj.getvalue()


def get_config_file(c: Connection, path: str) -> dict:
    result = c.sudo(f'cat {path}', hide=True)
    result = '[DEFAULT_SECTION]\n' + result.stdout
    config = configparser.ConfigParser()
    config.read_string(result)
    return dict(config.items('DEFAULT_SECTION'))


def get_yaml_file(c: Connection, path: str):
    return yaml.safe_load(get_file(c, path))


def get_config_local(filename: Path) -> dict:
    if not filename.exists():
        return {'error': 'file does not exist'}
    with open(filename, 'r') as file:
        try:
            return yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(e)
            return {'error': str(e)}


def save_config_local(filename: Path, config: dict):
    with open(filename, 'w') as file:
        return yaml.dump(config, file, default_flow_style=False, sort_keys=False)
