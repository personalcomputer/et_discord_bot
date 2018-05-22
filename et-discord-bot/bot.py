import asyncio
import datetime
import logging
import pytz
import socket

import discord

from .etwolf_client import ETClient
from .globals import config, p

QUERY_FREQUENCY = datetime.timedelta(seconds=60)


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
        self.loop.create_task(self._update())

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

    async def _update(self):
        while not self._dclient.is_closed:
            start = datetime.datetime.now()
            hosts = await self._get_serverstatus()
            await self._post_serverstatus(hosts)
            end = datetime.datetime.now()
            await asyncio.sleep((QUERY_FREQUENCY - (end-start)).total_seconds())

    async def _post_serverstatus(self, hosts):
        message_embed = discord.Embed(
            title=f'{config.game_name} Servers',
            colour=int('0xFFFFFF', 16),
        )
        total_players = 0
        for host_info in hosts:
            info = host_info[1].server_info
            player_count = int(info['humans'] if 'humans' in info else info['clients'])
            total_players += player_count
            if player_count > 0:
                icon = ':small_orange_diamond:'
            else:
                icon = ':black_small_square:'
            message_embed.add_field(
                name=f'{icon} {player_count}/{info["sv_maxclients"]} | {info["hostname_plaintext"]}',
                value=f'`+connect {host_info[0][0]}:{host_info[0][1]}` | Map: {info["mapname"]}',
                inline=False,
            )
        last_updated = datetime.datetime.now(tz=pytz.timezone(config.output_timezone))
        message_embed.description = (
            f'{total_players} total players online '
            f'(list last updated at {last_updated.strftime("%H:%M")} {last_updated.tzname()})'
        )

        logging.info(f'Posting status message')
        if self._status_message:
            await self._dclient.edit_message(self._status_message, embed=message_embed)
        else:
            self._status_message = await self._dclient.send_message(self._status_channel, embed=message_embed)

    async def _get_serverstatus(self):
        logging.info(f'Querying server status')
        tasks = []
        for host in config.et_hosts_list:
            tasks.append((
                (socket.gethostbyname(host[0]), host[1]),
                self.loop.create_task(self._etclient.get_server_info(host[0], host[1]))
            ))

        await asyncio.gather(*[h[1] for h in tasks])
        host_details = [
            (task[0], task[1].result())
            for task in tasks if not task[1].exception()
        ]
        return sorted(host_details, key=lambda host_info: host_info[1].server_info['hostname_plaintext'], reverse=True)

    async def _reply_dm(self, message):
        if message.author in self._users_who_have_seen_help_message:
            return None
        else:
            response = (
                f'Hi there! I provide info on {config.game_name} server status. I\'m like the in-game multiplayer '
                f'server list, but imported into Discord.\n'
                f'\n'
                f'You can see my updates on this channel: #{self._status_channel.name}\n'
                f'\n'
                f'For help and support, please reach out to {config.bot_administrator}. Cheers!'
            )
            self._users_who_have_seen_help_message.add(message.author)
            return response
