import asyncio
import datetime
import logging

import discord

from .etwolf_client import ETClient
from .globals import config, p


class DiscordClient(discord.Client):
    """
    A slight modification of the discord.py Client that hides some of the metaprogramming and also untangles the event
    loop control such that DiscordClient only creates tasks, you need to set up the event loop externally.
    """

    def __init__(self, api_auth_token, loop=None):
        self._api_auth_token = api_auth_token
        super().__init__(loop=loop)

    def add_event_callback(self, event_name, callback_func):
        setattr(self, event_name, callback_func)

    async def start(self):
        await self.login(self._api_auth_token)
        await self.connect()


class ETBot(object):

    def __init__(self, api_auth_token, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._dclient = DiscordClient(api_auth_token=api_auth_token, loop=loop)
        self._dclient.add_event_callback('on_ready', lambda: self._on_discord_ready())
        self._dclient.add_event_callback('on_message', lambda message: self._on_discord_message(message))

        self._etclient = ETClient(loop)
        self._serverstatus_message_cache = None
        self._serverstatus_cached_timed = None

        self._users_who_have_seen_help_message = set()

    async def start(self):
        await self._dclient.start()

    async def logout(self):
        logging.info('logging out')
        await self._dclient.logout()
        await self._dclient.close()

    async def _on_discord_ready(self):
        logging.info(f'Successfully logged in as {self._dclient.user.name} ({self._dclient.user.id})')

    async def _on_discord_message(self, message):
        if message.author == self._dclient.user:
            return

        logging.debug('Recieved message from @{message.author.name}: "{message.content}"')

        if message.content == '!serverstatus':
            response = await self._reply_serverstatus()
        elif message.channel.is_private:
            response = await self._reply_dm(message)
        else:
            return

        if not response:
            return

        logging.info(f'Responding to message from @{message.author.name}: "{message.content}"'
                     f' →  "{response}"')
        await self._dclient.send_message(message.channel, response)

    async def _reply_serverstatus(self):
        refresh_cache = False
        if self._serverstatus_message_cache is None:
            refresh_cache = True
        else:
            cache_age = datetime.datetime.now() - self._serverstatus_cached_time
            cache_life = datetime.timedelta(seconds=config.server_status_cache_expiry)
            refresh_cache = cache_age >= cache_life

        if refresh_cache:
            host_details = []
            for host in config.et_hosts_list:
                raw_info = await self._etclient.get_server_info(host[0], host[1])
                host_details.append((
                    raw_info.server_info["hostname_plaintext"],
                    int(raw_info.server_info['humans']),
                ))

            response = '\n'.join([
                f'{host[0]}: {host[1]} {p.plural("player", host[1])}'
                for host in host_details
            ])

            self._serverstatus_message_cache = response
            self._serverstatus_cached_time = datetime.datetime.now()
        return self._serverstatus_message_cache

    async def _reply_dm(self, message):
        if message.author in self._users_who_have_seen_help_message:
            return None
        else:
            response = (
                f'Hi there! I provide info on {config.game_name} server status. I\'m like the in-game multiplayer '
                f'server list, but imported into Discord.\n'
                f'\n'
                f'Supported commands:\n'
                f' • !serverstatus\n'
                f'\n'
                f'For help and support, please reach out to {config.bot_administrator}. Cheers!'
            )
            self._users_who_have_seen_help_message.add(message.author)
            return response
