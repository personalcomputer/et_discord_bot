import asyncio
import copy
import datetime
import logging
import socket
import sqlite3
import tempfile

import discord
import pytz

from .etwolf_client import ETClient
from .config import config
from .util import get_time_until_next_interval_start
from .util import split_chunks

SERVER_LIST_UPDATE_FREQUENCY = datetime.timedelta(hours=1)
STATUS_UPDATE_FREQUENCY = datetime.timedelta(seconds=60)


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


class HostManagerModel(object):

    def __init__(self):
        self.raw = []
        assert(config.db_url.startswith('sqlite://'))  # No other DBMSes supported right now
        self._sqlite_db_path = config.db_url.replace('sqlite://', '')
        self._migrate()
        self._load_from_db()

    def save(self):
        with sqlite3.connect(self._sqlite_db_path) as db_conn:
            c = db_conn.cursor()
            c.execute('UPDATE host SET active=0')
            for host in self.raw:
                c.execute('SELECT id FROM host WHERE ip=? AND port=?', (host[0], host[1],))
                result = c.fetchall()
                if result:
                    c.execute('UPDATE host SET active=1 WHERE id=?', (result[0][0],))
                else:
                    c.execute('INSERT INTO host (ip, port, active) VALUES (?, ?, 1)', (host[0], host[1],))

    def refresh_from_db(self):
        self._load_from_db()

    def _migrate(self):
        with sqlite3.connect(self._sqlite_db_path) as db_conn:
            c = db_conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS host (id INTEGER PRIMARY KEY, ip TEXT, port INT, active INT)')

    def _load_from_db(self):
        with sqlite3.connect(self._sqlite_db_path) as db_conn:
            c = db_conn.cursor()
            c.execute('SELECT ip, port FROM host WHERE active=1')
            self.raw = c.fetchall()


class ETBot(object):

    def __init__(self, api_auth_token, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._dclient = DiscordClient(api_auth_token=api_auth_token, loop=loop)
        self._dclient.add_event_callback('on_ready', lambda: self._on_discord_ready())
        self._dclient.add_event_callback('on_message', lambda message: self._on_discord_message(message))

        self._etclient = ETClient(loop)

        self._healthy = True

        self._hosts = HostManagerModel()
        self._status_channel = None
        self._status_message = None
        self._users_who_have_seen_help_message = set()

    async def start(self):
        try:
            await self._dclient.start()
        except Exception:
            self._healthy = False
            raise

    async def logout(self):
        await self._dclient.logout()
        await self._dclient.close()

    def is_healthy(self):
        return self._healthy

    async def _on_discord_ready(self):
        try:
            logging.info(f'Successfully logged in as {self._dclient.user.name} ({self._dclient.user.id})')
            self._status_channel = self._dclient.get_channel(config.status_output_channel)
            async for message in self._dclient.logs_from(self._status_channel, limit=30):
                if message.author == self._dclient.user:
                    self._status_message = message
                    break
            self.loop.create_task(self._update_server_list())
            self.loop.create_task(self._update_status_message())
        except Exception:
            self._healthy = False
            raise

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
        try:
            while True:
                host_details = await self._query_serverstatus()
                await self._post_serverstatus(host_details)
                now = datetime.datetime.now(tz=pytz.timezone(config.output_timezone))
                await asyncio.sleep((get_time_until_next_interval_start(now, STATUS_UPDATE_FREQUENCY)).total_seconds())
                if self._dclient.is_closed:
                    break
        finally:
            self._healthy = False

    async def _update_server_list(self):
        try:
            while True:
                self._hosts.raw = await self._query_server_list()
                self._hosts.save()
                await asyncio.sleep(SERVER_LIST_UPDATE_FREQUENCY.total_seconds())
        finally:
            self._healthy = False

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
        for hostname, port in full_host_list:
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

        additional_host_list = []
        for host in config.additional_servers:
            try:
                hostname = socket.gethostbyname_ex(host['hostname'])[2][0]
            except socket.gaierror:
                pass
            else:
                additional_host_list.append((hostname, host['port']))

        logging.info(f'Updated server list. {len(filtered_host_list)} servers (filtered from {len(full_host_list)} '
                     f'total ET servers), plus {len(additional_host_list)} servers from config.')
        return list(set(filtered_host_list).union(additional_host_list))

    async def _post_serverstatus(self, host_details):
        message_embed = discord.Embed(
            title=f'{config.game_name_display} Servers',
            colour=int('FFFFFF', 16),
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
        last_updated_str = f'{last_updated.strftime("%a %b %-d %H:%M")} {last_updated.tzname()}'
        message_embed.description = (
            f'{total_players} total players online now\n'
            f'This status list is updated every minute - last update at {last_updated_str}'
        )

        logging.info(f'Posting status message. {total_players} players online.')
        if self._status_message:
            await self._dclient.edit_message(self._status_message, embed=message_embed)
        else:
            self._status_message = await self._dclient.send_message(self._status_channel, embed=message_embed)

    async def _query_serverstatus(self):
        host_list = copy.copy(self._hosts.raw)
        tasks = []
        for hostname, port in host_list:
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
            key=lambda host_info: (-int(host_info['clients']), host_info['hostname_plaintext'])
        )

    async def _reply_dm(self, message):
        if message.author in self._users_who_have_seen_help_message:
            return None
        else:
            response = (
                f'Hi there! I provide info on {config.game_name_display} server status. I\'m like the in-game '
                f'multiplayer server list, but imported into Discord.\n'
                f'\n'
                f'You can see my updates on this channel: #{self._status_channel.name}\n'
                f'\n'
                f'For help and support, please reach out to {config.bot_administrator}. Cheers!'
            )
            self._users_who_have_seen_help_message.add(message.author)
            return response
