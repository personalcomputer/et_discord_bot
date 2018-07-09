import collections
import json
import os

from json_minify import json_minify


CONFIG_FILEPATH = os.environ.get('CONFIG_PATH', 'config.json')

Config = collections.namedtuple(
    'Config',
    ['bot_administrator', 'status_output_channel', 'output_timezone',
     'discord_api_auth_token', 'game_name_display', 'server_filter']
)

with open(CONFIG_FILEPATH) as config_file:
    # Global
    config = Config(**json.loads(json_minify(config_file.read())))
