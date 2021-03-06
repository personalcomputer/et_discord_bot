import collections
import json
import os

from json_minify import json_minify

Config = collections.namedtuple(
    'Config',
    ['bot_administrator', 'status_output_channel', 'output_timezone', 'discord_api_auth_token', 'game_name_display',
     'server_filter', 'db_url', 'additional_servers']
)


def load_config():
    CONFIG_PATH = os.environ.get('CONFIG_PATH', 'config.json')
    with open(CONFIG_PATH) as config_file:
        return Config(**json.loads(json_minify(config_file.read())))


# Global
config = load_config()
