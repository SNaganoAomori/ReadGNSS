import os
from typing import NamedTuple

import yaml

dir_name = os.path.dirname(__file__)
file_path = os.path.join(dir_name, 'test\\test.yaml')

global CONFIG
with open(file_path, mode='r', encoding='utf-8') as f:
    CONFIG = yaml.load(f, Loader=yaml.FullLoader)


def _convert_none_string(data: dict) -> dict:
    new_data = {}
    for key, value in data.items():
        if value == 'None':
            new_data[key] = None
        else:
            new_data[key] = value
    return new_data

class TestData(NamedTuple):
    _DrgWayPoint__read_coords = CONFIG['_DrgWayPoint']['read_coords']['data']
    _modelling = _convert_none_string(CONFIG['_modelling']['data'])
    original_data_to = _convert_none_string(CONFIG['original_data_to']['data'])

class Answer(NamedTuple):
    _DrgWayPoint__read_coords = CONFIG['_DrgWayPoint']['read_coords']['answer']
    _DrgWayPoint__read_items = CONFIG['_DrgWayPoint']['read_items']['answer']
    _modelling = _convert_none_string(CONFIG['_modelling']['answer'])
    original_data_to = _convert_none_string(CONFIG['original_data_to']['answer'])


