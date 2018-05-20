import collections
import json

import inflect
from json_minify import json_minify


CONFIG_FILEPATH = './config.json'

Config = collections.namedtuple('Config',
    ['bot_administrator', 'server_status_cache_expiry', 'discord_api_auth_token', 'et_hosts_list']
)
with open(CONFIG_FILEPATH) as config_file:
    config = Config(**json.loads(json_minify(config_file.read())))

p = inflect.engine()
