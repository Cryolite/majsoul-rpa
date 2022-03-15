#!/usr/bin/env python3

from pathlib import Path
from typing import (Union,)
import yaml
import jsonschema


_S3_AUTHENTICATION_SCHEMA = {
    'type': 'object',
    'required': [
        'method',
        'email_address',
        'bucket_name',
        'key_prefix',
    ],
    'properties': {
        'method': {
            'const': 's3',
        },
        'email_address': {
            'type': 'string',
        },
        'bucket_name': {
            'type': 'string',
        },
        'key_prefix': {
            'type': 'string',
        },
    },
    'additionalProperties': {
        'aws_profile': {
            'type': 'string',
        },
    },
}


_AUTHENTICATION_SCHEMA = {
    'oneOf': [
        _S3_AUTHENTICATION_SCHEMA,
    ],
}


_SINGLE_CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'authentication',
    ],
    'proprties': {
        'authentication': _AUTHENTICATION_SCHEMA,
    },
    'additionalProperties': True,
}


_LIST_CONFIG_SCHEMA = {
    'type': 'array',
    'minItems': 1,
    'items': {
        'type': 'object',
        'required': [
            'name',
            'authentication',
        ],
        'properties': {
            'name': {
                'type': 'string',
            },
            'authentication': _AUTHENTICATION_SCHEMA,
        },
        'additionalProperties': True,
    },
}


_CONFIG_SCHEMA = {
    'oneOf': [
        _SINGLE_CONFIG_SCHEMA,
        _LIST_CONFIG_SCHEMA,
    ],
}


_CONFIG = None


def get_config(path: Union[str, Path]) -> object:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise RuntimeError(f'{path}: Does not exist.')
    if not path.is_file():
        raise RuntimeError(f'{path}: Not a file.')

    with open(path) as f:
        config = yaml.load(f, Loader=yaml.Loader)
    jsonschema.validate(config, _CONFIG_SCHEMA)

    if not isinstance(config, list):
        _CONFIG = config
        return config

    if len(config) == 1:
        _CONFIG = config[0]
        return config[0]

    config_names = set()
    for c in config:
        name = c['name']
        if name in config_names:
            raise RuntimeError(f'{name}: A duplicate config name.')
        config_names.add(name)
    for i, c in enumerate(config):
        name = c['name']
        print(f'{i}: {name}')
    print('')
    while True:
        selection = input('Which configuration to use?: ')
        selection = int(selection)
        if selection < len(config):
            _CONFIG = config[selection]
            return config[selection]
