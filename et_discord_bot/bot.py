import asyncio
import copy
import datetime
import logging
import socket
import tempfile

import discord
import pytz

from .etwolf_client import ETClient
from .config import config
from .util import get_time_until_next_interval_start
from .util import split_chunks

SERVER_LIST_UPDATE_FREQUENCY = datetime.timedelta(hours=1)
STATUS_UPDATE_FREQUENCY = datetime.timedelta(seconds=60)
MAX_CONCURRENT_STATUS_QUERIES = 25


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

        self._host_list = []
        self._status_channel = None
        self._status_message = None
        self._users_who_have_seen_help_message = set()

    async def start(self):
        await self._dclient.start()

    async def logout(self):
        logging.info('logging out')
        await self._dclient.logout()
        await self._dclient.close()

    async def _on_discord_ready(self):
        logging.info(f'Successfully logged in as {self._dclient.user.name} ({self._dclient.user.id})')
        self._status_channel = self._dclient.get_channel(config.status_output_channel)
        async for message in self._dclient.logs_from(self._status_channel, limit=30):
            if message.author == self._dclient.user:
                self._status_message = message
                break
        self.loop.create_task(self._update_server_list())
        self.loop.create_task(self._update_status_message())

    async def _on_discord_message(self, message):
        if message.author == self._dclient.user:
            return

        logging.debug('Recieved message from @{message.author.name}: "{message.content}"')

        if message.channel.is_private:
            response = await self._reply_dm(message)
        else:
            return

        if not response:
            return

        logging.info(f'Responding to message from @{message.author.name}: "{message.content}"'
                     f' →  "{response}"')
        await self._dclient.send_message(message.channel, response)

    async def _update_status_message(self):
        while not self._dclient.is_closed:
            host_details = await self._query_serverstatus()
            await self._post_serverstatus(host_details)
            now = datetime.datetime.now(tz=pytz.timezone(config.output_timezone))
            await asyncio.sleep((get_time_until_next_interval_start(now, STATUS_UPDATE_FREQUENCY)).total_seconds())

    async def _update_server_list(self):
        while not self._dclient.is_closed:
            self._host_list = await self._query_server_list()
            await asyncio.sleep(SERVER_LIST_UPDATE_FREQUENCY.total_seconds())

    def _host_details_match_filter(self, host_details):
        for key in config.server_filter:
            if key not in host_details:
                return False
            if host_details[key] != config.server_filter[key]:
                return False
        return True

    async def _query_server_list(self):
        logging.info('Updating server list.')

        full_host_list = await self._etclient.get_server_list()
        tasks = []
        for host_list_chunk in split_chunks(full_host_list, MAX_CONCURRENT_STATUS_QUERIES):
            for hostname, port in host_list_chunk:
                tasks.append(self.loop.create_task(self._etclient.get_server_info(hostname, port)))
            await asyncio.gather(*[h for h in tasks], return_exceptions=True)

        filtered_host_list = []
        for (hostname, port), task in zip(full_host_list, tasks):
            if task.exception():
                continue
            host_details = task.result()
            if not self._host_details_match_filter(host_details):
                continue
            filtered_host_list.append((hostname, port))

        logging.info(f'Updated server list. {len(filtered_host_list)} servers (filtered from {len(full_host_list)} '
                     f'total ET servers).')
        return filtered_host_list

    async def _post_serverstatus(self, host_details):
        message_embed = discord.Embed(
            title=f'{config.game_name_display} Servers',
            colour=int('0xFFFFFF', 16),
        )
        total_players = 0
        for host_info in host_details:
            player_count = int(host_info['humans'] if 'humans' in host_info else host_info['clients'])
            total_players += player_count
            if player_count > 0:
                icon = ':large_blue_circle:'
            else:
                icon = ':black_circle:'
            message_embed.add_field(
                name=f'{icon} {player_count}/{host_info["sv_maxclients"]} | {host_info["hostname_plaintext"]}',
                value=f'`+connect {host_info["ip"]}:{host_info["port"]}` | Map: {host_info["mapname"]}',
                inline=False,
            )
        last_updated = datetime.datetime.now(tz=pytz.timezone(config.output_timezone))
        message_embed.description = (
            f'{total_players} total players online, {len(host_details)} servers '
            f'(list last updated at {last_updated.strftime("%H:%M")} {last_updated.tzname()})'
        )

        logging.info(f'Posting status message. {total_players} players online.')
        if self._status_message:
            await self._dclient.edit_message(self._status_message, embed=message_embed)
        else:
            self._status_message = await self._dclient.send_message(self._status_channel, embed=message_embed)

    async def _query_serverstatus(self):
        tasks = []
        host_list = copy.copy(self._host_list)
        for host_list_chunk in split_chunks(host_list, MAX_CONCURRENT_STATUS_QUERIES):
            for hostname, port in host_list_chunk:
                tasks.append(self.loop.create_task(self._etclient.get_server_info(hostname, port)))
            await asyncio.gather(*[h for h in tasks], return_exceptions=True)

        if any(task.exception() for task in tasks):
            logging.warning(f'{sum(task.exception() is not None for task in tasks)} failed get_server_info queries')

        host_details = []
        for (hostname, port), task in zip(host_list, tasks):
            if task.exception():
                break
            host_info = task.result()
            host_info['ip'] = hostname
            host_info['port'] = port
            host_details.append(host_info)

        return sorted(
            host_details,
            key=lambda host_info: host_info['hostname_plaintext'],
            reverse=True
        )

    async def _reply_dm(self, message):
        if message.author in self._users_who_have_seen_help_message:
            return None
        else:
            response = (
                f'Hi there! I provide info on {config.game_name_display} server status. I\'m like the in-game multiplayer '
                f'server list, but imported into Discord.\n'
                f'\n'
                f'You can see my updates on this channel: #{self._status_channel.name}\n'
                f'\n'
                f'For help and support, please reach out to {config.bot_administrator}. Cheers!'
            )
            self._users_who_have_seen_help_message.add(message.author)
            return response
