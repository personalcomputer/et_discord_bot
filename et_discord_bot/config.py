import collections
import json

from json_minify import json_minify


CONFIG_FILEPATH = './config.json'

Config = collections.namedtuple(
    'Config',
    ['bot_administrator', 'status_output_channel', 'output_timezone', 'discord_api_auth_token', 'game_name_display',
     'server_filter']
)


global config


def load_config():
    with open(CONFIG_FILEPATH) as config_file:
        config = Config(**json.loads(json_minify(config_file.read())))
