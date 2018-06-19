import asyncio_extras
import asyncio
import collections
import datetime
import json
import logging
import re
import socket
import struct

from async_timeout import timeout

from .util import split_chunks

OUTBOUND_GLOBAL_MAX_THROUGHPUT = 256*1024  # Bytes per second
OUTBOUND_GLOBAL_MAX_PACKET_RATE = 50       # Datagrams per second
ET_SERVER_RESPONSE_TIMEOUT = datetime.timedelta(seconds=5)


class ETClientProtocol(asyncio.DatagramProtocol):

    PROTOCOL_VERSION = 84

    # static class vars for rate-limiting global throughput. This makes ETClientProtocol non threadsafe (but still
    # coroutine-safe).
    last_sent_message_timestamp = None
    last_sent_message_length = None

    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.message_queue = []
        self._waiter = None

    def connection_made(self, transport):
        self.transport = transport

    async def send_message(self, data):
        # Rate-limit sending rate. Note that there is no queueing of messages, so if multiple messages are pending then
        # it is arbitrary which gets sent first. This works only in the non-RT spike-heavy network conditions of
        # et_discord_bot.
        if ETClientProtocol.last_sent_message_timestamp:
            wait = None
            while wait is None or wait > 0:
                interval = max(
                    ETClientProtocol.last_sent_message_length / OUTBOUND_GLOBAL_MAX_THROUGHPUT,
                    1/OUTBOUND_GLOBAL_MAX_PACKET_RATE
                )
                wait = (ETClientProtocol.last_sent_message_timestamp + interval) - self.loop.time()
                if wait > 0:
                    await asyncio.sleep(wait)

        full_message = b'\xff\xff\xff\xff' + data
        self.transport.sendto(full_message)
        ETClientProtocol.last_sent_message_length = len(full_message)
        ETClientProtocol.last_sent_message_timestamp = self.loop.time()

    async def send_getservers(self):
        await self.send_message(f'getservers {ETClientProtocol.PROTOCOL_VERSION} empty full'.encode())

    async def send_getinfo(self):
        await self.send_message('getinfo\n'.encode())

    def decode_dict(self, raw):
        value = dict()
        raw_list = raw[1:].split('\\')
        for i in range(0, len(raw_list), 2):
            value[raw_list[i]] = raw_list[i+1]
        return value

    def decode_getserversResponse(self, data):
        servers = []
        servers_data = data[data.find(b'\\'):data.rfind(b'\\')]
        servers_data_list = split_chunks(servers_data, 7)
        for server_raw in servers_data_list:
            unpacked_ip_and_port = struct.unpack('!BBBBH', server_raw[1:])
            ip = '.'.join(map(str, unpacked_ip_and_port[:-1]))
            port = int(unpacked_ip_and_port[-1])
            servers.append((ip, port))
        return servers

    def decode_infoResponse(self, data):
        message_parts = data.decode().split('\n')
        host_info = self.decode_dict(message_parts[1])

        host_info['hostname_plaintext'] = re.sub(r'\^.', '', host_info['hostname'])
        logging.debug(json.dumps(host_info, indent=4, sort_keys=True))
        # Known values:
        # 'challenge', 'version', 'protocol', 'hostname', 'serverload', 'mapname', 'clients', 'humans', 'sv_maxclients',
        # 'gametype', 'pure', 'game', 'friendlyFire', 'maxlives', 'needpass', 'gamename', 'g_antilag', 'weaprestrict',
        # 'balancedteams'

        host_info['players'] = []
        for player_info_raw in message_parts[2:]:
            player_info_dict = re.match(r'(?P<score>\d+) (?P<ping>\d+) "(?P<name>.+)"', player_info_raw).groupdict()
            host_info['players'].append(player_info_dict)

        return host_info

    def datagram_received(self, data, _):
        data = data[4:]  # drop \0xff\0xff\0xff\0xf

        if data.startswith(b'infoResponse'):
            message_type = 'infoResponse'
            message_content = self.decode_infoResponse(data)
        elif data.startswith(b'getserversResponse'):
            message_type = 'getserversResponse'
            message_content = self.decode_getserversResponse(data)
        else:
            logging.warning(f'Parsing message with first bytes "{data[:20]}" not implemented, ignoring message.')
            return

        logging.debug(f'Received {message_type}')
        self.message_queue.append((message_type, message_content))

        # Wake up waiter.
        if self._waiter is not None:
            self._waiter.set_result(None)

    async def wait_for_message(self):
        if self._waiter is not None:
            raise RuntimeError('ETClientProtocol.wait_for_message called while another coroutine is already '
                               'waiting.')
        self._waiter = self.loop.create_future()
        try:
            await self._waiter
        finally:
            self._waiter = None

    def error_received(self, exc):
        logging.error(f'ETClientProtocol: Error received: {str(exc)}')
        if self._waiter is not None:
            self._waiter.set_result(None)

    def connection_lost(self, exc):
        logging.debug('ETClientProtocol: Socket closed')
        if self._waiter is not None:
            self._waiter.set_result(None)


class ETClient(object):

    MASTER_SERVER_HOST = 'etmaster.idsoftware.com'
    MASTER_SERVER_PORT = 27950

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()

    @asyncio_extras.async_contextmanager
    async def connect(self, addr):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: ETClientProtocol(self.loop),
            remote_addr=addr
        )
        try:
            yield protocol
        finally:
            transport.close()

    async def get_server_list(self, master_server_addr=None):
        if master_server_addr is None:
            master_server_addr = (socket.gethostbyname(ETClient.MASTER_SERVER_HOST), ETClient.MASTER_SERVER_PORT)

        async with self.connect(master_server_addr) as protocol:
            try:
                await protocol.send_getservers()

                while True:
                    async with timeout(ET_SERVER_RESPONSE_TIMEOUT.total_seconds()):
                        await protocol.wait_for_message()
            except asyncio.TimeoutError:
                if not protocol.message_queue:
                    raise
                else:
                    pass

            servers = []
            for message_type, servers_part in protocol.message_queue:
                if message_type != 'getserversResponse':
                    raise ValueError()
                servers.extend(servers_part)

            return servers

    async def get_server_info(self, server, port):
        async with self.connect((server, port)) as protocol:
            tries = 3
            while tries > 0:
                await protocol.send_getinfo()

                try:
                    async with timeout(ET_SERVER_RESPONSE_TIMEOUT.total_seconds()):
                        await protocol.wait_for_message()
                        message_type, message_content = protocol.message_queue.pop()
                        if message_type != 'infoResponse':
                            raise ValueError()
                        return message_content
                except asyncio.TimeoutError:
                    tries -= 1
                    if not tries:
                        raise
