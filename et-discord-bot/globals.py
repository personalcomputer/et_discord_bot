import collections
import json

from json_minify import json_minify
import inflect


CONFIG_FILEPATH = './config.json'

Config = collections.namedtuple(
    'Config',
    ['bot_administrator', 'server_status_cache_expiry', 'status_output_channel', 'output_timezone',
     'discord_api_auth_token', 'et_hosts_list', 'game_name']
)
with open(CONFIG_FILEPATH) as config_file:
    # Global
    config = Config(**json.loads(json_minify(config_file.read())))

# Global
p = inflect.engine()
